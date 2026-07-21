"""SimulateAI configuration — reads from environment variables with sensible defaults.

Load order:
1. .env file in project root (if python-dotenv is installed)
2. Environment variables (override .env)
3. Hardcoded defaults (fallback)

For local development, copy .env.example to .env and fill in your keys.
"""

import os
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # dotenv not installed — rely on real env vars or defaults


# --- LLM Provider ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "ollama", "gemini", or "openai"

# --- Ollama Settings ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# --- Gemini Settings ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

# --- OpenAI-compatible API Settings ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "claude-sonnet-4.6")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# --- Default Model (derived from provider) ---
DEFAULT_MODEL = (
    GEMINI_MODEL if LLM_PROVIDER == "gemini"
    else OPENAI_MODEL if LLM_PROVIDER == "openai"
    else "qwen2.5:3b"
)

# --- Concurrency & Timeout ---
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120.0"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "5"))

# --- RAG Settings ---
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in ("true", "1", "yes")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
