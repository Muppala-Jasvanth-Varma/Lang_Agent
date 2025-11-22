from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from app.utils.logger import log_event

class Neo4jConnector:
    def __init__(self):
        self.connected = False
        self.driver = None
        self._connect()
    
    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
                connection_timeout=10  # 10 second timeout
            )
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()[0]
                if test_value == 1:
                    self.connected = True
                    log_event("NEO4J_CONNECT", "Successfully connected to Neo4j database")
                else:
                    self.connected = False
                    log_event("NEO4J_WARNING", "Neo4j connection test failed", "warning")
                    
        except Exception as e:
            self.connected = False
            self.driver = None
            log_event("NEO4J_WARNING", f"Neo4j not available: {str(e)} - Using fallback mode", "warning")
    
    def close(self):
        if self.driver:
            try:
                self.driver.close()
                log_event("NEO4J_CLOSE", "Neo4j connection closed")
            except Exception as e:
                log_event("NEO4J_CLOSE_ERROR", f"Error closing Neo4j connection: {str(e)}", "error")
    
    def execute_query(self, query, parameters=None):
        if not self.connected or not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            log_event("NEO4J_QUERY_ERROR", f"Query failed: {str(e)}", "error")
            return []
    
    def health_check(self):
        if not self.connected:
            return {"status": "disconnected", "message": "Neo4j not available"}
        
        try:
            with self.driver.session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
                version_info = result.single()
                return {
                    "status": "connected",
                    "message": "Neo4j is healthy",
                    "version": version_info["versions"][0] if version_info else "unknown"
                }
        except Exception as e:
            self.connected = False
            return {"status": "error", "message": f"Health check failed: {str(e)}"}

neo4j = Neo4jConnector()

def close_driver():
    if neo4j:
        neo4j.close()