from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information.
    
    Args:
        query: The search query string
    
    Returns:
        Search results as a string
    """
    return f"Results for {query}"
from langchain_core.messages import HumanMessage
import json
import re

from app.tools.graph_tool import search_knowledge_graph
from app.tools.internet_tool import internet_tool
from app.config import GEMINI_API_KEY
from app.utils.logger import log_event
from app.utils.formatters import format_sources, create_structured_output

class SimpleLangGraphAgent:
    def __init__(self):
        self.llm = self._setup_llm()
        self.graph = self._build_graph()
        log_event("SIMPLE_AGENT", "Simple LangGraph agent initialized")
    
    def _setup_llm(self):
        """Setup the LLM with Gemini"""
        if not GEMINI_API_KEY:
            log_event("LLM_SETUP", "Gemini API key not configured - using fallback mode", "warning")
            return None
        
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=GEMINI_API_KEY,
                temperature=0.1,
                max_output_tokens=1024
            )
        except Exception as e:
            log_event("LLM_SETUP_ERROR", f"Failed to setup LLM: {str(e)}", "error")
            return None
    
    def _build_graph(self):
        """Build a simple LangGraph workflow"""
        workflow = StateGraph(dict)
        
        workflow.add_node("search", self._search_node)
        workflow.add_node("generate", self._generate_node)
        
        workflow.set_entry_point("search")
        
        workflow.add_edge("search", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def _search_node(self, state):
        query = state.get("query", "")
        options = state.get("options", {})
        
        log_event("SEARCH_NODE", f"Searching for: {query}")
        
        all_results = []
        
        if options.get("use_graph", True):
            try:
                graph_results = search_knowledge_graph(query, options.get("max_results", 3))
                all_results.extend(graph_results)
                log_event("GRAPH_SEARCH", f"Found {len(graph_results)} graph results")
            except Exception as e:
                log_event("GRAPH_SEARCH_ERROR", f"Graph search failed: {str(e)}", "error")
        
        if options.get("use_internet", True):
            try:
                internet_results = internet_tool.search_internet(query, options.get("max_results", 3))
                all_results.extend(internet_results)
                log_event("INTERNET_SEARCH", f"Found {len(internet_results)} internet results")
            except Exception as e:
                log_event("INTERNET_SEARCH_ERROR", f"Internet search failed: {str(e)}", "error")
        
        state["all_results"] = all_results
        state["total_sources"] = len(all_results)
        
        return state
    
    def _generate_node(self, state):
        """Generate the final answer"""
        query = state.get("query", "")
        all_results = state.get("all_results", [])
        
        if not all_results:
            state["answer"] = "I couldn't find enough relevant information to answer your question."
            state["sources"] = []
            state["structured_output"] = {
                "key_points": ["No information found"],
                "summary": "Unable to generate answer due to insufficient information"
            }
            return state
        
        sources = format_sources(all_results)
        
        if self.llm:
            try:
                context_text = self._format_contexts(all_results)
                prompt = self._create_prompt(query, context_text)
                
                response = self.llm.invoke([HumanMessage(content=prompt)])
                parsed_response = self._parse_response(response.content)
                
                state["answer"] = parsed_response["answer"]
                state["structured_output"] = {
                    "key_points": parsed_response["key_points"],
                    "summary": parsed_response["summary"]
                }
                
            except Exception as e:
                log_event("LLM_GENERATION_ERROR", f"LLM generation failed: {str(e)}", "error")
                state = self._generate_fallback_answer(state, all_results)
        else:
            state = self._generate_fallback_answer(state, all_results)
        
        state["sources"] = sources
        return state
    
    def _format_contexts(self, results):
        context_text = ""
        for i, result in enumerate(results, 1):
            context_text += f"\n--- Source {i} ({result.get('type', 'unknown')}) ---\n"
            context_text += f"Title: {result.get('title', 'N/A')}\n"
            context_text += f"Content: {result.get('content', '')}\n"
        return context_text
    
    def _create_prompt(self, query, context_text):
        return f"""
        Based on the following information, provide a comprehensive answer to the query.
        
        QUERY: {query}
        
        INFORMATION:
        {context_text}
        
        Please provide:
        1. A clear main answer
        2. 3-5 key points
        3. A brief summary
        
        Format as JSON:
        {{
            "answer": "your answer",
            "key_points": ["point1", "point2", "point3"],
            "summary": "brief summary"
        }}
        """
    
    def _parse_response(self, response_text):
        """Parse the LLM response"""
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "answer": response_text,
            "key_points": ["See main answer for details"],
            "summary": response_text[:100] + "..." if len(response_text) > 100 else response_text
        }
    
    def _generate_fallback_answer(self, state, results):
        graph_count = len([r for r in results if r.get('type') == 'graph'])
        internet_count = len([r for r in results if r.get('type') == 'internet'])
        
        state["answer"] = (
            f"I found information about your query from {len(results)} sources "
            f"({graph_count} from knowledge graph, {internet_count} from web search). "
            f"Configure LLM for detailed AI responses."
        )
        state["structured_output"] = {
            "key_points": [
                f"Graph sources: {graph_count}",
                f"Internet sources: {internet_count}",
                "Fallback mode active",
                "LLM not configured"
            ],
            "summary": f"Found {len(results)} information sources"
        }
        return state
    
    def process_query(self, query, options=None, context=None):
        try:
            log_event("AGENT_PROCESS", f"Processing: {query[:50]}...")
            
            initial_state = {
                "query": query,
                "options": options or {},
                "context": context or {}
            }
            
            final_state = self.graph.invoke(initial_state)
            
            response = {
                "status": "success",
                "response": {
                    "answer": final_state["answer"],
                    "sources": final_state["sources"],
                    "structured_output": final_state["structured_output"]
                }
            }
            
            if context:
                response["context"] = context
            
            log_event("AGENT_SUCCESS", f"Processed query successfully")
            return response
            
        except Exception as e:
            log_event("AGENT_ERROR", f"Processing failed: {str(e)}", "error")
            return {
                "status": "error",
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": f"Failed to process query: {str(e)}"
                }
            }
langgraph_agent = SimpleLangGraphAgent()