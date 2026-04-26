"""
Run a simple evaluation for the local RAG app.

Usage:
    python evals/run_eval.py
    python evals/run_eval.py --skip-generation
    python evals/run_eval.py --max-questions 3
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any


# Allows this script to import from the current flat project structure.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from ask import make_prompt, search
from ollama_client import OllamaError, generate


DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "evals" / "questions.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "evals" / "results.csv"


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load JSONL evaluation questions."""
    questions: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            if not item.get("question"):
                raise ValueError(f"Missing question on line {line_number}")

            questions.append(item)

    return questions


def normalize_expected_files(item: dict[str, Any]) -> list[str]:
    expected_files = item.get("expected_files")

    if expected_files is None and item.get("expected_file"):
        expected_files = [item["expected_file"]]

    if expected_files is None:
        return []

    if isinstance(expected_files, str):
        return [expected_files]

    return list(expected_files)


def normalize_expected_pages(item: dict[str, Any]) -> list[str]:
    expected_pages = item.get("expected_pages")

    if expected_pages is None and item.get("expected_page") is not None:
        expected_pages = [item["expected_page"]]

    if expected_pages is None:
        return []

    if isinstance(expected_pages, (str, int)):
        return [str(expected_pages)]

    return [str(page) for page in expected_pages]


def contains_all_terms(text: str, terms: list[str]) -> bool:
    """Check that all expected terms appear in the answer."""
    lower_text = text.lower()

    return all(str(term).lower() in lower_text for term in terms)


def check_source_hit(hits: list[dict[str, Any]], expected_files: list[str]) -> bool | None:
    """Check whether at least one expected file appears in retrieved chunks."""
    if not expected_files:
        return None

    retrieved_files = {str(hit.get("file", "")).lower() for hit in hits}
    expected_file_set = {file_name.lower() for file_name in expected_files}

    return bool(retrieved_files & expected_file_set)


def check_page_hit(
    hits: list[dict[str, Any]],
    expected_files: list[str],
    expected_pages: list[str],
) -> bool | None:
    """Check whether expected file/page appears in retrieved chunks."""
    if not expected_files or not expected_pages:
        return None

    expected_file_set = {file_name.lower() for file_name in expected_files}
    expected_page_set = {page.lower() for page in expected_pages}

    for hit in hits:
        file_name = str(hit.get("file", "")).lower()
        page = str(hit.get("page", "")).lower()

        if file_name in expected_file_set and page in expected_page_set:
            return True

    return False


def bool_to_csv(value: bool | None) -> int | str:
    if value is None:
        return ""

    return int(value)


def evaluate_question(
    item: dict[str, Any],
    skip_generation: bool = False,
) -> dict[str, Any]:
    """Run retrieval and optional generation for one question."""
    question = item["question"]
    expected_files = normalize_expected_files(item)
    expected_pages = normalize_expected_pages(item)
    answer_contains = list(item.get("answer_contains", []))

    started = time.perf_counter()

    hits: list[dict[str, Any]] = []
    answer = ""
    error = ""

    try:
        hits = search(question)

        if hits and not skip_generation:
            prompt = make_prompt(question, hits)
            answer = generate(prompt)

        elif not hits:
            answer = "I could not find that in the indexed documents."

    except OllamaError as exc:
        error = str(exc)
        answer = error

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        answer = error

    latency_seconds = round(time.perf_counter() - started, 3)

    source_hit = check_source_hit(hits, expected_files)
    page_hit = check_page_hit(hits, expected_files, expected_pages)

    if answer_contains and not skip_generation:
        answer_terms_hit = contains_all_terms(answer, answer_contains)
    else:
        answer_terms_hit = None

    answer_passed = None

    if not skip_generation:
        source_ok = True if source_hit is None else source_hit
        page_ok = True if page_hit is None else page_hit
        terms_ok = True if answer_terms_hit is None else answer_terms_hit

        answer_passed = source_ok and page_ok and terms_ok and not error

    top_hit = hits[0] if hits else {}

    return {
        "id": item.get("id", ""),
        "question": question,
        "expected_files": "; ".join(expected_files),
        "expected_pages": "; ".join(expected_pages),
        "answer_contains": "; ".join(str(term) for term in answer_contains),
        "source_hit": bool_to_csv(source_hit),
        "page_hit": bool_to_csv(page_hit),
        "answer_terms_hit": bool_to_csv(answer_terms_hit),
        "answer_passed": bool_to_csv(answer_passed),
        "latency_seconds": latency_seconds,
        "top_file": top_hit.get("file", ""),
        "top_page": top_hit.get("page", ""),
        "top_chunk": top_hit.get("chunk", ""),
        "top_distance": top_hit.get("distance", ""),
        "retrieved_files": "; ".join(str(hit.get("file", "")) for hit in hits),
        "retrieved_pages": "; ".join(str(hit.get("page", "")) for hit in hits),
        "answer": answer,
        "error": error,
    }


def write_results(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write evaluation results to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "question",
        "expected_files",
        "expected_pages",
        "answer_contains",
        "source_hit",
        "page_hit",
        "answer_terms_hit",
        "answer_passed",
        "latency_seconds",
        "top_file",
        "top_page",
        "top_chunk",
        "top_distance",
        "retrieved_files",
        "retrieved_pages",
        "answer",
        "error",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> str:
    """Create a compact summary for the terminal."""
    total = len(rows)

    def rate(column: str) -> str:
        values = [row[column] for row in rows if row[column] != ""]

        if not values:
            return "n/a"

        passed = sum(int(value) for value in values)

        return f"{passed}/{len(values)} ({passed / len(values):.1%})"

    avg_latency = (
        sum(float(row["latency_seconds"]) for row in rows) / total
        if total
        else 0.0
    )

    failed = [row for row in rows if row.get("answer_passed") == 0]
    failed_ids = ", ".join(row.get("id") or row["question"][:40] for row in failed[:10])

    lines = [
        f"Questions tested: {total}",
        f"Source hit rate: {rate('source_hit')}",
        f"Page hit rate: {rate('page_hit')}",
        f"Answer term hit rate: {rate('answer_terms_hit')}",
        f"Answer pass rate: {rate('answer_passed')}",
        f"Average latency: {avg_latency:.2f} seconds",
    ]

    if failed_ids:
        lines.append(f"Failed cases: {failed_ids}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate local RAG retrieval and answers.")

    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS_PATH,
        help="Path to JSONL questions file.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for CSV results.",
    )

    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Only evaluate retrieval. Do not call the chat model.",
    )

    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help="Optional limit for quick test runs.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    questions = load_questions(args.questions)

    if args.max_questions is not None:
        questions = questions[: args.max_questions]

    rows = []

    for index, item in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] {item['question']}")
        row = evaluate_question(item, skip_generation=args.skip_generation)
        rows.append(row)

    write_results(args.output, rows)

    print()
    print(summarize(rows))
    print(f"\nSaved results to: {args.output}")


if __name__ == "__main__":
    main()