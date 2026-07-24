from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./resume_intel.db"
    max_upload_mb: int = 5
    upload_dir: str = "./uploads"

    class Config:
        env_file = ".env"

settings = Settings()
