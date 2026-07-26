import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    FIREBASE_CREDENTIALS_PATH: str = "app/firebase-credentials.json"
    FIREBASE_DATABASE_URL: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""
    CAMERA_CAPTURE_INTERVAL_SECONDS: int = 10800 # 3 giờ (3 * 3600 giây)

    model_config = SettingsConfigDict(
        # Tìm tệp .env ở thư mục gốc của backend (cha của thư mục app/)
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Khởi tạo instance cấu hình toàn cục
settings = Settings()
