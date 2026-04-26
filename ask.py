from config import TOP_K
from ollama_client import embed_one, generate
from store import get_collection


def search(question: str) -> list[dict]:
    collection = get_collection()
    query_embedding = embed_one(question)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    hits = []

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for text, meta, distance in zip(documents, metadatas, distances):
        hits.append(
            {
                "text": text,
                "file": meta.get("file", "unknown"),
                "page": meta.get("page", ""),
                "chunk": meta.get("chunk", ""),
                "distance": distance,
            }
        )

    return hits


def make_prompt(question: str, hits: list[dict]) -> str:
    context_blocks = []

    for index, hit in enumerate(hits, start=1):
        page = f", page {hit['page']}" if hit.get("page") else ""

        context_blocks.append(
            f"[{index}] {hit['file']}{page}, chunk {hit['chunk']}\n"
            f"{hit['text']}"
        )

    context = "\n\n---\n\n".join(context_blocks)

    return f"""Answer from the context below. Do not use outside knowledge.

If the context does not contain the answer, say:
"I could not find that in the indexed documents."

Cite the bracket number, file name, and page if available.

Context:
{context}

Question:
{question}

Answer:
"""


def print_sources(hits: list[dict]) -> None:
    print("\nSources checked:")

    for index, hit in enumerate(hits, start=1):
        page = f" p.{hit['page']}" if hit.get("page") else ""
        print(
            f"{index}. {hit['file']}{page} "
            f"(chunk {hit['chunk']}, distance {hit['distance']:.4f})"
        )


def main() -> None:
    print("Local RAG. Type exit to quit.\n")

    while True:
        question = input("Ask: ").strip()

        if question.lower() in {"exit", "quit", "q"}:
            break

        if not question:
            continue

        hits = search(question)
        answer = generate(make_prompt(question, hits))

        print("\n" + answer)
        print_sources(hits)
        print()


if __name__ == "__main__":
    main()