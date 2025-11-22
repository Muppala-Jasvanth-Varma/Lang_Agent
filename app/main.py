from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes.agent import router as agent_router
from app.db.neo4j_connector import close_driver, neo4j
from app.utils.logger import log_event, setup_logging
from app.config import validate_config
from app.agents.langgraph_agent import langgraph_agent
from app.middleware.auth import verify_auth
import uvicorn

setup_logging()

missing_config = validate_config()
if missing_config:
    log_event("CONFIG_WARNING", f"Missing configuration: {', '.join(missing_config)}", "warning")

app = FastAPI(
    title="AI Agent Integration API (LangGraph)",
    description="Stateful AI agent with hybrid reasoning using LangGraph - Combines graph knowledge with internet search",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "AI Agent API Support",
        "email": "support@aiagent.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)

@app.get("/")
def root():
    status_info = {
        "message": "🚀 AI Agent Integration API with LangGraph is running", 
        "status": "active",
        "version": "2.0.0",
        "framework": "LangGraph",
        "services": {
            "neo4j": "connected" if neo4j.connected else "fallback_mode",
            "langgraph_agent": "initialized",
            "llm": "available" if langgraph_agent.llm else "fallback_mode",
            "authentication": "enabled"
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health", 
            "agent_query": "/api/v1/agent/query",
            "status": "/status"
        },
        "documentation": "Visit /docs for interactive API documentation"
    }
    return status_info

@app.get("/health")
def health_check():
    neo4j_health = neo4j.health_check()
    
    health_status = {
        "status": "healthy", 
        "service": "ai_agent_langgraph",
        "version": "2.0.0",
        "framework": "LangGraph",
        "timestamp": "2024-01-01T00:00:00Z",  # You might want to use actual timestamp
        "components": {
            "api": "healthy",
            "authentication": "healthy", 
            "neo4j": neo4j_health["status"],
            "langgraph_agent": "initialized",
            "llm": "available" if langgraph_agent.llm else "fallback"
        },
        "details": {
            "neo4j_message": neo4j_health.get("message", "Unknown"),
            "neo4j_version": neo4j_health.get("version", "unknown")
        }
    }
    
    missing = validate_config()
    if missing:
        health_status["config_warnings"] = missing
        health_status["status"] = "degraded"
    
    if not langgraph_agent.llm and "GEMINI_API_KEY" in missing:
        health_status["status"] = "degraded"
        health_status["components"]["llm"] = "unavailable"
    
    log_event("HEALTH_CHECK", f"Health status: {health_status['status']}")
    return health_status

@app.get("/status")
def detailed_status(user: str = Depends(verify_auth)):
    status_info = {
        "system": {
            "version": "2.0.0",
            "framework": "LangGraph",
            "uptime": "running",  # In production, you'd calculate actual uptime
            "environment": "development"  # Could be set via environment variable
        },
        "services": {
            "neo4j": {
                "connected": neo4j.connected,
                "status": neo4j.health_check()["status"],
                "uri": "bolt://localhost:7687"  # From config
            },
            "llm": {
                "available": langgraph_agent.llm is not None,
                "model": "gemini-pro",
                "provider": "Google Generative AI"
            },
            "tools": {
                "graph_search": "available",
                "internet_search": "available" if langgraph_agent.tools else "config_required",
                "semantic_search": "available"
            }
        },
        "metrics": {
            "active_connections": 1,  # Placeholder
            "total_queries": 0,  # Would track in production
            "average_response_time": "N/A"
        }
    }
    
    log_event("STATUS_CHECK", f"Detailed status checked by user: {user}")
    return status_info

@app.get("/tools")
def list_available_tools(user: str = Depends(verify_auth)):
    tools_info = []
    
    for tool in langgraph_agent.tools:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "available": True
        })
    
    additional_tools = [
        {
            "name": "semantic_search",
            "description": "Search vector store for semantically similar content",
            "available": True
        }
    ]
    
    tools_info.extend(additional_tools)
    
    return {
        "status": "success",
        "tools": tools_info,
        "count": len(tools_info)
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    log_event("HTTP_ERROR", f"HTTP {exc.status_code}: {exc.detail}", "error")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log_event("GLOBAL_ERROR", f"Unhandled exception: {str(exc)}", "error")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )

@app.on_event("startup")
async def startup_event():
    log_event("STARTUP", "AI Agent API server starting up...")
    
    missing_config = validate_config()
    if missing_config:
        log_event("STARTUP_WARNING", f"Missing configuration on startup: {', '.join(missing_config)}", "warning")
    else:
        log_event("STARTUP", "All configurations validated successfully")
    
    log_event("STARTUP", "AI Agent API server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    log_event("SHUTDOWN", "AI Agent API server shutting down...")
    close_driver()
    log_event("SHUTDOWN", "AI Agent API server shutdown complete")

if __name__ == "__main__":
    log_event("STARTUP", "Starting AI Agent API server directly")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)