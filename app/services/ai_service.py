import base64
import io
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# Đường dẫn tới file weight, nằm tại app/models/best.pt
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best.pt"
CONFIDENCE_THRESHOLD = 0.15  # Ngưỡng tin cậy tối ưu để phát hiện đầy đủ tất cả quả trứng ngay cả khi bị che khuất một phần


class AIService:
    """
    Service chịu trách nhiệm load model YOLOv8 (best.pt) và chạy inference
    để phát hiện, đếm số lượng trứng trong ảnh.

    Model chỉ được load DUY NHẤT 1 LẦN khi server khởi động (singleton pattern),
    KHÔNG load lại mỗi request - vì load model rất chậm (vài giây), còn
    chạy inference trên model đã load sẵn thì rất nhanh (vài chục ms - vài trăm ms).
    """

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if not MODEL_PATH.exists():
            logger.warning(
                f"Không tìm thấy model weights tại: {MODEL_PATH}. "
                f"AI prediction sẽ trả về success=False cho tới khi có file best.pt."
            )
            return
        try:
            logger.info(f"Đang tải model YOLOv8 từ: {MODEL_PATH}")
            self.model = YOLO(str(MODEL_PATH))
            # Ghi đè tên nhãn lớp 0 thành 'Egg' (dùng ASCII để OpenCV result.plot() không bị lỗi font Unicode)
            try:
                if hasattr(self.model, "names") and isinstance(self.model.names, dict):
                    self.model.names[0] = "Egg"
                if hasattr(self.model, "model") and hasattr(self.model.model, "names") and isinstance(self.model.model.names, dict):
                    self.model.model.names[0] = "Egg"
            except Exception as name_err:
                logger.warning(f"Không thể ghi đè tên class 0: {name_err}")

            logger.info("Tải model YOLOv8 thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi tải model YOLOv8: {e}")
            self.model = None

    def is_ready(self) -> bool:
        """Kiểm tra model đã sẵn sàng để inference chưa (dùng cho /health endpoint)."""
        return self.model is not None

    def predict(self, image_bytes: bytes) -> dict:
        """
        Nhận vào bytes ảnh thô, trả về dict chuẩn cho route.ts:
        { success, detectedCount, confidence, processedImageBase64, message }
        """
        if not self.is_ready():
            return {
                "success": False,
                "detectedCount": 0,
                "confidence": 0.0,
                "processedImageBase64": "",
                "message": "Model AI chưa được nạp (best.pt không tồn tại hoặc lỗi khi load).",
            }

        try:
            # Decode bytes ảnh -> numpy array định dạng BGR (chuẩn OpenCV)
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_np = np.array(pil_image)
            image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

            # Chạy inference
            results = self.model.predict(source=image_bgr, conf=CONFIDENCE_THRESHOLD, verbose=False)
            result = results[0]

            boxes = result.boxes
            detected_count = int(len(boxes)) if boxes is not None else 0
            avg_confidence = float(boxes.conf.mean()) if detected_count > 0 else 0.0

            # Vẽ bounding box lên ảnh (trả về numpy array đã annotate)
            plotted_bgr = result.plot()
            success_encode, buffer = cv2.imencode(".jpg", plotted_bgr)
            if not success_encode:
                raise RuntimeError("Không thể encode ảnh kết quả sang JPEG")

            processed_base64 = base64.b64encode(buffer).decode("utf-8")

            return {
                "success": True,
                "detectedCount": detected_count,
                "confidence": round(avg_confidence, 4),
                "processedImageBase64": processed_base64,
                "message": "Phân tích thành công",
            }

        except Exception as e:
            logger.error(f"Lỗi khi chạy inference AI: {e}")
            return {
                "success": False,
                "detectedCount": 0,
                "confidence": 0.0,
                "processedImageBase64": "",
                "message": f"Lỗi xử lý ảnh AI: {str(e)}",
            }


# Singleton - được khởi tạo (và load model) NGAY khi module này được import lần đầu tiên,
# tức là ngay lúc uvicorn khởi động server, không phải lúc có request đầu tiên gọi tới.
ai_service = AIService()