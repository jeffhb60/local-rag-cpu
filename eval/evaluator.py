import argparse
import json
from typing import Any

import requests

from api.schemas import EvalResult, EvalSummary
from core.generator import RAGGenerator


class Evaluator:
    """
    Simple RAG evaluation helper.

    A test passes only if:
    1. At least one expected source file appears in retrieved chunks.
    2. All expected keywords appear in the generated answer.
    """

    def __init__(self, generator: RAGGenerator | None = None):
        self.generator = generator

    def run(
        self,
        test_cases: list[dict[str, Any]],
        top_k: int = 8,
    ) -> EvalSummary:
        if self.generator is None:
            raise ValueError("Evaluator requires a RAGGenerator instance.")

        results: list[EvalResult] = []

        for case in test_cases:
            question = case["question"]
            expected_files = case.get("expected_source_files", [])
            expected_keywords = case.get("expected_answer_keywords", [])

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

            source_pass = (
                not expected_files
                or any(expected in retrieved_files for expected in expected_files)
            )

            answer_lower = answer.lower()
            keyword_pass = all(
                keyword.lower() in answer_lower
                for keyword in expected_keywords
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
                    passed=source_pass and keyword_pass,
                )
            )

        passed = sum(1 for result in results if result.passed)

        return EvalSummary(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
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

    for case in cases:
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

        answer_lower = answer.lower()
        keyword_pass = all(
            keyword.lower() in answer_lower
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