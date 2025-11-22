from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.middleware.auth import verify_auth
from app.agents.langgraph_agent import langgraph_agent
from app.utils.logger import log_event

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = {}
    options: Optional[Dict[str, Any]] = {
        "use_graph": True,
        "use_internet": True, 
        "max_results": 5
    }

class ErrorResponse(BaseModel):
    status: str
    error: Dict[str, str]

class SuccessResponse(BaseModel):
    status: str
    response: Dict[str, Any]

@router.post("/api/v1/agent/query", 
             response_model=SuccessResponse,
             responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def agent_query_endpoint(
    request: QueryRequest, 
    user: str = Depends(verify_auth)
):
    try:
        log_event("LANGGRAPH_API", f"User: {user}, Query: {request.query[:100]}...")
        
        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Query cannot be empty"
                    }
                }
            )
        
        result = langgraph_agent.process_query(
            query=request.query.strip(),
            options=request.options,
            context=request.context
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log_event("LANGGRAPH_API_ERROR", f"Endpoint error: {str(e)}", "error")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": {
                    "code": "INTERNAL_ERROR", 
                    "message": "Internal server error occurred while processing your request."
                }
            }
        )