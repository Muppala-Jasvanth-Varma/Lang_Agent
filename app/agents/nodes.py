from app.agents.state import AgentState
from app.tools.graph_tool import search_knowledge_graph
from app.tools.internet_tool import internet_tool
from app.utils.logger import log_event
from typing import List, Dict, Any

def route_query(state: AgentState) -> AgentState:
    query = state["query"]
    options = state["options"]
    
    log_event("ROUTER", f"Routing query: {query}")
    query_lower = query.lower()
    
    next_steps = ["analyze_query"]
    
    if options.get("use_graph", True) and _needs_graph_search(query_lower):
        next_steps.append("search_graph")
    
    if options.get("use_internet", True) and _needs_internet_search(query_lower):
        next_steps.append("search_internet")
    
    next_steps.append("generate_answer")
    
    state["next_step"] = next_steps[0] if next_steps else "generate_answer"
    state["steps_completed"].append("route_query")
    state["reasoning"].append(f"Query routed to steps: {', '.join(next_steps)}")
    
    return state

def _needs_graph_search(query: str) -> bool:
    graph_keywords = [
        "what is", "define", "explain", "concept", "theory", 
        "relationship", "how does", "compare", "difference between"
    ]
    return any(keyword in query for keyword in graph_keywords)

def _needs_internet_search(query: str) -> bool:
    internet_keywords = [
        "latest", "recent", "news", "update", "current", "2024", "2025",
        "today", "yesterday", "this week", "this month", "trending"
    ]
    return any(keyword in query for keyword in internet_keywords)

def analyze_query(state: AgentState) -> AgentState:
    query = state["query"]
    
    log_event("ANALYZER", f"Analyzing query: {query}")
    
    analysis = {
        "intent": "information_request",
        "complexity": "medium",
        "needs_facts": True,
        "needs_current_info": False,
        "expected_sources": ["graph"]
    }
    
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["what is", "define", "explain"]):
        analysis["intent"] = "definition"
        analysis["needs_facts"] = True
    elif any(word in query_lower for word in ["how to", "steps", "guide"]):
        analysis["intent"] = "instructions"
    elif any(word in query_lower for word in ["compare", "difference", "vs"]):
        analysis["intent"] = "comparison"
    
    if len(query.split()) > 10 or any(word in query_lower for word in ["complex", "advanced", "detailed"]):
        analysis["complexity"] = "high"
    elif len(query.split()) < 5:
        analysis["complexity"] = "low"
    
    if any(word in query_lower for word in ["latest", "recent", "news", "update"]):
        analysis["needs_current_info"] = True
        analysis["expected_sources"].append("internet")
    
    state["reasoning"].append(f"Query analysis: {analysis}")
    state["steps_completed"].append("analyze_query")
    state["next_step"] = "search_graph" if state["options"].get("use_graph", True) else "search_internet"
    
    return state

def search_graph(state: AgentState) -> AgentState:
    if not state["options"].get("use_graph", True):
        state["steps_completed"].append("search_graph")
        state["next_step"] = "search_internet"
        return state
    
    query = state["query"]
    max_results = state["options"].get("max_results", 5)
    
    log_event("GRAPH_NODE", f"Searching graph for: {query}")
    
    try:
        results = search_knowledge_graph(query, max_results)
        state["graph_results"] = results
        state["all_contexts"].extend(results)
        state["reasoning"].append(f"Found {len(results)} graph results")
        
    except Exception as e:
        log_event("GRAPH_NODE_ERROR", f"Graph search failed: {str(e)}", "error")
        state["last_error"] = f"Graph search error: {str(e)}"
    
    state["steps_completed"].append("search_graph")
    state["next_step"] = "search_internet" if state["options"].get("use_internet", True) else "generate_answer"
    
    return state

def search_internet(state: AgentState) -> AgentState:
    if not state["options"].get("use_internet", True):
        state["steps_completed"].append("search_internet")
        state["next_step"] = "generate_answer"
        return state
    
    query = state["query"]
    max_results = state["options"].get("max_results", 5)
    
    log_event("INTERNET_NODE", f"Searching internet for: {query}")
    
    try:
        internet_results = internet_tool.search_internet(query, max_results)
        state["internet_results"] = internet_results
        state["all_contexts"].extend(internet_results)
        
        semantic_results = internet_tool.semantic_search(query, max_results // 2)
        state["semantic_results"] = semantic_results
        state["all_contexts"].extend(semantic_results)
        
        state["reasoning"].append(f"Found {len(internet_results)} internet results and {len(semantic_results)} semantic results")
        
    except Exception as e:
        log_event("INTERNET_NODE_ERROR", f"Internet search failed: {str(e)}", "error")
        state["last_error"] = f"Internet search error: {str(e)}"
    
    state["steps_completed"].append("search_internet")
    state["next_step"] = "generate_answer"
    
    return state

def should_continue(state: AgentState) -> str:
    """Determine if the agent should continue or finish"""
    has_context = len(state["all_contexts"]) > 0
    max_iterations_reached = state["iterations"] >= 5
    
    if max_iterations_reached:
        state["max_iterations_reached"] = True
        return "finish"
    
    if state["next_step"] == "generate_answer" and has_context:
        return "generate_answer"
    elif state["next_step"] and state["next_step"] != "generate_answer":
        return "continue"
    else:
        return "finish"

def format_final_answer(state: AgentState) -> AgentState:
    """Format the final answer in the required structure"""
    from app.utils.formatters import format_sources, create_structured_output
    
    sources = format_sources(state["all_contexts"])
    
    structured_output = create_structured_output(
        answer=state["final_answer"],
        sources=sources,
        reasoning=state["reasoning"]
    )
    
    state["sources"] = sources
    state["structured_output"] = structured_output
    state["should_continue"] = False
    
    log_event("FINAL_FORMAT", "Formatted final answer with sources")
    
    return state