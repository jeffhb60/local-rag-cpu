# FastAPI RAG Study Assistant

A document-grounded Retrieval-Augmented Generation application built with FastAPI, Jinja templates, ChromaDB, OpenAI embeddings, DeepSeek chat generation, and JSONL-based evaluation.

The application lets users upload documents, index them into a local vector database, ask questions against the indexed corpus, and evaluate retrieval/answer quality with repeatable test cases.

---

## Use Cases

This project is designed for workflows where users need reliable answers from a controlled document corpus instead of open-ended web or chatbot responses.

### 1. Study Aid for Course Materials

Students can upload course readings, rubrics, textbook excerpts, study guides, or lecture notes and ask questions against only those documents.

Example questions:

```text
What are the main requirements for this assignment?
What does the reading say about judicial review?
What are the key terms I should know for this chapter?
```

---

### 2. Legal Case Review
Users can upload legal opinions, case briefs, or statutory materials and ask targeted questions about holdings, reasoning, doctrines, and source language.
Example questions:
```text
What was the holding in Obergefell?
What test did the Court apply in Tinker?
What did McCulloch say about implied federal powers?
```

The system returns source-grounded answers with file, page, and chunk references.

---

### 3. Policy and Procedure Search
Organizations can upload internal policies, handbooks, process documents, or compliance materials and ask operational questions.

Example questions:
```text
What is the escalation process?
What does the policy say about deadlines?
Who is responsible for approval?
```
This reduces the need to manually search long PDFs or document folders.

---

### 4. Evaluation of RAG Quality
Developers can test whether retrieval and answer generation are working correctly by uploading JSONL evaluation sets.

The system reports:
* Whether the expected source document was retrieved 
* Whether expected concepts appeared in the answer 
* Which keywords matched 
* Which keywords were missing 
* Which results may need manual review

This makes the project useful not only as a chatbot, but as a measurable RAG pipeline.

---

## Project Purpose

This project demonstrates a practical, inspectable, and evaluable RAG system rather than a generic chatbot.  The goal 
is to also provide an affordable option that can be either run with a local llm or an affordable solution such as DeepSeek v4 pro
or other model. The code is structured so that only minimal changes are needed to the vector database and embeddings to work with 
another model.  This could be used by 

The goal is to answer user questions using only indexed documents while providing:

- Source-grounded answers
- Retrieved chunk metadata
- Document upload and reindexing workflows
- Background job progress tracking
- Runtime prompt controls
- Evaluation metrics for retrieval and answer quality

The system is designed to be useful for study materials, legal case summaries, course documents, reference PDFs, and other document-heavy workflows.

---

## Tech Stack

| Layer            | Technology                                                   |
|------------------|--------------------------------------------------------------|
| Backend          | FastAPI                                                      |
| Frontend         | Jinja2 templates, vanilla JavaScript, CSS                    |
| Vector database  | ChromaDB                                                     |
| Embeddings       | OpenAI `text-embedding-3-small`                              |
| Chat generation  | DeepSeek `deepseek-v4-pro`                                   |
| Document parsing | PyMuPDF, python-docx                                         |
| Chunking         | LangChain SemanticChunker + RecursiveCharacterTextSplitter   |
| Reranking        | sentence-transformers CrossEncoder                           |
| Evaluation       | JSONL test cases with source and keyword/concept scoring     |
| Job tracking     | In-memory background job manager                             |

---

## Core Features

### 1. Upload and Index Documents

Users can upload one or more documents through the web interface.

Supported file types:

- `.pdf`
- `.docx`
- `.txt`
- `.md`

Uploaded documents are saved to:

```text
data/docs/
```

The system then:

1. Extracts text from the document.
2. Splits text into semantic chunks.
3. Embeds each chunk using OpenAI embeddings.
4. Stores chunk text, embeddings, and metadata in ChromaDB.
5. Updates the local index state so unchanged files can be skipped later.

Upload and indexing run as a background job so the UI can show progress.

---

### 2. Reindex Documents

The Reindex page allows users to:

- Refresh the document list
- Reindex selected files
- Reindex the full corpus
- Force rebuild indexed documents

Reindexing also runs as a background job with live status updates.

The app avoids re-indexing unchanged files unless force rebuild is enabled. File state is tracked in:

```text
data/index_state.json
```

---

### 3. Chat with Indexed Documents

The Chat page lets users ask questions against the indexed corpus.

The chat provider and model are intentionally locked:

```text
Chat provider: DeepSeek
Chat model: deepseek-v4-pro
```

The embedding provider and model are also intentionally locked:

```text
Embedding provider: OpenAI
Embedding model: text-embedding-3-small
```

Runtime-adjustable settings:

- Top K
- Temperature
- Strict grounding mode
- System prompt
- RAG instruction template

The assistant is instructed to answer only from retrieved context and cite sources using file name, page number, and chunk number when available.

---

### 4. Reranking

The system can rerank vector search results with a local cross-encoder model.

Default reranker:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The retrieval flow is:

1. Retrieve candidate chunks from Chroma.
2. Filter weak matches by retrieval distance.
3. Rerank the strongest candidates with a cross-encoder.
4. Send the final selected chunks to the chat model.

This usually improves answer quality, but the first run may be slower because the reranker model may need to download.

---

### 5. Evaluation Workflow

The Evaluation page supports JSONL test files.

Each line should be one JSON object:

```json
{"question": "What did Marbury v. Madison establish about judicial review?", "expected_source_files": ["marbury_v_madison.pdf"], "expected_answer_keywords": ["judicial review", "Constitution", "Supreme Court"]}
```

Evaluation reports:

- Total passed
- Total failed
- Source hit rate
- Keyword hit rate
- Average keyword coverage
- Manual review candidates
- Matched keywords
- Missing keywords

This avoids treating one brittle pass/fail number as the entire truth.

---

## Why Evaluation Uses Multiple Metrics

RAG evaluation is not always cleanly captured by a single pass/fail score.

A response can retrieve the correct source and provide a useful answer while failing an exact keyword check because it uses a reasonable paraphrase.

For that reason, this project separates:

| Metric                  | Purpose                                                      |
|-------------------------|--------------------------------------------------------------|
| Source pass             | Did retrieval find the expected source document?             |
| Keyword pass            | Did the answer include the expected concepts or equivalents? |
| Strict pass             | Did both source and keyword checks pass?                     |
| Keyword coverage        | What share of expected concepts appeared in the answer?      |
| Manual review candidate | Was the answer close enough to deserve human review?         |

This makes failure analysis more useful.

---

## Configurable Evaluation Equivalents

Some expected terms have acceptable equivalents.

Example:

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
.
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── project_exporter.py
│
├── api/
│   ├── __init__.py
│   ├── routes.py
│   ├── routes_chat.py
│   ├── routes_documents.py
│   ├── routes_eval.py
│   ├── routes_jobs.py
│   └── schemas.py
│
├── core/
│   ├── __init__.py
│   ├── document_loader.py
│   ├── embeddings.py
│   ├── generator.py
│   ├── ingestion.py
│   ├── llm_factory.py
│   ├── progress.py
│   ├── reranker.py
│   ├── semantic_chunker.py
│   ├── state.py
│   └── vectorstore.py
│
├── eval/
│   ├── __init__.py
│   └── evaluator.py
│
├── data/
│   ├── docs/
│   ├── evaluation/
│   │   └── equivalents.json
│   └── index_state.json
│
├── static/
│   ├── shared.js
│   ├── upload.js
│   ├── reindex.js
│   ├── chat.js
│   ├── evaluation.js
│   └── styles.css
│
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

### 2. Check out the project branch

```bash
git checkout rag_deepseek_v4_pro_v1.0
```

### 3. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root.

```env
OPENAI_API_KEY=your_openai_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Required keys:

| Variable            | Purpose                                 |
|---------------------|-----------------------------------------|
| `OPENAI_API_KEY`    | Required for OpenAI embeddings          |
| `DEEPSEEK_API_KEY`  | Required for DeepSeek chat generation   |
| `DEEPSEEK_BASE_URL` | DeepSeek OpenAI-compatible API base URL |

Do not commit `.env` to GitHub.

---

## Run the App

```bash
uvicorn main:app --reload --port 8000 --access-log
```

Then open:

```text
http://127.0.0.1:8000
```

The root page redirects to:

```text
/upload
```

If port `8000` is already in use, use another port:

```bash
uvicorn main:app --reload --port 8001 --access-log
```

Then open:

```text
http://127.0.0.1:8001
```

---

## Web Pages

| Route         | Purpose                                  |
|---------------|------------------------------------------|
| `/upload`     | Upload and index documents               |
| `/reindex`    | Reindex selected or all documents        |
| `/chat`       | Ask questions against indexed documents  |
| `/evaluation` | Run JSONL evaluation                     |

---

## Typical Workflow

### 1. Upload documents

Go to:

```text
/upload
```

Upload one or more supported documents.

Supported types:

```text
.pdf
.docx
.txt
.md
```

The page starts a background indexing job and displays progress.

---

### 2. Reindex documents

Go to:

```text
/reindex
```

Use this page to:

- Refresh the document list
- Reindex selected files
- Reindex the full corpus
- Force rebuild documents

Use force rebuild when:

- A document was changed but has the same filename
- Chunking settings changed
- Embedding settings changed
- `index_version` changed
- Chroma data needs to be rebuilt

---

### 3. Ask questions

Go to:

```text
/chat
```

Example question:

```text
What did Marbury v. Madison establish about judicial review?
```

The assistant should answer using only retrieved document context.

---

### 4. Run evaluation

Go to:

```text
/evaluation
```

Upload a `.jsonl` file.

Example JSONL line:

```json
{"question": "What did McCulloch v. Maryland hold about implied federal powers?", "expected_source_files": ["mcculloch_v_maryland.pdf"], "expected_answer_keywords": ["implied powers", "Necessary and Proper Clause", "Congress"]}
```

The UI starts an evaluation job and polls for progress.

---

## API Endpoints

### Settings

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/settings` | Get current settings |
| `PUT` | `/api/settings` | Update allowed runtime settings |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/documents` | List available and indexed documents |
| `POST` | `/api/documents/upload/start` | Start upload/index background job |
| `POST` | `/api/documents/upload` | Synchronous upload/index endpoint |
| `POST` | `/api/documents/reindex/start` | Start full reindex background job |
| `POST` | `/api/documents/reindex-selected/start` | Start selected-file reindex background job |
| `POST` | `/api/documents/reindex` | Synchronous full reindex endpoint |

### Jobs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/jobs/{job_id}` | Get job status |
| `GET` | `/api/jobs` | List jobs |
| `DELETE` | `/api/jobs/finished` | Clear finished jobs |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/query` | Ask a RAG question |

### Evaluation

| Method | Endpoint                  | Description                     |
|--------|---------------------------|---------------------------------|
| `POST` | `/api/evaluate/run/start` | Start background evaluation job |
| `POST` | `/api/evaluate/run`       | Run synchronous evaluation      |

---

## Configuration

Configuration is centralized in:

```text
config.py
```

Important defaults:

```python
embedding_provider = "openai"
embedding_model = "text-embedding-3-small"

chat_provider = "deepseek"
chat_model = "deepseek-v4-pro"

top_k_default = 12
temperature_default = 0.3
strictness_mode = True

reranker_enabled = True
retrieval_candidate_k = 20
rerank_top_k = 5
max_retrieval_distance = 0.65
```

Provider and model choices are intentionally locked to keep the app focused and consistent.

Runtime-adjustable settings are exposed on the Chat page:

- Top K
- Temperature
- Strict grounding mode
- System prompt
- RAG instruction template

---

## Index Versioning

The app uses `index_version` to determine whether existing indexed files are current.

Current default:

```python
index_version = "semantic-v2-openai-embeddings"
```

If you change chunking, embeddings, parsing behavior, or metadata structure, update `index_version` in `config.py` and reindex the corpus.

Example:

```python
index_version = "semantic-v3-openai-embeddings"
```

Then force rebuild documents from the Reindex page.

---

## Background Jobs

Upload, reindex, and evaluation workflows run as background jobs.

Job state is stored in memory through `core/progress.py`.

This supports:

- Current status
- Current item count
- Total item count
- Progress messages
- Logs
- Result payload
- Error messages

Important limitations:

- Jobs are lost when the server reloads.
- Use one Uvicorn worker for local development.
- In-memory jobs are not suitable for production.

For production, replace the in-memory job manager with Redis, RQ, Celery, Dramatiq, or a database-backed job table.

---

## Evaluation Notes

Early test runs showed that exact keyword matching can undercount valid answers.

Example:

```text
Expected keyword:
questioning must cease

Valid answer phrase:
interrogation must immediately stop
```

The answer can be conceptually correct while failing a naive exact-match check.

To address this, the evaluator supports:

- Normalized text matching
- Singular/plural tolerance
- Content-token overlap
- Configurable phrase equivalents
- Manual review flags
- `equivalents.json` mappings

This produces more useful diagnostics than a single rigid pass/fail score.

---

## Troubleshooting

### `{"detail":"Not Found"}` when opening an endpoint

Browser address bars send `GET` requests.

Use page routes in the browser:

```text
/upload
/reindex
/chat
/evaluation
```

API routes such as `/api/documents/upload/start` require `POST` and should be called by the frontend, curl, Postman, or JavaScript.

---

### Upload or indexing fails with `OPENAI_API_KEY is required`

The app uses OpenAI embeddings.

Check that `.env` contains:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Then restart Uvicorn.

---

### Chat fails with `DEEPSEEK_API_KEY is required`

The app uses DeepSeek chat generation.

Check that `.env` contains:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Then restart Uvicorn.

---

### Reindex or upload appears stuck

Check the PowerShell or terminal running Uvicorn.

You should see progress messages such as:

```text
Starting ingest: example.pdf
Extracting text from: example.pdf
Semantic chunking example.pdf, page 1
Embedding batch 1/4 for: example.pdf
Writing batch 1/4 to Chroma for: example.pdf
Finished indexing example.pdf
```

Also check the browser DevTools Network tab for pending `/api/jobs/{job_id}` requests.

---

### First reranker run is slow

The reranker uses `sentence-transformers`.

The first run may download the cross-encoder model:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

This can take time depending on the network and machine.

To disable reranking, set this in `.env` or `config.py`:

```env
RERANKER_ENABLED=false
```

---

### Chroma telemetry warning

You may see messages like:

```text
Failed to send telemetry event...
```

These are Chroma telemetry warnings, not RAG failures.

If indexing and search work, this can usually be ignored.

---

### Scanned PDFs return poor answers

The app extracts embedded text from PDFs.

If a PDF is image-only or scanned, it may require OCR before indexing.

---

## Known Limitations

This is a local development project, not a production deployment.

Current limitations:

- Background jobs are stored in memory.
- Server reloads clear active job history.
- ChromaDB is local.
- No authentication is implemented.
- No persistent user management is implemented.
- Evaluation still relies partly on keyword/concept matching.
- Long evaluations can be slow because each test case performs retrieval and generation.
- Some documents may require OCR if they are scanned image-only PDFs.
- The current UI is designed for single-user local use.

---

## Production Improvements

Potential next steps:

- Move background jobs to Redis, RQ, Celery, or Dramatiq.
- Add persistent job storage.
- Add authentication and user accounts.
- Add document-level permissions.
- Add hybrid search using BM25 plus vector search.
- Add document metadata filters.
- Add OCR for scanned PDFs.
- Add latency and cost tracking.
- Add source coverage metrics.
- Add manual review export for failed or borderline evaluation cases.
- Add Docker support.
- Add deployment configuration.
- Add automated tests for routes and ingestion.
- Add CI checks for formatting and imports.

---

## Portfolio Value

This project demonstrates:

- Python backend development
- FastAPI routing and request handling
- Modular API route organization
- File upload workflows
- Document parsing
- Semantic chunking
- Vector database usage
- Embedding-based retrieval
- Cross-encoder reranking
- RAG prompt construction
- LLM API integration
- Source-grounded answer generation
- Background job tracking
- Frontend polling
- Evaluation design
- Failure analysis

The project is intended to show not just that a chatbot can be built, but that the system can be measured, debugged, and improved.

---

## License

MIT License

Copyright (c) 2026 Jeffrey H. Butt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and sell copies of the
Software, subject to the conditions of the MIT License.