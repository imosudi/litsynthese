import os
from dotenv import load_dotenv

# Load local environment parameters
load_dotenv()

# Server parameters
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes")

# API keys for other LLM providers
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Base directory for all academic projects data
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECTS_BASE_DIR = os.path.join(BASE_DIR, "data", "projects")
