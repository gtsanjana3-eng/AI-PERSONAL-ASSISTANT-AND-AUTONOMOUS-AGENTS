from backend.tools.registry import registry
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import os
from typing import Any, Dict

from backend.database.db import (
    init_db,
    get_task_history,
    get_task_history_by_plan_id
)

from backend.agents.orchestrator import AgentOrchestrator


app = FastAPI(
    title="AI Personal Assistant API",
    version="1.0.0"
)


# Initialize database when the application starts
init_db()

orchestrator = AgentOrchestrator()


# ==========================================
# REQUEST MODELS
# ==========================================

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User request for the AI assistant"
    )


class ActionRequest(BaseModel):
    plan_id: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    task_id: int = Field(
        ...,
        ge=1
    )


# ==========================================
# CHAT API
# ==========================================

@app.post("/api/chat")
def chat_endpoint(
    request: ChatRequest
) -> Dict[str, Any]:

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    try:

        return orchestrator.process_request(
            message
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail="Failed to process the request."
        )


# ==========================================
# APPROVAL API
# ==========================================

@app.post("/api/approve")
def approve_endpoint(
    request: ActionRequest
) -> Dict[str, Any]:

    try:

        return orchestrator.approve_task(
            request.plan_id,
            request.task_id
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Failed to approve the task."
        )


# ==========================================
# REJECTION API
# ==========================================

@app.post("/api/reject")
def reject_endpoint(
    request: ActionRequest
) -> Dict[str, Any]:

    try:

        return orchestrator.reject_task(
            request.plan_id,
            request.task_id
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Failed to reject the task."
        )


# ==========================================
# TASK HISTORY
# ==========================================

@app.get("/api/history")
def history_endpoint(
    limit: int = 50
):

    # Keep the API within a safe range.
    limit = max(
        1,
        min(limit, 100)
    )

    return get_task_history(limit)


@app.get("/api/tools")
def tools_endpoint():
    return {
        "tools": registry.list_tools()
    }


@app.get("/api/health")
def health_endpoint():
    return {
        "status": "healthy",
        "service": "AI Personal Assistant"
    }


@app.get("/api/history/{plan_id}")
def history_detail_endpoint(
    plan_id: str
):

    if not plan_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Plan ID cannot be empty."
        )

    history = get_task_history_by_plan_id(
        plan_id
    )

    if history is None:

        raise HTTPException(
            status_code=404,
            detail="Plan history not found."
        )

    return history


# ==========================================
# FRONTEND
# ==========================================

frontend_path = os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ),
    "frontend"
)


if os.path.exists(frontend_path):

    app.mount(
        "/static",
        StaticFiles(
            directory=frontend_path
        ),
        name="static"
    )


    @app.get("/")
    def read_index():

        return FileResponse(
            os.path.join(
                frontend_path,
                "index.html"
            )
        )