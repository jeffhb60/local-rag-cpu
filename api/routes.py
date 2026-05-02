from fastapi import APIRouter

from api.routes_chat import router as chat_router
from api.routes_documents import router as documents_router
from api.routes_eval import router as eval_router
from api.routes_jobs import router as jobs_router


router = APIRouter()

router.include_router(documents_router)
router.include_router(chat_router)
router.include_router(eval_router)
router.include_router(jobs_router)