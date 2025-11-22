import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_USERNAME = os.getenv("API_USER", "agent")
API_PASSWORD = os.getenv("API_PASS", "secret")

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# External API Keys
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_RESULTS = 5
REQUEST_TIMEOUT = 30

MAX_RECURSION_LIMIT = 15
AGENT_TIMEOUT = 60

def validate_config():
    missing = []
    if not TAVILY_API_KEY:
        missing.append("TAVILY_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not NEO4J_PASSWORD or NEO4J_PASSWORD == "your_neo4j_password_here":
        missing.append("NEO4J_PASSWORD (update in .env file)")
    return missing