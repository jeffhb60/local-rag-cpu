from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import subprocess, sys

router = APIRouter()

@router.post("/run")
def run_eval():
    # Run the evaluation script
    result = subprocess.run([sys.executable, "eval/run_eval.py"], capture_output=True, text=True)
    return {"output": result.stdout, "error": result.stderr}