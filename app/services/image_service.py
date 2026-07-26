import logging
from fastapi import UploadFile, HTTPException
from app.firebase_service import firebase_service
from app.utils.helpers import (
    get_current_iso_timestamp,
    generate_safe_filename,
    generate_storage_path,
    generate_uuid
)

logger = logging.getLogger("uvicorn.error")

class ImageService:
    async def process_upload(
        self,
        machine_id: str,
        batch_id: str,
        incubation_day: int,
        phase: str,
        file: UploadFile,
        captured_at: str | None = None
    ) -> dict:
        # 1. Kiểm tra File tải lên
        if not file.filename:
            raise HTTPException(status_code=400, detail="Không tìm thấy tên file trong yêu cầu")
            
        content_type = file.content_type
        if not content_type or not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Định dạng tệp không hợp lệ. Chỉ chấp nhận tệp ảnh (.jpg, .jpeg, .png)")

        # Đọc dữ liệu nhị phân của ảnh
        try:
            file_content = await file.read()
        except Exception as e:
            logger.error(f"Lỗi khi đọc file upload: {str(e)}")
            raise HTTPException(status_code=500, detail="Không thể đọc nội dung file ảnh")

        # 2. Xử lý thời gian chụp
        if not captured_at:
            captured_at = get_current_iso_timestamp()

        # 3. Tạo tên file và đường dẫn Storage trên Firebase
        filename = generate_safe_filename(captured_at, file.filename)
        storage_path = generate_storage_path(machine_id, batch_id, filename)

        # 4. Thực hiện upload ảnh lên Firebase Storage
        try:
            download_url = self.upload_image_to_storage(storage_path, file_content, content_type)
        except Exception as e:
            logger.error(f"Lỗi khi tải ảnh lên Firebase Storage: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lỗi kết nối Firebase Storage: {str(e)}")

        # 5. Tạo metadata và lưu vào Realtime Database
        image_id = generate_uuid()
        metadata = {
            "imageId": image_id,
            "machineId": machine_id,
            "batchId": batch_id,
            "capturedAt": captured_at,
            "incubationDay": incubation_day,
            "phase": phase,
            "storagePath": storage_path,
            "downloadUrl": download_url,
            "analysisStatus": "pending",  # Mặc định là pending chờ hệ thống AI xử lý sau
            "detectedEggCount": 0,
            "missingEggCount": 0,
            "alert": False,
            "createdAt": get_current_iso_timestamp(),
            
            # Các trường mở rộng chuẩn bị sẵn cho AI model tích hợp sau này
            "annotatedImageUrl": "",
            "confidence": 0.0,
            "processingDurationMs": 0,
            "aiModelVersion": ""
        }

        try:
            self.save_image_metadata(machine_id, image_id, metadata)
        except Exception as e:
            logger.error(f"Lỗi khi ghi metadata vào Realtime Database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lỗi lưu trữ thông tin cơ sở dữ liệu: {str(e)}")

        return {
            "imageId": image_id,
            "machineId": machine_id,
            "batchId": batch_id,
            "storagePath": storage_path,
            "downloadUrl": download_url,
            "capturedAt": captured_at,
            "incubationDay": incubation_day,
            "phase": phase
        }

    def upload_image_to_storage(self, storage_path: str, content: bytes, content_type: str) -> str:
        """Tải dữ liệu nhị phân lên Firebase Storage và trả về URL tải ảnh công khai"""
        bucket = firebase_service.bucket
        blob = bucket.blob(storage_path)
        
        # Upload dữ liệu ảnh
        blob.upload_from_string(content, content_type=content_type)
        
        # Cố gắng cấp quyền public cho ảnh để ứng dụng hiển thị trực tiếp
        try:
            blob.make_public()
            return blob.public_url
        except Exception as e:
            logger.warning(f"Không thể make_public cho blob, chuyển sang dùng Signed URL có thời hạn: {str(e)}")
            # Trường hợp bucket bị chặn quyền IAM public, tạo Signed URL có hiệu lực 10 năm làm fallback
            from datetime import timedelta
            return blob.generate_signed_url(expiration=timedelta(days=3650))

    def save_image_metadata(self, machine_id: str, image_id: str, metadata: dict) -> None:
        """Lưu metadata vào Firebase Realtime Database tại path: incubators/{machineId}/images/{imageId}"""
        db_ref = firebase_service.db_reference
        image_ref = db_ref.child("incubators").child(machine_id).child("images").child(image_id)
        image_ref.set(metadata)

    async def process_raw_image(
        self,
        machine_id: str,
        batch_id: str,
        incubation_day: int,
        phase: str,
        file_content: bytes,
        filename: str = "capture.jpg",
        content_type: str = "image/jpeg",
        captured_at: str | None = None
    ) -> dict:
        """Xử lý và tải trực tiếp dữ liệu ảnh nhị phân (raw bytes) lên Firebase"""
        # 1. Kiểm tra dữ liệu ảnh nhị phân
        if not file_content:
            raise HTTPException(status_code=400, detail="Nội dung file ảnh rỗng")

        # 2. Xử lý thời gian chụp
        if not captured_at:
            captured_at = get_current_iso_timestamp()

        # 3. Tạo tên file và đường dẫn Storage trên Firebase
        filename = generate_safe_filename(captured_at, filename)
        storage_path = generate_storage_path(machine_id, batch_id, filename)

        # 4. Thực hiện upload ảnh lên Firebase Storage
        try:
            download_url = self.upload_image_to_storage(storage_path, file_content, content_type)
        except Exception as e:
            logger.error(f"Lỗi khi tải ảnh lên Firebase Storage: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lỗi kết nối Firebase Storage: {str(e)}")

        # 5. Tạo metadata và lưu vào Realtime Database
        image_id = generate_uuid()
        metadata = {
            "imageId": image_id,
            "machineId": machine_id,
            "batchId": batch_id,
            "capturedAt": captured_at,
            "incubationDay": incubation_day,
            "phase": phase,
            "storagePath": storage_path,
            "downloadUrl": download_url,
            "analysisStatus": "pending",  # Mặc định là pending chờ hệ thống AI xử lý sau
            "detectedEggCount": 0,
            "missingEggCount": 0,
            "alert": False,
            "createdAt": get_current_iso_timestamp(),
            
            # Các trường mở rộng chuẩn bị sẵn cho AI model tích hợp sau này
            "annotatedImageUrl": "",
            "confidence": 0.0,
            "processingDurationMs": 0,
            "aiModelVersion": ""
        }

        try:
            self.save_image_metadata(machine_id, image_id, metadata)
            # Cập nhật previewImage và latestImage của camera trong RTDB để web/app hiển thị ngay
            db_ref = firebase_service.db_reference
            # Cập nhật previewImage
            db_ref.child("incubators").child(machine_id).child("previewImage").set(download_url)
            # Cập nhật latestImage
            db_ref.child("incubators").child(machine_id).child("camera").child("latestImage").set({
                "imageUrl": download_url,
                "uploadedAt": {".sv": "timestamp"},
                "fileName": filename
            })
        except Exception as e:
            logger.error(f"Lỗi khi ghi metadata vào Realtime Database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lỗi lưu trữ thông tin cơ sở dữ liệu: {str(e)}")

        return {
            "imageId": image_id,
            "machineId": machine_id,
            "batchId": batch_id,
            "storagePath": storage_path,
            "downloadUrl": download_url,
            "capturedAt": captured_at,
            "incubationDay": incubation_day,
            "phase": phase
        }

# Tạo service instance toàn cục
image_service = ImageService()
