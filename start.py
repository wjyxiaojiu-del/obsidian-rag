"""Launch Obsidian RAG backend and frontend."""
import subprocess
import sys
import os
import time

try:
    ROOT = os.path.dirname(os.path.abspath(__file__))
    BACKEND = os.path.join(ROOT, "backend")
    FRONTEND = os.path.join(ROOT, "frontend")

    print("Starting Obsidian RAG...")
    print()

    # Start backend
    print("[1/2] Starting backend (port 8000)...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    time.sleep(3)

    # Start frontend
    print("[2/2] Starting frontend (port 3001)...")
    frontend = subprocess.Popen(
        ["cmd", "/c", "npm", "run", "dev"],
        cwd=FRONTEND,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    print()
    print("Both services started!")
    print("Frontend: http://localhost:3001")
    print("Backend:  http://localhost:8000")
    print()
    print("Close this window to stop both services.")

    backend.wait()

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    print()
    input("Press Enter to exit...")
