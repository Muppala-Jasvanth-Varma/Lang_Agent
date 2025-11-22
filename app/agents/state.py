from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator

class AgentState(TypedDict):
    query: str
    context: Dict[str, Any]
    options: Dict[str, Any]
    user_id: Optional[str]
    
    messages: Annotated[List[Dict[str, Any]], operator.add]
    current_step: str
    steps_completed: List[str]
    next_step: Optional[str]
    
    graph_results: List[Dict[str, Any]]
    internet_results: List[Dict[str, Any]]
    semantic_results: List[Dict[str, Any]]
    all_contexts: List[Dict[str, Any]]
    
    reasoning: List[str]
    tool_calls: List[Dict[str, Any]]
    iterations: int
    
    final_answer: str
    sources: List[Dict[str, Any]]
    structured_output: Dict[str, Any]
    confidence: float
    
    should_continue: bool
    max_iterations_reached: bool
    error: Optional[str]
    last_error: Optional[str]