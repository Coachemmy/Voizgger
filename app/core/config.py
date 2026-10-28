import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    META_API_KEY: str = os.getenv("MODEL_API_KEY", "")
    META_BASE_URL: str = "https://api.meta.ai/v1"
    MODEL_TEXT: str = "muse-spark-1.3"
    MODEL_AUDIO: str = "meta-models/muse-voice-transcribe"
    MODEL_VISION: str = "muse-wonder-1.0"

settings = Settings()