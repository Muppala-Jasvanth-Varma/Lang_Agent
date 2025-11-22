import os
import subprocess
import sys

def create_project_structure():
    """Create the complete project structure"""
    directories = [
        "app",
        "app/middleware", 
        "app/routes",
        "app/agents",
        "app/tools",
        "app/db",
        "app/utils",
        "logs",
        "vector_store"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Create __init__.py files
    init_files = [
        "app/__init__.py",
        "app/middleware/__init__.py",
        "app/routes/__init__.py", 
        "app/agents/__init__.py",
        "app/tools/__init__.py",
        "app/db/__init__.py",
        "app/utils/__init__.py"
    ]
    
    for init_file in init_files:
        with open(init_file, "w") as f:
            f.write("# Package initialization\n")
        print(f"✅ Created: {init_file}")
    
    print("🎉 LangGraph project structure created successfully!")
    print("\n📋 Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Edit .env file with your API keys")
    print("3. Start Neo4j database (optional)")
    print("4. Run: uvicorn app.main:app --reload")
    print("5. Test the API at: http://localhost:8000/docs")

if __name__ == "__main__":
    create_project_structure()