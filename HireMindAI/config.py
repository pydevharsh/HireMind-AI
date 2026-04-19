import os
from dotenv import load_dotenv

# .env file से environment variables load करेगा
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # Groq AI API
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # ElevenLabs Text to Speech API
    ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")