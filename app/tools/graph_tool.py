from langchain_core.tools import tool
from app.db.neo4j_connector import neo4j
from app.utils.logger import log_event
from typing import List, Dict, Any

@tool
def search_knowledge_graph(query: str, max_results: int = 3) -> list:
    """Search the knowledge graph for relevant information.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 3)
    
    Returns:
        A list of search results with title, content, and source information
    """
    try:
        if not neo4j.connected:
            return _get_fallback_graph_data(query, max_results)
        
        search_query = """
        MATCH (n:Concept)
        WHERE toLower(n.title) CONTAINS toLower($query)
           OR toLower(n.summary) CONTAINS toLower($query)
        OPTIONAL MATCH (n)-[r]-(related:Concept)
        WITH n, collect({relation: type(r), target: related.title}) as relationships
        RETURN n.title as title, n.summary as summary, n.category as category, 
               n.confidence as confidence, n.id as node_id, relationships
        LIMIT $max_results
        """
        
        results = neo4j.execute_query(search_query, {
            "query": query, 
            "max_results": max_results
        })
        
        formatted_results = []
        for result in results:
            content = result["summary"]
            relationships = result.get("relationships", [])
            if relationships:
                rel_text = " Related to: " + ", ".join([
                    f"{rel['target']} ({rel['relation']})" 
                    for rel in relationships[:3]  # Limit to 3 relationships
                ])
                content += rel_text
            
            formatted_results.append({
                "type": "graph",
                "title": result["title"],
                "content": content,
                "reference": f"graph:{result['node_id']}",
                "confidence": float(result.get("confidence", 0.8)),
                "category": result.get("category", "general"),
                "relationships": relationships
            })
        
        log_event("GRAPH_TOOL", f"Found {len(formatted_results)} graph results for: {query}")
        return formatted_results
        
    except Exception as e:
        log_event("GRAPH_TOOL_ERROR", f"Graph search failed: {str(e)}", "error")
        return _get_fallback_graph_data(query, max_results)

@tool
def get_related_concepts(concept_name: str, max_related: int = 3) -> List[Dict[str, Any]]:
    """Get concepts related to a specific concept from the knowledge graph.
    
    Args:
        concept_name: The name of the concept to find related concepts for
        max_related: Maximum number of related concepts to return (default: 3)
    
    Returns:
        A list of related concepts with relationship information
    """
    try:
        if not neo4j.connected:
            return []
        
        query = """
        MATCH (n:Concept {title: $concept_name})-[r]-(related:Concept)
        RETURN related.title as title, related.summary as summary, 
               type(r) as relationship, r.confidence as rel_confidence
        LIMIT $max_related
        """
        
        results = neo4j.execute_query(query, {
            "concept_name": concept_name,
            "max_related": max_related
        })
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "type": "graph_related",
                "title": result["title"],
                "content": result["summary"],
                "relationship": result["relationship"],
                "confidence": float(result.get("rel_confidence", 0.7)),
                "reference": f"graph:related:{concept_name}"
            })
        
        return formatted_results
        
    except Exception as e:
        log_event("RELATED_CONCEPTS_ERROR", f"Related concepts search failed: {str(e)}", "error")
        return []

def _get_fallback_graph_data(query: str, max_results: int):
    fallback_knowledge_base = {
        "ai": {
            "type": "graph",
            "title": "Artificial Intelligence",
            "content": "Field of computer science focused on creating intelligent machines that can learn, reason, and solve problems. Includes subfields like machine learning, natural language processing, and computer vision.",
            "reference": "graph:fallback:ai001",
            "confidence": 0.85,
            "category": "technology"
        },
        "machine learning": {
            "type": "graph",
            "title": "Machine Learning", 
            "content": "Subset of AI that uses statistical techniques to enable computers to learn and improve from experience without explicit programming. Common approaches include supervised learning, unsupervised learning, and reinforcement learning.",
            "reference": "graph:fallback:ml001",
            "confidence": 0.82,
            "category": "technology"
        },
        "deep learning": {
            "type": "graph",
            "title": "Deep Learning",
            "content": "Type of machine learning using neural networks with multiple layers to model complex patterns in large amounts of data. Particularly effective for image recognition, speech recognition, and natural language processing.",
            "reference": "graph:fallback:dl001", 
            "confidence": 0.80,
            "category": "technology"
        },
        "natural language processing": {
            "type": "graph",
            "title": "Natural Language Processing",
            "content": "Branch of AI that helps computers understand, interpret, and manipulate human language. Applications include chatbots, translation, and sentiment analysis.",
            "reference": "graph:fallback:nlp001",
            "confidence": 0.78,
            "category": "technology"
        },
        "computer vision": {
            "type": "graph", 
            "title": "Computer Vision",
            "content": "Field of AI that enables computers to interpret and understand the visual world from digital images or videos. Used in facial recognition, autonomous vehicles, and medical imaging.",
            "reference": "graph:fallback:cv001",
            "confidence": 0.77,
            "category": "technology"
        },
        "neural networks": {
            "type": "graph",
            "title": "Neural Networks",
            "content": "Computing systems inspired by biological neural networks. Consist of interconnected nodes (neurons) that process information and learn patterns.",
            "reference": "graph:fallback:nn001",
            "confidence": 0.79,
            "category": "technology"
        }
    }
    
    query_lower = query.lower()
    relevant_data = []
    
    for key, value in fallback_knowledge_base.items():
        if key in query_lower:
            relevant_data.append(value)
    
    if not relevant_data:
        for key, value in fallback_knowledge_base.items():
            if any(word in query_lower for word in key.split()):
                relevant_data.append(value)
    
    if not relevant_data and any(term in query_lower for term in ['ai', 'artificial', 'intelligence', 'machine', 'learning']):
        relevant_data = [
            fallback_knowledge_base["ai"],
            fallback_knowledge_base["machine learning"],
            fallback_knowledge_base["deep learning"]
        ]
    
    result = relevant_data[:max_results] if relevant_data else list(fallback_knowledge_base.values())[:max_results]
    log_event("GRAPH_FALLBACK", f"Using fallback graph data: {len(result)} results for: {query}")
    return result