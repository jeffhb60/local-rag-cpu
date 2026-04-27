import subprocess
import sys
from pathlib import Path

import streamlit as st

from ask import make_prompt, search
from config import BASE_DIR, DOCS_DIR
from loaders import SUPPORTED_FILES
from ollama_client import OllamaError
from providers import generate_answer


st.set_page_config(
    page_title="Local RAG Assistant",
    page_icon="📚",
    layout="wide",
)


def run_ingest() -> tuple[bool, str]:
    """
    Run ingest.py as a subprocess so the Streamlit app can index documents
    without duplicating ingestion logic.
    """
    result = subprocess.run(
        [sys.executable, "ingest.py"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )

    output = result.stdout.strip()

    if result.stderr.strip():
        output += "\n\nERRORS:\n" + result.stderr.strip()

    return result.returncode == 0, output


def save_uploaded_files(uploaded_files) -> list[Path]:
    """
    Save uploaded files into the configured DOCS_DIR.
    """
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    for uploaded_file in uploaded_files:
        target_path = DOCS_DIR / uploaded_file.name

        with target_path.open("wb") as file:
            file.write(uploaded_file.getbuffer())

        saved_paths.append(target_path)

    return saved_paths


def format_source(hit: dict, index: int) -> str:
    page = f", page {hit['page']}" if hit.get("page") else ""
    chunk = hit.get("chunk", "")
    distance = hit.get("distance")

    if isinstance(distance, float):
        distance_text = f", distance {distance:.4f}"
    else:
        distance_text = ""

    return f"{index}. {hit['file']}{page}, chunk {chunk}{distance_text}"


st.title("Local RAG Assistant")

st.caption(
    "Ask questions about documents indexed into your local ChromaDB database. "
    "Answers are generated through your local Ollama model."
)


with st.sidebar:
    st.header("Documents")

    st.write("Document folder:")
    st.code(str(DOCS_DIR), language="text")

    allowed_types = [ext.replace(".", "") for ext in SUPPORTED_FILES]

    uploaded_files = st.file_uploader(
        "Upload documents",
        type=allowed_types,
        accept_multiple_files=True,
    )

    if uploaded_files:
        saved_paths = save_uploaded_files(uploaded_files)

        st.success(f"Saved {len(saved_paths)} file(s).")

        with st.expander("Uploaded files"):
            for path in saved_paths:
                st.write(path.name)

    st.divider()

    if st.button("Index / Reindex Documents", use_container_width=True):
        with st.spinner("Indexing documents..."):
            ok, output = run_ingest()

        if ok:
            st.success("Indexing finished.")
        else:
            st.error("Indexing failed.")

        if output:
            st.code(output, language="text")

    st.divider()

    st.header("Model")

    provider = st.selectbox(
        "Provider",
        ["local", "deepseek", "gemini", "openai"],
    )

    model_override = st.text_input(
        "Model override optional",
        value="",
    )

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        sources = message.get("sources", [])

        if sources:
            with st.expander("Sources checked"):
                for source in sources:
                    st.write(source)


question = st.chat_input("Ask a question about your indexed documents")

if question:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            try:
                hits = search(question)

                if not hits:
                    answer = "I could not find that in the indexed documents."
                    sources = []
                else:
                    prompt = make_prompt(question, hits)
                    answer = generate_answer(
                        prompt,
                        provider_name=provider,
                        model=model_override.strip() or None,
                    )

                    sources = [
                        format_source(hit, index)
                        for index, hit in enumerate(hits, start=1)
                    ]

            except OllamaError as exc:
                answer = str(exc)
                sources = []

            except Exception as exc:
                answer = f"Something went wrong: {exc}"
                sources = []

        st.markdown(answer)

        if sources:
            with st.expander("Sources checked"):
                for source in sources:
                    st.write(source)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )