import os
import uuid
from datetime import datetime, timezone

def get_current_iso_timestamp() -> str:
    """Trả về thời gian hiện tại theo định dạng ISO 8601 UTC (VD: 2026-07-10T08:00:00Z)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def generate_safe_filename(captured_at_str: str | None = None, original_filename: str = "") -> str:
    """
    Tạo tên file an toàn dựa trên thời gian chụp ảnh.
    Định dạng: YYYY-MM-DD_HH-MM-SS.jpg hoặc .png tùy theo file gốc.
    """
    ext = ".jpg"
    if original_filename:
        _, file_ext = os.path.splitext(original_filename.lower())
        if file_ext in [".png", ".jpg", ".jpeg"]:
            ext = file_ext if file_ext != ".jpeg" else ".jpg"

    if captured_at_str:
        try:
            # Xử lý chuỗi thời gian ISO string
            clean_str = captured_at_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            timestamp_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
            return f"{timestamp_str}{ext}"
        except Exception:
            # Bỏ qua nếu parse lỗi và chuyển sang fallback
            pass

    # Fallback: sử dụng thời gian hiện tại của hệ thống
    return f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}{ext}"

def generate_storage_path(machine_id: str, batch_id: str, filename: str) -> str:
    """
    Tạo đường dẫn lưu trữ trên Firebase Storage.
    Cấu trúc: incubators/{machineId}/batches/{batchId}/images/raw/{filename}
    """
    # Chuẩn hóa để tránh các lỗ hổng về đường dẫn thư mục
    clean_machine_id = "".join(c for c in machine_id if c.isalnum() or c in "-_")
    clean_batch_id = "".join(c for c in batch_id if c.isalnum() or c in "-_")
    
    return f"incubators/{clean_machine_id}/batches/{clean_batch_id}/images/raw/{filename}"

def generate_uuid() -> str:
    """Tạo chuỗi định danh UUID duy nhất"""
    return str(uuid.uuid4())
