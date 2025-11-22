from langchain.tools import tool
from tavily import TavilyClient
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Any
from app.config import TAVILY_API_KEY, EMBEDDING_MODEL
from app.utils.logger import log_event

class InternetSearchTool:
    def __init__(self):
        self.tavily_available = bool(TAVILY_API_KEY)
        if self.tavily_available:
            self.tavily = TavilyClient(api_key=TAVILY_API_KEY)
        
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.vector_store = None
        self.documents = []
        self._load_vector_store()
        log_event("INTERNET_TOOL", f"Initialized - Tavily: {self.tavily_available}")
    
    def _load_vector_store(self):
        try:
            if os.path.exists("vector_store/faiss_index.pkl"):
                with open("vector_store/faiss_index.pkl", "rb") as f:
                    data = pickle.load(f)
                    self.vector_store = data["index"]
                    self.documents = data["documents"]
                log_event("VECTOR_STORE", f"Loaded {len(self.documents)} documents")
        except Exception as e:
            log_event("VECTOR_STORE_ERROR", f"Failed to load vector store: {str(e)}", "error")
            self.vector_store = None
            self.documents = []
    
    def _save_vector_store(self):
        try:
            with open("vector_store/faiss_index.pkl", "wb") as f:
                pickle.dump({
                    "index": self.vector_store,
                    "documents": self.documents
                }, f)
        except Exception as e:
            log_event("VECTOR_STORE_SAVE_ERROR", f"Failed to save vector store: {str(e)}", "error")
    
    
    def search_internet(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the internet for relevant information.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 5)
        
        Returns:
            A list of search results with title, content, and source information
        """
        try:
            if not self.tavily_available:
                return self._get_mock_internet_data(query, max_results)
            
            response = self.tavily.search(
                query=query,
                max_results=max_results,
                search_depth="advanced"
            )
            
            results = []
            for item in response.get("results", []):
                result_data = {
                    "type": "internet",
                    "title": item.get("title", "No title"),
                    "content": item.get("content", ""),
                    "reference": item.get("url", ""),
                    "confidence": min(0.9, float(item.get("score", 70)) / 100),
                    "published_date": item.get("published_date", ""),
                    "source": "tavily"
                }
                results.append(result_data)
                self._add_to_vector_store(result_data)
            
            log_event("INTERNET_SEARCH", f"Found {len(results)} internet results for: {query}")
            return results
            
        except Exception as e:
            log_event("INTERNET_SEARCH_ERROR", f"Internet search failed: {str(e)}", "error")
            return self._get_mock_internet_data(query, max_results)
    
    
    def search_news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for recent news articles related to the query.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 5)
        
        Returns:
            A list of news articles with title, content, and publication date
        """
        try:
            if not self.tavily_available:
                return self._get_mock_news_data(query, max_results)
            
            # Add news context to query
            news_query = f"news {query} 2024"
            
            response = self.tavily.search(
                query=news_query,
                max_results=max_results,
                search_depth="basic"
            )
            
            results = []
            for item in response.get("results", []):
                result_data = {
                    "type": "news",
                    "title": item.get("title", "No title"),
                    "content": item.get("content", ""),
                    "reference": item.get("url", ""),
                    "confidence": min(0.85, float(item.get("score", 70)) / 100),
                    "published_date": item.get("published_date", ""),
                    "source": "tavily_news"
                }
                results.append(result_data)
                self._add_to_vector_store(result_data)
            
            log_event("NEWS_SEARCH", f"Found {len(results)} news results for: {query}")
            return results
            
        except Exception as e:
            log_event("NEWS_SEARCH_ERROR", f"News search failed: {str(e)}", "error")
            return self._get_mock_news_data(query, max_results)
    
    
    def semantic_search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Perform semantic search on previously cached documents using embeddings.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 3)
        
        Returns:
            A list of semantically similar documents from the vector store
        """
        try:
            if self.vector_store is None or len(self.documents) == 0:
                return []
            
            query_embedding = self.embedding_model.encode([query])
            distances, indices = self.vector_store.search(
                query_embedding.astype('float32'), 
                min(max_results, len(self.documents))
            )
            
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx].copy()
                    doc["confidence"] = max(0.1, 1 - (distance / 10))
                    doc["source"] = "semantic_search"
                    results.append(doc)
            
            log_event("SEMANTIC_SEARCH", f"Found {len(results)} semantic results for: {query}")
            return results
            
        except Exception as e:
            log_event("SEMANTIC_SEARCH_ERROR", f"Semantic search failed: {str(e)}", "error")
            return []
    
    def _get_mock_internet_data(self, query: str, max_results: int):
        mock_data = [
            {
                "type": "internet",
                "title": f"Research about {query}",
                "content": f"This is mock content about {query}. In a real implementation, this would be actual web search results from Tavily API.",
                "reference": "https://example.com/mock-data",
                "confidence": 0.75,
                "published_date": "2024-01-01",
                "source": "mock"
            },
            {
                "type": "internet", 
                "title": f"Latest developments in {query}",
                "content": f"Mock summary of recent advancements in {query}. This demonstrates the system structure when external APIs are not configured.",
                "reference": "https://example.com/mock-news",
                "confidence": 0.70,
                "published_date": "2024-01-01",
                "source": "mock"
            }
        ]
        return mock_data[:max_results]
    
    def _get_mock_news_data(self, query: str, max_results: int):
        mock_news = [
            {
                "type": "news",
                "title": f"Breaking: New developments in {query}",
                "content": f"This is mock news content about {query}. Real news would come from Tavily API news search.",
                "reference": "https://example.com/mock-news",
                "confidence": 0.80,
                "published_date": "2024-01-15",
                "source": "mock_news"
            }
        ]
        return mock_news[:max_results]
    
    def _add_to_vector_store(self, document):
        try:
            text = f"{document['title']} {document['content'][:500]}"
            embedding = self.embedding_model.encode([text])
            
            if self.vector_store is None:
                dimension = embedding.shape[1]
                self.vector_store = faiss.IndexFlatL2(dimension)
            
            self.vector_store.add(embedding.astype('float32'))
            self.documents.append(document)
            
            if len(self.documents) % 5 == 0:
                self._save_vector_store()
                
        except Exception as e:
            log_event("VECTOR_ADD_ERROR", f"Failed to add to vector store: {str(e)}", "error")

internet_tool = InternetSearchTool()