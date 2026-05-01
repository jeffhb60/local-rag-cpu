from typing import Any

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    status: str
    file_name: str
    source_id: str | None = None
    chunks_added: int = 0
    reason: str | None = None


class ReindexResponse(BaseModel):
    status: str
    files_seen: int
    files_indexed: int
    files_skipped: int
    chunks_added: int
    details: list[IngestResponse] = Field(default_factory=list)


class AvailableDocument(BaseModel):
    file_name: str
    relative_path: str
    size_bytes: int


class DocumentsResponse(BaseModel):
    available_files: list[AvailableDocument]
    indexed_files: list[dict[str, Any]]
    chunk_count: int


class JobStartResponse(BaseModel):
    job_id: str
    status_url: str


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None
    temperature: float | None = None
    strictness: bool | None = None
    system_prompt: str | None = None
    rag_instruction_template: str | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list[RetrievedChunk]


class SettingsUpdate(BaseModel):
    top_k_default: int | None = None
    temperature_default: float | None = None
    strictness_mode: bool | None = None
    system_prompt: str | None = None
    rag_instruction_template: str | None = None


class EvalResult(BaseModel):
    question: str
    answer: str
    retrieved_source_files: list[str]
    expected_source_files: list[str]
    expected_answer_keywords: list[str]
    source_pass: bool
    keyword_pass: bool
    passed: bool


class EvalSummary(BaseModel):
    total: int
    passed: int
    failed: int
    results: list[EvalResult]