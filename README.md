# FastAPI RAG Study Assistant

A document-grounded Retrieval-Augmented Generation (RAG) study assistant built with FastAPI, ChromaDB, OpenAI embeddings, and DeepSeek chat generation.

The application lets users upload course or reference documents, index them into a local vector database, ask questions against the indexed corpus, and evaluate retrieval/answer quality using JSONL test cases.

---

## Project Purpose


This project is designed to demonstrate a practical, evaluable RAG system rather than a generic chatbot.

The goal is to answer user questions using only indexed documents while providing source citations and measurable evaluation results.

The system supports:

- Document upload and indexing
- Semantic chunking
- Vector search with ChromaDB
- Document-grounded chat responses
- Runtime prompt and retrieval controls
- Background job progress tracking
- Automated evaluation with source and keyword scoring
- Configurable keyword-equivalent mappings for fairer evaluation

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | Jinja2 templates, vanilla JavaScript, CSS |
| Vector database | ChromaDB |
| Embeddings | OpenAI `text-embedding-3-small` |
| Chat generation | DeepSeek `deepseek-v4-pro` |
| Document parsing | PyMuPDF, python-docx |
| Chunking | LangChain SemanticChunker + RecursiveCharacterTextSplitter |
| Evaluation | JSONL test cases with source and answer-concept checks |

---

## Core Features

### 1. Upload and Index Documents

Users can upload one or more supported documents through the web interface.

Supported file types:

- `.pdf`
- `.docx`
- `.txt`
- `.md`

Uploaded documents are saved to the local document directory, parsed, chunked, embedded, and stored in ChromaDB.

The upload workflow runs as a background job and reports progress through the UI.

---

### 2. Reindex Documents

The Reindex page allows users to:

- Refresh the document list
- Reindex selected files
- Reindex the full corpus
- Force rebuild indexed documents

Reindexing also runs as a background job with live progress updates.

---

### 3. Chat with Indexed Documents

The Chat page lets users ask questions against the indexed corpus.

The chat provider and model are intentionally locked:

```text
Chat provider: DeepSeek
Chat model: deepseek-v4-pro

```

The embedding provider and model are also locked:
```text
Embedding provider: OpenAI
Embedding model: text-embedding-3-small
```

Runtime-adjustable settings:
* Top K retrieval count 
* Temperature 
* Strict grounding mode 
* System prompt 
* RAG instruction template

The assistant is instructed to answer only from retrieved context and cite sources using source numbers, file names, pages, and chunk numbers when available.

---

### 4. Evaluation Workflow

The Evaluation page supports JSONL test files.

Each line in the JSONL file should look like this:
```json
{"question": "What did Marbury v. Madison establish about judicial review?", "expected_source_files": ["marbury_v_madison.pdf"], "expected_answer_keywords": ["judicial review", "Constitution", "Supreme Court"]}
```

Evaluation runs in the background and reports progress as each test case is processed.

The evaluator reports:
* Strict pass count 
* Source hit rate 
* Keyword hit rate 
* Average keyword coverage 
* Manual review candidates 
* Matched keywords 
* Missing keywords

This avoids treating one brittle pass/fail score as the entire truth.

---

## Why Evaluation Is Split into Multiple Metrics

RAG evaluation is not always cleanly captured by a single pass/fail number.

A response can retrieve the correct source and provide a useful answer while failing an exact keyword check because it uses a reasonable paraphrase.

For that reason, this project separates:

| Metric                  | Purpose                                                      |
|-------------------------|--------------------------------------------------------------|
| Source pass             | Did retrieval find the expected source document?             |
| Keyword pass            | Did the answer include the expected concepts or equivalents? |
| Strict pass             | Did both source and keyword checks pass?                     |
| Keyword coverage        | What share of expected concepts appeared in the answer?      |
| Manual review candidate | Was the answer close enough to deserve human review?         |

This makes failure analysis more honest and useful.

---

## Configurable Evaluation Equivalents

Some expected terms have acceptable equivalents.

For example:
```text
Expected: questioning must cease
Acceptable: interrogation must immediately stop
```

These mappings are stored in: 
```text
data/evaluation/equivalents.json
```

Example:
```json
{
  "questioning must cease": [
    "questioning must cease",
    "questioning must stop",
    "interrogation must cease",
    "interrogation must stop",
    "interrogation must immediately stop",
    "cannot resume until an attorney is present",
    "no questioning can occur"
  ],
  "right to counsel": [
    "right to counsel",
    "right to the assistance of counsel",
    "right to an attorney",
    "assistance of counsel",
    "appointed counsel"
  ]
}
```
This allows domain experts or instructors to add acceptable terminology without editing Python code.

---

## Project Structure

```text
├── main.py
├── config.py
├── requirements.txt
├── api/
│   ├── __init__.py
│   ├── routes.py
│   └── schemas.py
├── core/
│   ├── __init__.py
│   ├── document_loader.py
│   ├── embeddings.py
│   ├── generator.py
│   ├── ingestion.py
│   ├── llm_factory.py
│   ├── progress.py
│   ├── semantic_chunker.py
│   ├── state.py
│   └── vectorstore.py
├── eval/
│   ├── __init__.py
│   └── evaluator.py
├── data/
│   ├── docs/
│   ├── evaluation/
│   │   └── equivalents.json
│   └── index_state.json
├── static/
│   ├── shared.js
│   ├── upload.js
│   ├── reindex.js
│   ├── chat.js
│   ├── evaluation.js
│   └── styles.css
└── templates/
    ├── base.html
    ├── upload.html
    ├── reindex.html
    ├── chat.html
    ├── evaluation.html
    └── index.html
```

---

## Installation 

### 1. Clone the repository 
```bash
git clone https://github.com/jeffhb60/rag-project.git
cd rag-project
```

### 2. Create a virtual environment
On Windows PowerShell
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. git checkout branch-name
```bash
git checkout rag_deepseek_v4_pro_v1.0
```

### 4. Install dependencies 
pip install -r requirements.txt 

---

## Environment Variables
Create a `.env` file in the porject root. 
```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

OPENAI_API_KEY=your_openai_api_key_here
```

---

## Run the App

```bash
uvicorn main:app --reload --port 8000 --access-log
```

Then open 
```bash
http://127.0.0.1:8000
```
The app redirects to the Upload page.

---

## Typical Workflow

### 1. Upload documents
Go to: 
```text
/upload
```

Upload PDFs, DOCX, TXT, or Markdown files. 

The page will show indexing progress. 

---

### 2. Reindex if needed
Go to: 
```text
/reindex
```

Use this page to refresh the document list, reindex selected files, or rebuild the entire vector index.

---

### 3. Ask questions 
Go to: 
```text
/chat
```

Ask questions about the indexed documents.

Example: 

```text
What did Marbury v. Madison establish about judicial review?
```

The assistant should answer only from retrieved context and cite sources.

---

### 4. Run evaluation 
Go to: 
```text
/evaluation
```

Upload a JSONL test file. 

Example JSONL line: 
```text
{"question": "What did McCulloch v. Maryland hold about implied federal powers?", "expected_source_files": ["mcculloch_v_maryland.pdf"], "expected_answer_keywords": ["implied powers", "Necessary and Proper Clause", "Congress"]}
```

The UI shows progress as each test case runs.

---

## API Endpoints 

### Pages 

| Route                  | Description                              |
|------------------------|------------------------------------------|
| `/upload`              | Upload and index documents               |
| `/reindex`             | Reindex selected or all documents        |
| `/chat`                | Ask questions against indexed documents  |
| `/evaluation`          | Run JSONL evaluation                     |

### API 

| Method   | Endpoint                                | Description                          | 
|----------|-----------------------------------------|--------------------------------------|
| `GET`    | `/api/settings`                         | Get current settings                 | 
| `PUT`    | `/api/settings`                         | Update allowed runtime settings      |
| `GET`    | `/api/documents`                        | List available and indexed documents |
| `POST`   | `/api/documents/upload/start`           | Start upload/index background job    |
| `POST`   | `/api/documents/reindex/start`          | Start full reindex background job    | 
| `POST`   | `/api/documents/reindex-selected/start` | Start selected-file reindex job      |
| `GET`    | `/api/jobs/{job_id}`                    | Poll job status                      |
| `GET`    | `/api/jobs`                             | List jobs                            |
| `DELETE` | `/api/jobs/finished`                    | Clear finished jobs                  | 
| `POST`   | `/api/query`                            | Ask a RAG question                   |
| `POST`   | `/api/evaluate/run/start`               | Start background evaluation job      |
| `POST`   | `/api/evaluate/run`                     | Run synchronous evaluation           |

---

## Configuration 

Configuration is centralized in `config.py`

Important defaults: 

```Python
top_k_default = 8
temperature_default = 0.3
strictness_mode = True
embedding_model = "text-embedding-3-small"
chat_model = "deepseek-v4-pro"
```

The app intentionally locks provider/model choices to reduce UI complexity and keep the system focused.

Runtime-adjustable settings are exposed on the Chat page:
* Top K
* Temperature
* Strict grounding mode
* System prompt
* RAG instruction template

---

## Current Evaluation Findings

Early test runs showed that exact keyword matching can undercount valid answers.

For example, an answer may say:
```text
interrogation must immediately stop
```

while the expected keyword is: 
```text
questioning must cease
```

The answer is conceptionally correct but a naive exact keyword match would mark it wrong. 

To address this the evaluator now supports: 
* normalized text matching 
* singular/plural tolerance 
* content-token overlap 
* configurable phrase equivalents 
* manual review flags
* `equivalents.json` file where known equivalents can be mapped.  

This produces more useful diagnostics than a single rigid score.

--- 

## Known Limitations 

This is a local development project, not a production deployment.

Current limitations:
* Background jobs are stored in memory.
* Uvicorn should be run with one worker. 
* Server reloads clear active job history. 
* ChromaDB is local. 
* Evaluation still relies partly on keyword/concept matching. 
* No authentication is implemented. 
* No persistent user management is implemented. 
* Long evaluations can be slow because each test case performs retrieval and generation. 
* Some documents may require OCR if they are scanned image-only PDFs.

---

## Production Improvements

Potential next steps:
* Move background jobs to Redis, RQ, Celery, or Dramatiq.
* Add persistent job storage.
* Add authentication.
* Add reranking after vector retrieval.
* Add hybrid search using BM25 plus vector search.
* Add document-level metadata filters.
* Add OCR for scanned PDFs.
* Add latency and cost tracking.
* Add source coverage metrics.
* Add manual review export for failed or borderline evaluation cases.
* Add Docker support.
* Add deployment configuration.

---

## Final 
Portfolio Value

This project demonstrates:
* Python backend development 
* FastAPI routing and request handling 
* File upload workflows 
* Document parsing 
* Semantic chunking 
* Vector database usage 
* Embedding-based retrieval 
* RAG prompt construction 
* LLM API integration 
* Source-grounded answer generation 
* Background job tracking 
* Frontend polling 
* Evaluation design 
* Failure analysis

The project is intended to show not just that a chatbot can be built, but that the system can be measured, debugged, and improved.

---

## License

```text
MIT License

Copyright (c) 2026 Jeffrey H. Butt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction.
```