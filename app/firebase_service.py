import os
import json
import base64
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
            cls._instance._bucket = None
            cls._instance._db_reference = None
            cls._instance._initialized = False
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        if self._initialized:
            return

        if not firebase_admin._apps:
            cred = None
            cred_json_env = os.getenv("FIREBASE_CREDENTIALS_JSON")
            cred_b64_env = os.getenv("FIREBASE_CREDENTIALS_BASE64")
            cred_path = settings.FIREBASE_CREDENTIALS_PATH
            
            # 1. Đọc từ biến môi trường FIREBASE_CREDENTIALS_JSON (chuỗi JSON trực tiếp)
            if cred_json_env:
                try:
                    logger.info("Khởi tạo Firebase Admin SDK từ biến môi trường FIREBASE_CREDENTIALS_JSON")
                    cred_dict = json.loads(cred_json_env)
                    cred = credentials.Certificate(cred_dict)
                except Exception as e:
                    logger.error(f"Lỗi khi đọc FIREBASE_CREDENTIALS_JSON: {e}")

            # 2. Đọc từ biến môi trường FIREBASE_CREDENTIALS_BASE64
            if not cred and cred_b64_env:
                try:
                    logger.info("Khởi tạo Firebase Admin SDK từ biến môi trường FIREBASE_CREDENTIALS_BASE64")
                    decoded = base64.b64decode(cred_b64_env).decode("utf-8")
                    cred_dict = json.loads(decoded)
                    cred = credentials.Certificate(cred_dict)
                except Exception as e:
                    logger.error(f"Lỗi khi đọc FIREBASE_CREDENTIALS_BASE64: {e}")

            # 3. Đọc từ đường dẫn tệp trong settings
            if not cred and cred_path and os.path.exists(cred_path):
                try:
                    logger.info(f"Khởi tạo Firebase Admin SDK bằng credentials JSON tại: {cred_path}")
                    cred = credentials.Certificate(cred_path)
                except Exception as e:
                    logger.error(f"Lỗi khi đọc tệp credentials tại {cred_path}: {e}")

            # 4. Đọc từ Secret Files của Render (/etc/secrets/...)
            possible_secret_paths = [
                "/etc/secrets/firebase-credentials.json",
                "/etc/secrets/firebase_credentials.json",
                "firebase-credentials.json",
                "app/firebase-credentials.json"
            ]
            if not cred:
                for spath in possible_secret_paths:
                    if os.path.exists(spath):
                        try:
                            logger.info(f"Khởi tạo Firebase Admin SDK từ Secret File: {spath}")
                            cred = credentials.Certificate(spath)
                            break
                        except Exception as e:
                            logger.error(f"Lỗi khi đọc secret file {spath}: {e}")

            if not cred:
                logger.warning(
                    f"Không tìm thấy tệp credentials Firebase hoặc biến môi trường FIREBASE_CREDENTIALS_JSON. "
                    "Sẽ cố gắng sử dụng Application Default Credentials (ADC)..."
                )
                try:
                    cred = credentials.ApplicationDefault()
                except Exception as e:
                    logger.error(f"Không thể tạo ApplicationDefault credentials: {e}")
                    cred = None

            try:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': settings.FIREBASE_DATABASE_URL,
                    'storageBucket': settings.FIREBASE_STORAGE_BUCKET
                })
                logger.info("Khởi tạo Firebase Admin SDK thành công.")
                self._initialized = True
            except Exception as e:
                logger.error(f"Lỗi khi initialize_app Firebase: {e}")

    @property
    def bucket(self):
        if self._bucket is None:
            try:
                self._bucket = storage.bucket()
            except Exception as e:
                logger.error(f"Không thể truy cập Firebase Storage bucket: {e}")
                raise RuntimeError(
                    "Không thể kết nối Firebase Storage. Vui lòng cấu hình FIREBASE_CREDENTIALS_JSON "
                    "hoặc thêm Secret File firebase-credentials.json trên Render."
                ) from e
        return self._bucket

    @property
    def db_reference(self):
        if self._db_reference is None:
            try:
                self._db_reference = db.reference()
            except Exception as e:
                logger.error(f"Không thể truy cập Firebase Realtime Database reference: {e}")
                raise RuntimeError(
                    "Không thể kết nối Firebase Realtime Database. Vui lòng cấu hình FIREBASE_CREDENTIALS_JSON "
                    "hoặc thêm Secret File firebase-credentials.json trên Render."
                ) from e
        return self._db_reference

# Khởi tạo instance toàn cục (Singleton)
firebase_service = FirebaseService()
