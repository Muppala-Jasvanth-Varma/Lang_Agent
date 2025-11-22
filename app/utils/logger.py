import logging
import os
from datetime import datetime
import sys

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create handlers
    file_handler = logging.FileHandler("logs/agent.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create our specific logger
    logger = logging.getLogger("ai_agent")
    logger.setLevel(logging.INFO)
    
    return logger

# Initialize logger
logger = setup_logging()

def log_event(event_type: str, message: str, level: str = "info"):
    """
    Structured event logging with different levels
    
    Args:
        event_type: Type of event (e.g., "API_REQUEST", "GRAPH_SEARCH")
        message: Log message
        level: Log level ("info", "warning", "error", "debug")
    """
    timestamp = datetime.now().isoformat()
    log_message = f"[{timestamp}] {event_type}: {message}"
    
    if level == "error":
        logger.error(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "debug":
        logger.debug(log_message)
    else:
        logger.info(log_message)

def log_api_request(user: str, endpoint: str, method: str, status_code: int = None):
    """Log API request details"""
    log_event(
        "API_REQUEST",
        f"User: {user}, Endpoint: {endpoint}, Method: {method}, Status: {status_code or 'pending'}",
        "info"
    )

def log_agent_step(step_name: str, query: str, results_count: int = None):
    """Log agent workflow steps"""
    message = f"Step: {step_name}, Query: {query}"
    if results_count is not None:
        message += f", Results: {results_count}"
    log_event("AGENT_STEP", message, "info")

def log_tool_usage(tool_name: str, query: str, execution_time: float = None):
    """Log tool usage and performance"""
    message = f"Tool: {tool_name}, Query: {query}"
    if execution_time:
        message += f", Time: {execution_time:.2f}s"
    log_event("TOOL_USAGE", message, "debug")

def log_error(context: str, error: Exception, user: str = None):
    """Log errors with context"""
    user_info = f"User: {user}, " if user else ""
    log_event(
        "ERROR",
        f"{user_info}Context: {context}, Error: {str(error)}",
        "error"
    )

def log_performance(operation: str, duration: float, details: str = None):
    """Log performance metrics"""
    message = f"Operation: {operation}, Duration: {duration:.2f}s"
    if details:
        message += f", Details: {details}"
    log_event("PERFORMANCE", message, "info")