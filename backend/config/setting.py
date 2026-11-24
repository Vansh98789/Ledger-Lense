import os
from dotenv import load_dotenv

load_dotenv()


if not os.getenv("GROQ_API_KEY"):
    raise ValueError("Groq Api key need to set ")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
