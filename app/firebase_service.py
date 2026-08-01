import os
import logging
import firebase_admin
from firebase_admin import credentials, db, storage
from app.config import settings

logger = logging.getLogger("uvicorn.error")

class FirebaseService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        # Kiểm tra xem ứng dụng Firebase đã được khởi tạo chưa
        if not firebase_admin._apps:
            cred = None
            cred_json_env = os.getenv("FIREBASE_CREDENTIALS_JSON")
            cred_path = settings.FIREBASE_CREDENTIALS_PATH
            
            # 1. Thử đọc từ biến môi trường FIREBASE_CREDENTIALS_JSON (dạng chuỗi JSON)
            if cred_json_env:
                try:
                    import json
                    logger.info("Khởi tạo Firebase Admin SDK từ biến môi trường FIREBASE_CREDENTIALS_JSON")
                    cred_dict = json.loads(cred_json_env)
                    cred = credentials.Certificate(cred_dict)
                except Exception as e:
                    logger.error(f"Lỗi khi đọc FIREBASE_CREDENTIALS_JSON: {e}")

            # 2. Thử đọc từ đường dẫn file trong settings
            if not cred and cred_path and os.path.exists(cred_path):
                logger.info(f"Khởi tạo Firebase Admin SDK bằng credentials JSON tại: {cred_path}")
                cred = credentials.Certificate(cred_path)
                
            # 3. Thử đọc từ Render Secret File (/etc/secrets/firebase-credentials.json)
            if not cred and os.path.exists("/etc/secrets/firebase-credentials.json"):
                logger.info("Khởi tạo Firebase Admin SDK từ Render Secret File (/etc/secrets/firebase-credentials.json)")
                cred = credentials.Certificate("/etc/secrets/firebase-credentials.json")

            if not cred:
                logger.warning(
                    f"Không tìm thấy credentials JSON tại {cred_path} hoặc biến môi trường FIREBASE_CREDENTIALS_JSON. "
                    "Sẽ cố gắng sử dụng Application Default Credentials (ADC)..."
                )
                try:
                    cred = credentials.ApplicationDefault()
                except Exception as e:
                    logger.error(f"Không thể tạo credentials mặc định: {e}")
                    cred = None

            # Thực hiện khởi tạo
            firebase_admin.initialize_app(cred, {
                'databaseURL': settings.FIREBASE_DATABASE_URL,
                'storageBucket': settings.FIREBASE_STORAGE_BUCKET
            })
            logger.info("Khởi tạo Firebase Admin SDK thành công.")
                
        # Gán bucket và reference để sử dụng ở các lớp nghiệp vụ
        self.bucket = storage.bucket()
        self.db_reference = db.reference()

# Khởi tạo instance toàn cục (Singleton)
firebase_service = FirebaseService()
