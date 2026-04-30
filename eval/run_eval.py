import json
import sys
sys.path.append(".")
from app.rag.pipeline import RAGPipeline
from app.rag.prompts import load_settings

def run_eval():
    settings = load_settings()
    pipeline = RAGPipeline()
    with open("eval/test_set.jsonl", "r") as f:
        tests = [json.loads(line) for line in f if line.strip()]

    results = []
    for idx, test in enumerate(tests):
        # Force strict mode for evaluation
        result = pipeline.answer(
            question=test["question"],
            provider_name=settings["default_provider"],
            model_name=settings["default_model"],
            mode="strict"
        )
        answer = result["answer"]
        sources = result["sources"]
        # check keywords
        keywords_ok = all(kw.lower() in answer.lower() for kw in test["expected_answer_keywords"])
        # check source files appear in citations
        cited_files = [s["file"] for s in sources]
        sources_ok = any(f in cited_files for f in test["expected_source_files"])
        passed = keywords_ok and sources_ok
        results.append({
            "test_index": idx,
            "question": test["question"],
            "answer": answer,
            "keywords_found": keywords_ok,
            "sources_found": sources_ok,
            "passed": passed
        })

    # Print report
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    print(f"Evaluation: {passed}/{total} passed")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] Q: {r['question']} -> Keywords {'✔' if r['keywords_found'] else '✘'}, Sources {'✔' if r['sources_found'] else '✘'}")
    return results

if __name__ == "__main__":
    run_eval()