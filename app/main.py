import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import upload
from app.services.ai_service import ai_service

app = FastAPI(
    title="Smart Hatch System Camera Processing Backend",
    description="Backend API nhận diện và xử lý ảnh chụp từ camera ESP32-S3 gắn trong máy ấp.",
    version="1.0.0"
)

# Cấu hình CORS để cho phép Web Dashboard và Web Client kết nối dễ dàng
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các endpoints của router upload (hỗ trợ cả /api và /)
app.include_router(upload.router, prefix="/api", tags=["Camera Processing"])
app.include_router(upload.router, tags=["Camera Processing"])

@app.get("/health")
async def health_check():
    """Kiểm tra tình trạng hoạt động của hệ thống"""
    return {
        "status": "healthy",
        "firebase_connection": "connected",
        "ai_model_loaded": ai_service.is_ready()
    }

if __name__ == "__main__":
    # Khởi chạy server uvicorn trực tiếp bằng python
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )
