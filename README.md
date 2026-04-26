# Local RAG CPU Assistant

A simple local Retrieval-Augmented Generation (RAG) project for asking questions about local documents such as manuals, 
PDFs, Word documents, Markdown files, and text files.

This project runs locally using:
* **Ollama** for the local language model and embeddings
* **llama3.2:3b** as the local chat model
* **all-minilm** as the embedding model
* **ChromaDB** as the local vector database
* **pypdf** for PDF parsing
* **python-docx** for Word document parsing

The goal is to create a practical, CPU-friendly document assistant that can search your local files and answer 
questions using only the indexed document context.

---

## 1. What This Project Does
This project lets you:

1. Place documents into a local docs/ folder.
2. Run an ingestion script that extracts text from those documents.
3. Split the extracted text into overlapping chunks.
4. Convert those chunks into embeddings using Ollama.
5. Store those embeddings in a local ChromaDB database.
6. Ask questions through a command-line interface.
7. Retrieve the most relevant document chunks.
8. Send those chunks to a local LLM to generate an answer.

The system does not send your documents to an external API. The document search and language model run locally through 
Ollama and ChromaDB.

## 2. Project Stack 


| **Component** | **Tool** | **Purpose**                                         |
|:---|:---|:--|
| Local LLM | `llama3.2:3b` | Generates answers from retrieved context            |
| Embeddings | `all-minilm` | Converts document chunks and questions into vectors |
| Vector Database | ChromaDB | Stores and searches document embeddings             | 
| PDF Reader | pypdf | Extracts text from PDF files                        | 
| Word reader | python-docx | Extract text from `.docx` files                     | 
| HTTP client | requests | Calls the local Ollama API                          | 

## 3. Project Structure

```file_structure 
local-rag-cpu/
│
├── docs/
│   └── put your PDFs, DOCX, TXT, and MD files here
│
├── chroma_db/
│   └── local ChromaDB files are created here
│
├── .gitignore
├── README.md
├── requirements.txt
├── config.py
├── ollama_client.py
├── loaders.py
├── splitter.py
├── store.py
├── ingest.py
└── ask.py
```

## 4. File Overview 

### 4a. `config.py`
* Stores project settings such as 
* Document folder path
* ChromaDB folder path
* Chroma collection name
* Ollama URL
* Chat model name
* Embedding model name
* Chunk size
* Chunk overlap
* Number of retrieved chunks

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
PDF files include page metadata when text is extracted successfully.

### 4d. `splitter.py`
Splits large text into smaller overlapping chunks.

This matters because the LLM should not receive an entire manual at once. Instead, the system retrieves only the most 
relevant sections.

### 4e. `store.py`
Creates or opens the local ChromaDB collection.

### 4f. `ingest.py`
Indexes documents into ChromaDB.

This script:
1. Finds supported files in docs/.
2. Loads text from each file.
3. Splits the text into chunks.
4. Creates embeddings for each chunk.
5. Stores the chunks, embeddings, and metadata in ChromaDB.

### 4g. `ask.py`
Runs the command-line question-answering interface.

This script:
1. Accepts a user question.
2. Embeds the question.
3. Searches ChromaDB for relevant chunks.
4. Builds a prompt using those chunks.
5. Sends the prompt to the local LLM.
6. Prints the answer and the sources checked.

## 5. Requirements
Before running this project, install:
* Python 3.10 or newer
* Ollama
* The required Ollama models
* The Python dependencies in requirements.txt

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

## 7. Python Setup
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

## 8. Dependencies
The `requirements.txt` file should include: 
```depenencies 
chromadb==1.5.8
requests==2.33.1
pypdf==6.10.2
python-docx==1.2.0
tqdm==4.67.3
```

To check installed versions:
```bash 
pip show chromadb requests pypdf python-docx tqdm
```

## 9. Add Documents 
Place your files in the docs/ folder. 

Supported formats: 
```list
.pdf
.docx
.txt
.md
```

Example: 
```file_structure
RAG_Project/
└── docs/
    ├── The_Grapes_of_Wrath_Full_Text.pdf
    ├── The_Grapes_of_Wrath_Wikipedia.pdf
```

## 10. Ingest Documents
Run: 
```bash
python ingest.py
```
Expected output looks similiar to: 
```output
The_Grapes_of_Wrath_Full_Text.pdf: 100%|██████████| 92/92 [04:07<00:00,  2.70s/it]
indexed: The_Grapes_of_Wrath_Full_Text.pdf (1470 chunks)
The_Grapes_of_Wrath_Wikipedia.pdf: 100%|██████████| 4/4 [00:10<00:00,  2.73s/it]
indexed: The_Grapes_of_Wrath_Wikipedia.pdf (64 chunks)
done
```
The ingestion step creates or updates the local ChromaDB database in the `chroma_db` directory. 

## 11. Ask Questions 
After ingestion finishes, run: 
```bash
python ask.py
```
Then ask a question:
```output
Ask: Why was the Joad family going to California?
```

Example output: 
```output
According to [1] The_Grapes_of_Wrath_Wikipedia.pdf, page 2, chunk 4 and [2] The_Grapes_of_Wrath_Wikipedia.pdf, page 2, chunk 3:

The Joad family was going to California in search of work and a better life. They had heard that California offered high pay and were willing to take the risk of leaving their farm behind due to the devastating effects of the Dust Bowl.

In [4] The_Grapes_of_Wrath.pdf, page 221, chunk 648:

The Joad family was also going to California because they had no other option left. They had lost their farm and were struggling to survive in Oklahoma, so they decided to seek work in California.

It is not explicitly stated that the Joad family's motivation for moving to California was solely economic, but it seems to be a major factor.

Sources checked:
1. The_Grapes_of_Wrath_Wikipedia.pdf p.2 (chunk 4, distance 0.8339)
2. The_Grapes_of_Wrath_Wikipedia.pdf p.2 (chunk 3, distance 0.9135)
3. The_Grapes_of_Wrath_Wikipedia.pdf p.2 (chunk 7, distance 0.9357)
4. The_Grapes_of_Wrath.pdf p.221 (chunk 648, distance 0.9463)
5. The_Grapes_of_Wrath_Full_Text.pdf p.221 (chunk 648, distance 0.9463)
```
To exit: 
```script
exit
```
You can also exit with: 
```script
quit
q
```

## 11. Normal Workflow
After the first step, the usual workflow is: 
```bash 
.venv\Scripts\activate
python ingest.py
python ask.py
```
Run python `ingest.py` again whenever you add, remove, or update documents in the `docs/` folder.

## 12. How the RAG Flow Works 
```diagram
Local documents
      ↓
Text extraction
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
```
The language model does not read every document every time. It only receives the chunks that ChromaDB finds most relevant to the question.

That is what makes this practical on CPU.

## 13. Chunking 
Documents are usually too large to send directly to a small local model.

Chunking breaks the document into smaller sections.

The current settings are:
```script 
CHUNK_CHARS = 1000
CHUNK_OVERLAP = 180
```
This means each chunk is about 1,000 characters long, with 180 characters of overlap between neighboring chunks.

The overlap helps preserve context when an answer spans the boundary between two chunks.

## 14. Current Retrieval Settings
The project currently retrieves the top 5 matching chunks by default: 
```code
TOP_K = 5
```
If answers feel incomplete, increase this to:
```code
TOP_K = 8
```
If answers are too slow or include too much irrelevant context, reduce it to:
```code
TOP_K = 3
```

## 15. CPU Performance Notes
This project is designed for CPU-first use. 
Expected behavior: 

| **Task** | **CPU Performance** | 
|:---|:---|
| Ingesting small text files | Fast |
| Ingesting large PDFs | Slower but usuable | 
| Asking short questions | Usable |
| Asking broad summary questions | Slower | 
| Running large models | Not recommended | 

The model `llama3.2:3b` is a practical starting point for CPU use. Larger models may provide better answers but will 
usually be slower without a GPU.

## 16. Troubleshooting
### 16a. Error Message: `Could not reach Ollama. Start it, then try again.`
Ollama is not running.
Try: 
```bash
ollama serve
```
Or open the Ollama desktop application if you installed the desktop version.

### 16b. Error Message: `model not found`
The required model has not been downloaded.

Run: 
```bash
ollama pull llama3.2:3b
ollama pull all-minilm
```

### 16c. Error Message: `No files found in docs`
The `docs/` folder is empty or the files are not supported.
Supported extensions:
```bash
.pdf
.docx
.txt
.md
```

### 16d. PDF produces no useful text 
The PDF may be scanned rather than text-based.  `pypdf` can extract embedded text, but it does not perform OCR. We plan 
to add OCR later with a tool such as Tesseract.

### 16e. Answers are weak or vague
Possible causes:
* The relevant document was not indexed.
* The PDF text extraction was poor.
* The chunk size is too small.
* `TOP_K` is too low.
* The question is too broad.

Try: 
```block
TOP_K = 8
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 250
```
Then rerun: 
```bash
python ingest.py
python ask.py
```

### 16f. Answers include information not in the documents
The prompt already tells the model to use only retrieved context, but small local models can still drift.

Possible improvements:
* Lower the temperature.
* Retrieve fewer but more relevant chunks.
* Improve chunking.
* Add a reranking step.
* Use a stronger local model if hardware allows.

Default temperature setting:
```code
"temperature": 0.1
```

### 16f. Limitations
This is a simple local RAG system. 

Known limitations:
* No OCR for scanned PDFs
* No web interface
* No user authentication
* No advanced document cleanup
* No reranking
* No hybrid keyword/vector search
* No automatic file change detection
* No conversation memory across questions

### 16g. Possible Upcoming Improvements
Good next upgrades:
1. Add OCR for scanned PDFs.
2. Add a Streamlit web interface.
3. Add file upload from the browser.
4. Add hybrid search with keyword and vector retrieval.
5. Add reranking for better source selection.
6. Add source previews before answering.
7. Add document delete/reindex commands.
8. Add a simple test suite.
9. Add logging.
10. Add Docker support.

## 17.  License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## 18. Contact 
For questions, open a GitHub issue or contact me through my GitHub profile.







