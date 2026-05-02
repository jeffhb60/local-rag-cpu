import argparse
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

from api.schemas import EvalResult, EvalSummary
from config import settings
from core.generator import RAGGenerator


ProgressCallback = Callable[[str, int, int], None]


STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "by",
    "must",
    "did",
    "does",
    "do",
    "was",
    "were",
    "is",
    "are",
    "be",
    "being",
    "about",
}


def normalize_text(value: str) -> str:
    """
    Normalize text for evaluation comparisons.

    Steps:
    - lowercase
    - normalize dashes
    - remove most punctuation
    - collapse repeated whitespace
    """
    value = value.lower()
    value = value.replace("–", "-")
    value = value.replace("—", "-")
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def singularize_token(token: str) -> str:
    """
    Small plural-tolerance helper.

    This is intentionally simple. It is not meant to be a full stemmer.
    """
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"

    if token.endswith("s") and len(token) > 4:
        return token[:-1]

    return token


def content_tokens(value: str) -> list[str]:
    """
    Convert text into comparable content tokens.

    Removes common stopwords and applies light singular/plural normalization.
    """
    normalized = normalize_text(value)

    return [
        singularize_token(token)
        for token in normalized.split()
        if token not in STOPWORDS
    ]


def load_equivalents(path: Path) -> dict[str, list[str]]:
    """
    Load keyword-equivalent mappings from JSON.

    Expected JSON format:
    {
      "right to counsel": [
        "right to counsel",
        "right to the assistance of counsel",
        "right to an attorney"
      ]
    }

    If the file does not exist, evaluation still works with no custom equivalents.
    """
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid evaluation equivalents JSON: {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Evaluation equivalents file must contain a JSON object: {path}"
        )

    normalized: dict[str, list[str]] = {}

    for key, values in data.items():
        if not isinstance(key, str):
            continue

        if not isinstance(values, list):
            continue

        normalized_key = normalize_text(key)

        normalized_values = [
            value
            for value in values
            if isinstance(value, str) and value.strip()
        ]

        normalized[normalized_key] = normalized_values

    return normalized


def phrase_or_equivalent_match(
    keyword: str,
    answer: str,
    legal_equivalents: dict[str, list[str]],
) -> bool:
    """
    Check exact phrase match or configured equivalent phrase match.
    """
    keyword_norm = normalize_text(keyword)
    answer_norm = normalize_text(answer)

    if not keyword_norm:
        return True

    if keyword_norm in answer_norm:
        return True

    equivalents = legal_equivalents.get(keyword_norm, [])

    for equivalent in equivalents:
        if normalize_text(equivalent) in answer_norm:
            return True

    return False


def loose_keyword_match(
    keyword: str,
    answer: str,
    question: str = "",
    legal_equivalents: dict[str, list[str]] | None = None,
) -> bool:
    """
    Fairer keyword/concept match.

    Supports:
    - exact normalized phrase matches
    - externally configured equivalent phrases
    - singular/plural tolerance
    - content-token overlap across the answer and question

    Including the question prevents false failures where a term appears in the
    user question and the answer directly responds to it.
    """
    legal_equivalents = legal_equivalents or {}

    keyword_norm = normalize_text(keyword)
    answer_norm = normalize_text(answer)
    question_norm = normalize_text(question)
    combined_norm = f"{question_norm} {answer_norm}".strip()

    if not keyword_norm:
        return True

    if keyword_norm in answer_norm:
        return True

    if phrase_or_equivalent_match(
        keyword=keyword,
        answer=answer,
        legal_equivalents=legal_equivalents,
    ):
        return True

    keyword_singular = " ".join(
        singularize_token(token)
        for token in keyword_norm.split()
    )

    combined_singular = " ".join(
        singularize_token(token)
        for token in combined_norm.split()
    )

    if keyword_singular in combined_singular:
        return True

    keyword_tokens = content_tokens(keyword)

    if not keyword_tokens:
        return True

    combined_tokens = set(content_tokens(f"{question} {answer}"))

    matched = sum(1 for token in keyword_tokens if token in combined_tokens)

    if len(keyword_tokens) == 1:
        return matched == 1

    required = max(1, round(len(keyword_tokens) * 0.67))
    return matched >= required


class Evaluator:
    """
    RAG evaluation helper.

    Reports:
    - source hit rate
    - keyword hit rate
    - strict pass rate
    - keyword coverage
    - manual review candidates

    This avoids treating one brittle pass/fail score as the whole truth.
    """

    def __init__(
        self,
        generator: RAGGenerator | None = None,
        equivalents_path: Path | None = None,
    ):
        self.generator = generator
        self.equivalents_path = (
            equivalents_path
            or settings.evaluation_equivalents_path
        )

    def run(
            self,
            test_cases: list[dict[str, Any]],
            top_k: int = 8,
            retrieval_only: bool = False,
            progress_callback: ProgressCallback | None = None,
    ) -> EvalSummary:
        if self.generator is None:
            raise ValueError("Evaluator requires a RAGGenerator instance.")

        legal_equivalents = load_equivalents(self.equivalents_path)

        results: list[EvalResult] = []
        total = len(test_cases)

        for index, case in enumerate(test_cases, start=1):
            question = case["question"]
            expected_files = case.get("expected_source_files", [])
            expected_keywords = case.get("expected_answer_keywords", [])

            if progress_callback:
                mode_label = "retrieval-only" if retrieval_only else "generation"
                progress_callback(
                    f"Running {mode_label} test case {index}/{total}: {question[:120]}",
                    index - 1,
                    total,
                )

            if retrieval_only:
                query_embedding = self.generator.embeddings.embed_query(question)

                retrieved_chunks = self.generator.vectorstore.query(
                    question=question,
                    query_embedding=query_embedding,
                    top_k=top_k,
                )

                answer = None
            else:
                rag_result = self.generator.answer(
                    question=question,
                    top_k=top_k,
                )

                answer = rag_result["answer"]
                retrieved_chunks = rag_result["retrieved_chunks"]

            retrieved_files = [
                chunk["metadata"].get("file_name", "")
                for chunk in retrieved_chunks
            ]

            retrieved_files_normalized = {
                file_name.lower().strip()
                for file_name in retrieved_files
            }

            expected_files_normalized = [
                file_name.lower().strip()
                for file_name in expected_files
            ]

            source_pass = (
                    not expected_files_normalized
                    or any(
                expected in retrieved_files_normalized
                for expected in expected_files_normalized
            )
            )

            if retrieval_only:
                keyword_pass = None
                matched_keywords = []
                missing_keywords = []
                keyword_coverage = None
                passed = source_pass
                needs_manual_review = False

            else:
                matched_keywords: list[str] = []
                missing_keywords: list[str] = []

                for keyword in expected_keywords:
                    did_match = loose_keyword_match(
                        keyword=keyword,
                        answer=answer or "",
                        question=question,
                        legal_equivalents=legal_equivalents,
                    )

                    if did_match:
                        matched_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)

                keyword_total = len(expected_keywords)

                keyword_coverage = (
                    len(matched_keywords) / keyword_total
                    if keyword_total > 0
                    else 1.0
                )

                keyword_pass = keyword_coverage >= 0.80
                passed = source_pass and keyword_pass

                needs_manual_review = (
                        source_pass
                        and not passed
                        and keyword_coverage >= 0.50
                )

            results.append(
                EvalResult(
                    question=question,
                    answer=answer,
                    retrieved_source_files=retrieved_files,
                    expected_source_files=expected_files,
                    expected_answer_keywords=expected_keywords,
                    source_pass=source_pass,
                    keyword_pass=keyword_pass,
                    passed=passed,
                    matched_keywords=matched_keywords,
                    missing_keywords=missing_keywords,
                    keyword_coverage=(
                        round(keyword_coverage, 3)
                        if keyword_coverage is not None
                        else None
                    ),
                    retrieval_only=retrieval_only,
                    needs_manual_review=needs_manual_review,
                )
            )

            if progress_callback:
                status = "passed" if passed else "failed"

                if retrieval_only:
                    progress_callback(
                        f"Finished retrieval-only test case {index}/{total}: {status}",
                        index,
                        total,
                    )
                else:
                    if missing_keywords:
                        progress_callback(
                            (
                                f"Finished test case {index}/{total}: {status}. "
                                f"Coverage {keyword_coverage:.0%}. "
                                f"Missing: {', '.join(missing_keywords)}"
                            ),
                            index,
                            total,
                        )
                    else:
                        progress_callback(
                            f"Finished test case {index}/{total}: {status}",
                            index,
                            total,
                        )

        passed_count = sum(1 for result in results if result.passed)
        source_passed = sum(1 for result in results if result.source_pass)

        if retrieval_only:
            keyword_passed = None
            keyword_hit_rate = None
            average_keyword_coverage = None
            manual_review_count = 0
        else:
            keyword_passed = sum(
                1 for result in results if result.keyword_pass is True
            )

            keyword_hit_rate = (
                round(keyword_passed / total, 3)
                if total
                else 0.0
            )

            keyword_coverages = [
                result.keyword_coverage
                for result in results
                if result.keyword_coverage is not None
            ]

            average_keyword_coverage = (
                round(sum(keyword_coverages) / len(keyword_coverages), 3)
                if keyword_coverages
                else 0.0
            )

            manual_review_count = sum(
                1
                for result in results
                if result.needs_manual_review
            )

        if progress_callback:
            mode_label = "retrieval-only evaluation" if retrieval_only else "evaluation"
            progress_callback(
                f"{mode_label.capitalize()} complete: {passed_count}/{total} passed.",
                total,
                total,
            )

        return EvalSummary(
            total=total,
            passed=passed_count,
            failed=total - passed_count,
            retrieval_only=retrieval_only,
            source_passed=source_passed,
            source_hit_rate=round(source_passed / total, 3) if total else 0.0,
            keyword_passed=keyword_passed,
            keyword_hit_rate=keyword_hit_rate,
            average_keyword_coverage=average_keyword_coverage,
            manual_review_count=manual_review_count,
            results=results,
        )


def run_eval_against_api(
    jsonl_path: str,
    api_url: str,
    top_k: int,
) -> dict[str, Any]:
    """
    CLI evaluator that calls the running FastAPI server.

    Example:
    python -m eval.evaluator --jsonl eval/test_cases.jsonl --api-url http://localhost:8000/api/query
    """
    cases: list[dict[str, Any]] = []

    with open(jsonl_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                cases.append(json.loads(line))

    legal_equivalents = load_equivalents(settings.evaluation_equivalents_path)

    results: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        question = case["question"]

        print(f"Running API eval case {index}/{len(cases)}: {question}")

        payload = {
            "question": question,
            "top_k": top_k,
        }

        response = requests.post(api_url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()

        answer = data["answer"]

        retrieved_files = [
            chunk["metadata"].get("file_name", "")
            for chunk in data["retrieved_chunks"]
        ]

        expected_files = case.get("expected_source_files", [])
        expected_keywords = case.get("expected_answer_keywords", [])

        source_pass = (
            not expected_files
            or any(expected in retrieved_files for expected in expected_files)
        )

        matched_keywords = [
            keyword
            for keyword in expected_keywords
            if loose_keyword_match(
                keyword=keyword,
                answer=answer,
                question=question,
                legal_equivalents=legal_equivalents,
            )
        ]

        missing_keywords = [
            keyword
            for keyword in expected_keywords
            if keyword not in matched_keywords
        ]

        keyword_coverage = (
            len(matched_keywords) / len(expected_keywords)
            if expected_keywords
            else 1.0
        )

        keyword_pass = keyword_coverage >= 0.80
        passed = source_pass and keyword_pass

        results.append(
            {
                "question": question,
                "answer": answer,
                "passed": passed,
                "source_pass": source_pass,
                "keyword_pass": keyword_pass,
                "keyword_coverage": round(keyword_coverage, 3),
                "retrieved_files": retrieved_files,
                "expected_files": expected_files,
                "expected_keywords": expected_keywords,
                "matched_keywords": matched_keywords,
                "missing_keywords": missing_keywords,
                "needs_manual_review": (
                    source_pass
                    and not passed
                    and keyword_coverage >= 0.50
                ),
            }
        )

    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    source_passed = sum(1 for result in results if result["source_pass"])
    keyword_passed = sum(1 for result in results if result["keyword_pass"])
    manual_review_count = sum(
        1
        for result in results
        if result["needs_manual_review"]
    )

    average_keyword_coverage = (
        sum(result["keyword_coverage"] for result in results) / total
        if total > 0
        else 0.0
    )

    summary = {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "source_passed": source_passed,
        "source_hit_rate": round(source_passed / total, 3) if total else 0.0,
        "keyword_passed": keyword_passed,
        "keyword_hit_rate": round(keyword_passed / total, 3) if total else 0.0,
        "average_keyword_coverage": round(average_keyword_coverage, 3),
        "manual_review_count": manual_review_count,
        "results": results,
    }

    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", required=True)
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/api/query",
    )
    parser.add_argument("--top-k", type=int, default=8)

    args = parser.parse_args()

    run_eval_against_api(
        jsonl_path=args.jsonl,
        api_url=args.api_url,
        top_k=args.top_k,
    )