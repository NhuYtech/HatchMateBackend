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
            cred_path = settings.FIREBASE_CREDENTIALS_PATH
            
            # Kiểm tra tệp JSON credentials có tồn tại không
            if cred_path and os.path.exists(cred_path):
                logger.info(f"Khởi tạo Firebase Admin SDK bằng credentials JSON tại: {cred_path}")
                cred = credentials.Certificate(cred_path)
            else:
                logger.warning(
                    f"Không tìm thấy credentials JSON tại {cred_path}. "
                    "Sẽ cố gắng sử dụng Application Default Credentials (ADC) mặc định..."
                )
                try:
                    cred = credentials.ApplicationDefault()
                except Exception as e:
                    logger.error(
                        "Không thể khởi tạo credentials mặc định. "
                        "Vui lòng tạo tệp .env và đặt cấu hình chính xác cho FIREBASE_CREDENTIALS_PATH."
                    )
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
