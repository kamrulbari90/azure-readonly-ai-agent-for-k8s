from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .collectors import collect_kubernetes, query_azure_monitor
from .analyzer import analyze
from .config import settings

app = FastAPI(
    title="Azure Read-Only AI Infrastructure Agent",
    description="Collects operational evidence and recommends fixes; does not modify infrastructure.",
    version="0.1.0",
)

class InvestigationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    lookback_minutes: int = Field(default=60, ge=1, le=1440)
    include_kubernetes: bool = True

@app.get("/health")
def health():
    return {"status": "ok", "mode": "read-only-recommendations-only"}

@app.post("/investigate")
def investigate(request: InvestigationRequest):
    lookback = min(request.lookback_minutes, settings.max_lookback_minutes)
    evidence = {
        "lookback_minutes": lookback,
        "azure_monitor": query_azure_monitor(lookback),
        "kubernetes": collect_kubernetes() if request.include_kubernetes
            else {"source": "kubernetes", "status": "skipped", "reason": "Not requested"},
    }
    try:
        report = analyze(request.question, evidence)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {type(exc).__name__}") from exc
    return {
        "mode": "read-only",
        "infrastructure_changed": False,
        "question": request.question,
        "evidence": evidence,
        "recommendation_report": report,
    }
