from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from api.schemas import (
    QueryRequest,
    QueryResponse,
    RetrievedChunk,
    SettingsUpdate,
)
from config import settings
from core.generator import RAGGenerator


router = APIRouter(tags=["chat"])


@router.get("/settings")
async def get_settings():
    return jsonable_encoder(
        {
            "app_name": settings.app_name,
            "app_env": settings.app_env,
            "docs_dir": settings.docs_dir,
            "chroma_dir": settings.chroma_dir,
            "index_state_path": settings.index_state_path,
            "evaluation_equivalents_path": settings.evaluation_equivalents_path,
            "collection_name": settings.collection_name,
            "index_version": settings.index_version,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "chat_provider": settings.chat_provider,
            "chat_model": settings.chat_model,
            "deepseek_base_url": settings.deepseek_base_url,
            "top_k_default": settings.top_k_default,
            "temperature_default": settings.temperature_default,
            "strictness_mode": settings.strictness_mode,
            "system_prompt": settings.system_prompt,
            "rag_instruction_template": settings.rag_instruction_template,
            "context_format": settings.context_format,
        }
    )


@router.put("/settings")
async def update_settings(update: SettingsUpdate):
    """
    Only updates allowed runtime settings.

    Provider, chat model, and embedding model are intentionally locked.
    """
    update_data = update.model_dump(exclude_unset=True)

    if "top_k_default" in update_data and update_data["top_k_default"] is not None:
        settings.top_k_default = max(1, min(int(update_data["top_k_default"]), 50))

    if "temperature_default" in update_data and update_data["temperature_default"] is not None:
        settings.temperature_default = max(
            0.0,
            min(float(update_data["temperature_default"]), 2.0),
        )

    if "strictness_mode" in update_data and update_data["strictness_mode"] is not None:
        settings.strictness_mode = bool(update_data["strictness_mode"])

    if "system_prompt" in update_data and update_data["system_prompt"] is not None:
        settings.system_prompt = update_data["system_prompt"]

    if "rag_instruction_template" in update_data and update_data["rag_instruction_template"] is not None:
        template = update_data["rag_instruction_template"]

        if "{context}" not in template or "{question}" not in template:
            raise HTTPException(
                status_code=400,
                detail="RAG instruction template must include {context} and {question}.",
            )

        settings.rag_instruction_template = template

    return {
        "status": "updated",
        "settings": await get_settings(),
    }


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    generator = RAGGenerator(settings)

    result = generator.answer(
        question=req.question,
        top_k=req.top_k,
        temperature=req.temperature,
        strictness=req.strictness,
        system_prompt=req.system_prompt,
        rag_instruction_template=req.rag_instruction_template,
    )

    chunks_out = [
        RetrievedChunk(
            chunk_id=chunk["chunk_id"],
            text=chunk["text"],
            metadata=chunk["metadata"],
            distance=chunk["distance"],
        )
        for chunk in result["retrieved_chunks"]
    ]

    return QueryResponse(
        question=req.question,
        answer=result["answer"],
        retrieved_chunks=chunks_out,
    )