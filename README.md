# Local RAG CPU Assistant

A simple local Retrieval-Augmented Generation (RAG) project for asking questions about local documents such as manuals, PDFs, Word documents, Markdown files, and text files.

This project runs locally using:

* **Ollama** for the local language model and embeddings
* **llama3.2:3b** as the local chat model
* **all-minilm** as the embedding model
* **ChromaDB** as the local vector database
* **Streamlit** for the browser-based chat interface
* **pypdf** for normal PDF text extraction
* **PyMuPDF** for rendering scanned PDF pages before OCR
* **Tesseract OCR** through `pytesseract` for scanned PDFs
* **python-docx** for Word document parsing
* **python-dotenv** for local `.env` configuration

The goal is to create a practical, CPU-friendly document assistant that can search your local files and answer questions using only the indexed document context.

The system does not send your documents to an external API. Document search, embeddings, and answer generation run locally through Ollama and ChromaDB.

## 1. What This Project Does
This project lets you:

1. Place documents into a local `docs/` folder or a private folder configured through `.env`.
2. Upload supported documents through a Streamlit browser interface.
3. Run an ingestion script that extracts text from those documents.
4. Use normal PDF text extraction first.
5. Fall back to OCR when a PDF page has little or no extractable embedded text.
6. Split extracted text into overlapping chunks.
7. Convert those chunks into embeddings using Ollama.
8. Store those embeddings in a local ChromaDB database.
9. Ask questions through either a Streamlit web interface or a command-line interface.
10. Retrieve the most relevant document chunks.
11. Send those chunks to a local LLM to generate an answer.
12. Display the answer and the sources checked.

## 2. Project Stack 

| Component | Tool | Purpose |
|:---|:---|:---|
| Local LLM | `llama3.2:3b` | Generates answers from retrieved context |
| Embeddings | `all-minilm` | Converts document chunks and questions into vectors |
| Vector Database | ChromaDB | Stores and searches document embeddings |
| Web Interface | Streamlit | Provides browser-based chat, file upload, and indexing controls |
| PDF Reader | pypdf | Extracts embedded text from PDF files |
| OCR Renderer | PyMuPDF | Renders scanned PDF pages as images for OCR |
| OCR Engine | Tesseract OCR | Reads text from scanned PDF images |
| OCR Wrapper | pytesseract | Lets Python call Tesseract |
| Word Reader | python-docx | Extracts text from `.docx` files |
| Config Loader | python-dotenv | Loads local settings from `.env` |
| HTTP Client | requests | Calls the local Ollama API |

## 3. Project Structure

```text
local-rag-cpu/
│
├── docs/
│   └── put your PDFs, DOCX, TXT, and MD files here
│
├── chroma_db/
│   └── local ChromaDB files are created here
│
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── config.py
├── ollama_client.py
├── loaders.py
├── splitter.py
├── store.py
├── ingest.py
├── ask.py
└── app.py
```

## 4. File Overview 

### 4a. `config.py`
Loads project settings from .env.

Important settings include:
* Document folder path
* ChromaDB folder path
* Chroma collection name
* Index version
* Ollama URL
* Chat model name
* Embedding model name
* Chunk size
* Chunk overlap
* Number of retrieved chunks
* Embedding and generation timeouts
* OCR settings
* Tesseract executable path

### 4b. `ollama_client.py`
Wraps the Ollama API calls. 

Main functions: 
* `embed_one(text)`
* `embed_many(texts)`
* `generate(prompt)`

This keeps the Ollama-specific code separate from the rest of the project.

### 4c. `loaders.py`
Reads files from disk and extracts text.
Supported file types: 
* `.pdf`
* `.docx`
* `.txt`
* `.md`

For PDFs, the loader first tries normal embedded text extraction with `pypdf`.

If the extracted text is too short, the loader can fall back to OCR:
1. PyMuPDF renders the PDF page as an image.
2. Tesseract OCR reads the image.
3. The OCR text is used if it is better than the extracted PDF text.

### 4d. `splitter.py`
Splits large text into smaller overlapping chunks.

This matters because the LLM should not receive an entire manual at once. Instead, the system retrieves only the most 
relevant sections.

### 4e. `store.py`
Creates or opens the local ChromaDB collection.

### 4f. `ingest.py`
Indexes documents into ChromaDB.

This script:
1. Finds supported files in DOCS_DIR. 
2. Loads text from each file. 
3. Uses OCR when needed and enabled. 
4. Splits the text into chunks. 
5. Creates embeddings for each chunk. 
6. Stores the chunks, embeddings, and metadata in ChromaDB. 
7. Skips files that are already indexed with the same file stamp. 
8. Uses `INDEX_VERSION` to force reindexing when extraction logic changes.

### 4g. `ask.py`
Runs the command-line question-answering interface.

This script:
1. Accepts a user question.
2. Embeds the question.
3. Searches ChromaDB for relevant chunks.
4. Builds a prompt using those chunks.
5. Sends the prompt to the local LLM.
6. Prints the answer and the sources checked.

### 4h. `app.py`

Runs the Streamlit web interface.

This app:
1. Opens a browser-based chat interface.
2. Lets you upload supported documents into `DOCS_DIR`.
3. Lets you run `ingest.py` from the sidebar.
4. Sends questions through the same local RAG pipeline used by `ask.py`.
5. Displays answers in chat format.
6. Shows the retrieved source chunks used for the answer.
7. Lets you clear the current chat session.

## 5. Requirements
Before running this project, install:
* Python 3.10 or newer
* Ollama
* Tesseract OCR
* The required Ollama models
* The Python dependencies in `requirements.txt`

## 6. Install Ollama Models
Run these commands:
```bash
ollama pull llama3.2:3b
ollama pull all-minilm
```

You can test the chat model with:
```bash 
ollama run llama3.2:3b
```

Exit the Ollama with: 
```bash 
/bye
```

## 7. Install Tesseract OCR
OCR requires the Tesseract OCR application, not just the Python package.
### 7a. Windows
Install Tesseract OCR.
A common install path is:
```text
C:/Program Files/Tesseract-OCR/tesseract.exe
```
Set this path in your `.env` file:
```text
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```
### 7b. macOS
Install with Homebrew:
```bash
brew install tesseract
```
If Tesseract is on your system PATH, you can leave `TESSERACT_CMD` blank.

### 7c. Linux
Install with apt: 
```bash
sudo apt install tesseract-ocr
```
If Tesseract is on your system PATH, you can leave `TESSERACT_CMD` blank.

## 8. Python Setup
From the project folder: 
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
On macOS or Linux: 
```bash 
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 9. Dependencies
The `requirements.txt` file should include: 
```depenencies 
chromadb==1.5.8
pillow==12.2.0
PyMuPDF==1.27.2.3
pypdf==6.10.2
pytesseract==0.3.13
python-docx==1.2.0
python-dotenv==1.2.2
requests==2.33.1
streamlit==1.56.0
tqdm==4.67.3
```

To check installed versions:
```bash 
pip show chromadb pillow PyMuPDF pypdf pytesseract python-docx python-dotenv requests streamlit tqdm
```

## 10. Environment Configuration
Create a `.env` file in the same folder as the `config.py`. 

Example:
```env
# Local RAG paths
DOCS_DIR=docs
DB_DIR=chroma_db

# ChromaDB
COLLECTION=manuals
INDEX_VERSION=streamlit-v1

# Ollama
OLLAMA_URL=http://localhost:11434
CHAT_MODEL=llama3.2:3b
EMBED_MODEL=all-minilm

# Chunking
CHUNK_CHARS=1000
CHUNK_OVERLAP=180

# Ingestion / retrieval
EMBED_BATCH_SIZE=16
TOP_K=5

# Timeouts
GENERATE_TIMEOUT=300
EMBED_TIMEOUT=180

# OCR
OCR_ENABLED=true
OCR_MIN_TEXT_CHARS=40
OCR_DPI=200
OCR_LANG=eng
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```
If you want to keep documents outside the project folder, use an absolute path:
```env
DOCS_DIR=C:/Users/YourName/Documents/private_rag_docs
DB_DIR=C:/Users/YourName/Documents/private_rag_db
```

Do not commit your real `.env` file to any repositories or anything else that is public facing. We recommend using 
.gitignore to filter this.  Here is a recommended .gitignore: 
```gitignore
.env
docs/
chroma_db/
__pycache__/
.venv/
```

## 11. Add Documents 
You can add documents in either of two ways.

### 11a. Add files manually

Place your files in the configured documents folder.

By default this is `docs/`.

Supported formats include:

```text
.pdf
.docx
.txt
.md
```

Example:

```text
local-rag-cpu/
└── docs/
    ├── The_Grapes_of_Wrath_Full_Text.pdf
    ├── The_Grapes_of_Wrath_Wikipedia.pdf
```

### 11b. Upload files through Streamlit

Run the Streamlit app:

```bash
streamlit run app.py
```

Then use the sidebar file uploader to upload supported files. Uploaded files are saved into the configured `DOCS_DIR`.

After uploading files, click **Index / Reindex Documents** in the sidebar.

## 12. Ingest Documents
You can index documents from the command line or from the Streamlit app.

### 12a: Command line

Run:

```bash
python ingest.py
```

Expected output looks similar to:

```text
The_Grapes_of_Wrath_Full_Text.pdf: 100%|██████████| 92/92 [04:07<00:00,  2.70s/it]
indexed: The_Grapes_of_Wrath_Full_Text.pdf (1470 chunks, 0 OCR chunks)
The_Grapes_of_Wrath_Wikipedia.pdf: 100%|██████████| 4/4 [00:10<00:00,  2.73s/it]
indexed: The_Grapes_of_Wrath_Wikipedia.pdf (64 chunks, 0 OCR chunks)
done
```

If a document has already been indexed and has not changed, it may be skipped:

```text
skipped: The_Grapes_of_Wrath_Full_Text.pdf is already indexed
skipped: The_Grapes_of_Wrath_Wikipedia.pdf is already indexed
done
```

The ingestion step creates or updates the local ChromaDB database in the configured `DB_DIR`.

### 12b: Streamlit app

Run:

```bash
streamlit run app.py
```

Then click **Index / Reindex Documents** in the sidebar.

The app runs `ingest.py` and displays the output in the browser.

## 13. Reindexing Documents
The project uses a file stamp to avoid reindexing unchanged files.

The file stamp includes:

* File path
* File size
* File modified time
* `INDEX_VERSION`

If you change extraction behavior, OCR settings, chunking logic, or metadata logic, update this value in `.env`:

```env
INDEX_VERSION=streamlit-v2
```

Then rerun one of the following:

```bash
python ingest.py
```

or:

```bash
streamlit run app.py
```

Then click **Index / Reindex Documents**.

This forces the project to treat the documents as needing a fresh index.

## 14. Ask Questions 
After ingestion finishes, run:

```bash
streamlit run app.py
```

Then ask a question in the chat box:

```text
Why was the Joad family going to California?
```

The app will:

1. Embed the question.
2. Search ChromaDB for relevant chunks.
3. Build a prompt using the retrieved chunks.
4. Send the prompt to the local Ollama chat model.
5. Display the answer.
6. Show the sources checked in an expandable section.

## 15. Ask Questions from the Command Line

The command-line interface is still available.

After ingestion finishes, run:

```bash
python ask.py
```

Then ask a question:

```text
Ask: Why was the Joad family going to California?
```

Example output:

```text
According to [1] The_Grapes_of_Wrath_Wikipedia.pdf, page 2, chunk 4 and [2] The_Grapes_of_Wrath_Wikipedia.pdf, page 2, chunk 3:

The Joad family was going to California in search of work and a better life. They had heard that California offered high pay and were willing to take the risk of leaving their farm behind due to the devastating effects of the Dust Bowl.

Sources checked:
1. The_Grapes_of_Wrath_Wikipedia.pdf p.2 (chunk 4, distance 0.8339)
2. The_Grapes_of_Wrath_Wikipedia.pdf p.2 (chunk 3, distance 0.9135)
```

To exit:

```text
exit
```

You can also exit with:

```text
quit
q
```

## 16. Normal Workflow
### 16a. Browser workflow

After setup, the usual Streamlit workflow is:

```bash
.venv\Scripts\activate
streamlit run app.py
```

On macOS or Linux:

```bash
source .venv/bin/activate
streamlit run app.py
```

Then use the browser app to:

1. Upload documents.
2. Index or reindex documents.
3. Ask questions.
4. Review sources checked.

### 16b. Command-line workflow

You can still use the command-line workflow:

```bash
.venv\Scripts\activate
python ingest.py
python ask.py
```

On macOS or Linux:

```bash
source .venv/bin/activate
python ingest.py
python ask.py
```

Run `python ingest.py` again whenever you add, remove, or update documents in the configured documents folder.

## 17. How the RAG Flow Works

```text
Local documents
      ↓
Text extraction
      ↓
OCR fallback if needed
      ↓
Chunking
      ↓
Embeddings
      ↓
ChromaDB storage
      ↓
User question
      ↓
Question embedding
      ↓
Similarity search
      ↓
Relevant chunks
      ↓
Local LLM answer
      ↓
Answer and sources shown in Streamlit or CLI
```

The language model does not read every document every time. It only receives the chunks that ChromaDB finds most relevant to the question.

That is what makes this practical on CPU.

## 18. Chunking 
Documents are usually too large to send directly to a small local model.

Chunking breaks the document into smaller sections.

The current settings are:

```python
CHUNK_CHARS = 1000
CHUNK_OVERLAP = 180
```

This means each chunk is about 1,000 characters long, with 180 characters of overlap between neighboring chunks.

The overlap helps preserve context when an answer spans the boundary between two chunks.

If you change chunking settings, consider bumping `INDEX_VERSION` and rerunning ingestion.

## 19. Current Retrieval Settings
The project currently retrieves the top 5 matching chunks by default: 
```python
TOP_K = 5
```
If answers feel incomplete, increase this to:
```python
TOP_K = 8
```
If answers are too slow or include too much irrelevant context, reduce it to:
```python
TOP_K = 3
```

## 20. OCR Settings

OCR is controlled through `.env`.

```env
OCR_ENABLED=true
OCR_MIN_TEXT_CHARS=40
OCR_DPI=200
OCR_LANG=eng
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### 20a. `OCR_ENABLED`

Turns OCR fallback on or off.

```env
OCR_ENABLED=false
```

### 20b. `OCR_MIN_TEXT_CHARS`

If normal PDF text extraction returns fewer characters than this threshold, OCR is attempted.

```env
OCR_MIN_TEXT_CHARS=40
```

### 20c. `OCR_DPI`

Controls image rendering quality before OCR.

Higher values may improve OCR quality but will slow ingestion.

```env
OCR_DPI=200
```

### 20d. `OCR_LANG`

Sets the Tesseract OCR language.

English:

```env
OCR_LANG=eng
```

Spanish:

```env
OCR_LANG=spa
```

Multiple languages may be possible if installed:

```env
OCR_LANG=eng+spa
```

## 21. CPU Performance Notes

This project is designed for CPU-first use.

Expected behavior:

| Task | CPU Performance |
|:---|:---|
| Ingesting small text files | Fast |
| Ingesting normal text-based PDFs | Moderate |
| Ingesting scanned PDFs with OCR | Slower |
| Asking short questions | Usable |
| Asking broad summary questions | Slower |
| Running large models | Not recommended |

The model `llama3.2:3b` is a practical starting point for CPU use. Larger models may provide better answers but will usually be slower without a GPU.

OCR can be significantly slower than normal PDF text extraction because each scanned page must be rendered and processed as an image.

## 22. Troubleshooting

### 22a. Error Message: `Could not reach Ollama. Start it, then try again.`

Ollama is not running.

Try:

```bash
ollama serve
```

Or open the Ollama desktop application if you installed the desktop version.

### 22b. Error Message: `model not found`

The required model has not been downloaded.

Run:

```bash
ollama pull llama3.2:3b
ollama pull all-minilm
```

### 22c. Error Message: `No files found in docs`

The configured documents folder is empty or the files are not supported.

Check your `.env`:

```env
DOCS_DIR=docs
```

Supported extensions:

```text
.pdf
.docx
.txt
.md
```

You can also upload supported files through the Streamlit sidebar.

### 22d. Streamlit command not found

Streamlit is not installed in the active Python environment.

Run:

```bash
pip install -r requirements.txt
```

Then try again:

```bash
streamlit run app.py
```

### 22e. Streamlit opens but answers fail

Possible causes:

* Ollama is not running.
* The chat model has not been pulled.
* The embedding model has not been pulled.
* Documents have not been indexed yet.
* ChromaDB is empty.

Try:

```bash
ollama serve
ollama pull llama3.2:3b
ollama pull all-minilm
python ingest.py
streamlit run app.py
```

### 22f. Uploaded files do not show up in answers

Uploading a file only saves it into `DOCS_DIR`. The file still needs to be indexed.

After uploading, click **Index / Reindex Documents** in the Streamlit sidebar.

### 22g. PDF produces weak or missing text

Possible causes:

* The PDF is scanned.
* OCR is disabled.
* Tesseract is not installed.
* `TESSERACT_CMD` points to the wrong location.
* The scan quality is poor.
* The OCR language is wrong.

Check these `.env` values:

```env
OCR_ENABLED=true
OCR_MIN_TEXT_CHARS=40
OCR_DPI=200
OCR_LANG=eng
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```

If OCR still fails, try increasing DPI:

```env
OCR_DPI=300
```

Then bump the index version:

```env
INDEX_VERSION=ocr-v2
```

Then rerun:

```bash
python ingest.py
```

or reindex from the Streamlit sidebar.

### 22h. OCR failed for page

If you see output like:

```text
OCR failed for scanned_contract.pdf page 3: ...
```

Check that:

1. Tesseract OCR is installed.
2. `pytesseract` is installed.
3. `PyMuPDF` is installed.
4. `pillow` is installed.
5. `TESSERACT_CMD` is correct.

On Windows, the path often needs to be:

```env
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### 22i. Answers are weak or vague

Possible causes:

* The relevant document was not indexed.
* The PDF text extraction was poor.
* OCR was needed but failed.
* The chunk size is too small.
* `TOP_K` is too low.
* The question is too broad.

Try:

```env
TOP_K=8
CHUNK_CHARS=1200
CHUNK_OVERLAP=250
INDEX_VERSION=chunk-v2
```

Then rerun:

```bash
python ingest.py
streamlit run app.py
```

or:

```bash
python ingest.py
python ask.py
```

### 22j. Answers include information not in the documents

The prompt tells the model to use only retrieved context, but small local models can still drift.

Possible improvements:

* Lower the temperature in `ollama_client.py`.
* Retrieve fewer but more relevant chunks.
* Improve chunking.
* Add reranking.
* Use a stronger local model if hardware allows.

Current default temperature:

```text
"temperature": 0.1
```

### 22k. `.env` values are not loading

Make sure:

1. The `.env` file is in the same folder as `config.py`.
2. `config.py` calls `load_dotenv(BASE_DIR / ".env")`.
3. `python-dotenv` is installed.
4. You restarted the script after editing `.env`.

Test with:

```bash
python -c "from config import DOCS_DIR, OCR_ENABLED; print(DOCS_DIR, OCR_ENABLED)"
```

## 23. Limitations

This is a simple local RAG system.

Known limitations:

* OCR quality depends on scan quality.
* OCR can be slow on large scanned PDFs.
* Streamlit is intended for a local or lightweight browser interface, not a hardened multi-user production app.
* No user authentication.
* No advanced document cleanup.
* No reranking.
* No hybrid keyword/vector search.
* No automatic file change detection.
* No conversation memory across separate app sessions.
* No document delete command beyond reingestion behavior.
* Small local models may still hallucinate if retrieved context is weak.

## 24. Possible Upcoming Improvements

Good next upgrades:

1. Add hybrid search with keyword and vector retrieval.
2. Add reranking for better source selection.
3. Add source previews before answering.
4. Add document delete/reindex commands.
5. Add a simple test suite.
6. Add structured logging.
7. Add Docker support.
8. Add an `.env.example` template.
9. Add OCR confidence reporting.
10. Add OCR-only mode for scanned document batches.

## 25. License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 26. Contact

For questions, open a GitHub issue or contact me through my GitHub profile.