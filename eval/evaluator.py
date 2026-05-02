import argparse
import json
import re
from collections.abc import Callable
from typing import Any

import requests

from api.schemas import EvalResult, EvalSummary
from core.generator import RAGGenerator


ProgressCallback = Callable[[str, int, int], None]


def normalize_text(value: str) -> str:
    """
    Normalize text for evaluation.

    Keeps the evaluator simple but less brittle:
    - lowercase
    - remove punctuation
    - collapse whitespace
    """
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def loose_keyword_match(keyword: str, answer: str) -> bool:
    """
    Returns True if the keyword is reasonably represented in the answer.

    This avoids false failures where the answer is correct but phrased slightly
    differently.

    Examples:
    - "racial classifications" should match "racial classification"
    - "right to counsel" should match "right to the assistance of counsel"
    - "questioning must cease" should partially match "interrogation must immediately stop"
    """
    keyword_norm = normalize_text(keyword)
    answer_norm = normalize_text(answer)

    if not keyword_norm:
        return True

    # Exact normalized phrase match.
    if keyword_norm in answer_norm:
        return True

    # Singular/plural tolerance.
    keyword_singular = " ".join(
        token[:-1] if token.endswith("s") and len(token) > 4 else token
        for token in keyword_norm.split()
    )

    answer_singular = " ".join(
        token[:-1] if token.endswith("s") and len(token) > 4 else token
        for token in answer_norm.split()
    )

    if keyword_singular in answer_singular:
        return True

    keyword_tokens = [
        token
        for token in keyword_singular.split()
        if token not in {
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
        }
    ]

    if not keyword_tokens:
        return True

    answer_tokens = set(answer_singular.split())

    matched = sum(1 for token in keyword_tokens if token in answer_tokens)
    required = max(1, round(len(keyword_tokens) * 0.65))

    return matched >= required


class Evaluator:
    """
    Simple RAG evaluation helper.

    A test passes if:
    1. At least one expected source file appears in retrieved chunks.
    2. Expected answer keywords are reasonably represented in the answer.

    This is intentionally a loose evaluator, not a legal final-answer judge.
    """

    def __init__(self, generator: RAGGenerator | None = None):
        self.generator = generator

    def run(
        self,
        test_cases: list[dict[str, Any]],
        top_k: int = 8,
        progress_callback: ProgressCallback | None = None,
    ) -> EvalSummary:
        if self.generator is None:
            raise ValueError("Evaluator requires a RAGGenerator instance.")

        results: list[EvalResult] = []
        total = len(test_cases)

        for index, case in enumerate(test_cases, start=1):
            question = case["question"]
            expected_files = case.get("expected_source_files", [])
            expected_keywords = case.get("expected_answer_keywords", [])

            if progress_callback:
                progress_callback(
                    f"Running test case {index}/{total}: {question[:120]}",
                    index - 1,
                    total,
                )

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

            keyword_matches = {
                keyword: loose_keyword_match(keyword, answer)
                for keyword in expected_keywords
            }

            keyword_pass = all(keyword_matches.values())

            passed = source_pass and keyword_pass

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
                )
            )

            if progress_callback:
                status = "passed" if passed else "failed"
                missing_keywords = [
                    keyword
                    for keyword, did_match in keyword_matches.items()
                    if not did_match
                ]

                if missing_keywords:
                    progress_callback(
                        (
                            f"Finished test case {index}/{total}: {status}. "
                            f"Missing keywords: {', '.join(missing_keywords)}"
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

        if progress_callback:
            progress_callback(
                f"Evaluation complete: {passed_count}/{total} passed.",
                total,
                total,
            )

        return EvalSummary(
            total=total,
            passed=passed_count,
            failed=total - passed_count,
            results=results,
        )


def run_eval_against_api(
    jsonl_path: str,
    api_url: str,
    top_k: int,
) -> dict[str, Any]:
    cases = []

    with open(jsonl_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                cases.append(json.loads(line))

    results = []

    for index, case in enumerate(cases, start=1):
        print(f"Running API eval case {index}/{len(cases)}: {case['question']}")

        payload = {
            "question": case["question"],
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

        keyword_pass = all(
            loose_keyword_match(keyword, answer)
            for keyword in expected_keywords
        )

        results.append(
            {
                "question": case["question"],
                "passed": source_pass and keyword_pass,
                "source_pass": source_pass,
                "keyword_pass": keyword_pass,
                "retrieved_files": retrieved_files,
                "expected_files": expected_files,
                "expected_keywords": expected_keywords,
            }
        )

    passed = sum(1 for result in results if result["passed"])
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
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