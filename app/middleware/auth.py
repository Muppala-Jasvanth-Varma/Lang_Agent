from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config import API_USERNAME, API_PASSWORD
from app.utils.logger import log_event
import secrets

security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    try:
        # Constant-time comparison to prevent timing attacks
        username_correct = secrets.compare_digest(credentials.username, API_USERNAME)
        password_correct = secrets.compare_digest(credentials.password, API_PASSWORD)
        
        if not (username_correct and password_correct):
            log_event("AUTH_FAILED", f"Failed authentication attempt for user: {credentials.username}", "warning")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error": {
                        "code": "AUTH_FAILED",
                        "message": "Invalid credentials provided."
                    }
                },
                headers={"WWW-Authenticate": "Basic"},
            )
        
        log_event("AUTH_SUCCESS", f"User authenticated: {credentials.username}")
        return credentials.username
        
    except HTTPException:
        raise
    except Exception as e:
        log_event("AUTH_ERROR", f"Unexpected authentication error: {str(e)}", "error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error": {
                    "code": "AUTH_SYSTEM_ERROR",
                    "message": "Authentication system error occurred."
                }
            }
        )

def optional_auth(credentials: HTTPBasicCredentials = Depends(security)):
    try:
        return verify_auth(credentials)
    except HTTPException:
        return None

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: str = Depends(verify_auth)):
        # Simple role check - can be extended with proper user management
        if "admin" in self.allowed_roles and user == "admin":
            return user
        elif "user" in self.allowed_roles:
            return user
        else:
            log_event("AUTH_ROLE_FAILED", f"User {user} lacks required roles: {self.allowed_roles}", "warning")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "error": {
                        "code": "INSUFFICIENT_PERMISSIONS",
                        "message": "Insufficient permissions to access this resource."
                    }
                }
            )
admin_only = RoleChecker(["admin"])
any_authenticated_user = RoleChecker(["user", "admin"])