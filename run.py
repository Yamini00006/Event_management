#!/usr/bin/env python3
"""
EventFlow - Quick Start Script
================================
Run this script to install dependencies and start the server.

Usage:
    python run.py

Or manually:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import subprocess
import sys
import os

def main():
    print("⚡ EventFlow - Starting up...")
    print("=" * 50)

    # Install deps
    print("📦 Installing dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "-r", "requirements.txt", "-q", "--break-system-packages"
    ])
    print("✅ Dependencies installed")

    print("\n🚀 Starting EventFlow server...")
    print("=" * 50)
    print("🌐 Open: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/api/docs")
    print("")
    print("Demo accounts:")
    print("  🔴 Admin:     admin@eventflow.com / admin123")
    print("  🟡 Organizer: organizer@eventflow.com / org123")
    print("  🟢 Attendee:  attendee@eventflow.com / att123")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")

    os.execvp("uvicorn", ["uvicorn", "main:app", "--reload", "--port", "8000", "--host", "0.0.0.0"])

if __name__ == "__main__":
    main()
