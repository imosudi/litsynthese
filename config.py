import os
import socket
from dotenv import load_dotenv

# Force IPv4 resolution to prevent connection hangs in IPv6-unsupported networks
original_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

# Load local environment parameters
load_dotenv()

# Server parameters
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes")

# API keys for LLM providers
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Base directory for all academic projects data
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECTS_BASE_DIR = os.path.join(BASE_DIR, "data", "projects")

# Model fallback configurations for downstream LLM services
GEMINI_MODELS_FALLBACK = [
    "gemini-3.5-pro",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemini-3.1-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash"
]

LLAMA_MODELS_FALLBACK = [
    "groq/llama-3.1-70b-versatile",
    "groq/llama-3.1-8b-instant",
    "openrouter/meta-llama/llama-3.1-70b-instruct",
    "openrouter/meta-llama/llama-3.1-8b-instruct"
]


