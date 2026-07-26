import asyncio
import logging
import urllib.request
import time
from app.firebase_service import firebase_service
from app.config import settings
from app.services.image_service import image_service

logger = logging.getLogger("uvicorn.error")

async def fetch_image_from_camera(ip_or_url: str) -> bytes | None:
    """Tải hình ảnh tĩnh từ camera ESP32-CAM qua cổng LAN"""
    # Xử lý định dạng IP/URL
    if "://" in ip_or_url:
        from urllib.parse import urlparse
        parsed = urlparse(ip_or_url)
        host = parsed.hostname
        capture_url = f"http://{host}/capture"
    else:
        clean_ip = ip_or_url.split(":")[0]
        capture_url = f"http://{clean_ip}/capture"

    try:
        logger.info(f"Đang gọi URL chụp ảnh: {capture_url}")
        # Chạy trong threadpool của asyncio để tránh chặn event loop chính
        def do_request():
            with urllib.request.urlopen(capture_url, timeout=10) as response:
                return response.read()
                
        loop = asyncio.get_running_loop()
        image_bytes = await loop.run_in_executor(None, do_request)
        return image_bytes
    except Exception as e:
        logger.error(f"Không thể lấy ảnh từ camera tại {capture_url}: {e}")
        return None

async def check_and_capture_all_cameras():
    """Kiểm tra và thực hiện chụp ảnh cho tất cả máy ấp đang trong chu kỳ hoạt động"""
    db_ref = firebase_service.db_reference
    try:
        incubators = db_ref.child("incubators").get()
        if not incubators:
            return

        for machine_id, data in incubators.items():
            if not isinstance(data, dict):
                continue

            # 1. Kiểm tra chu kỳ ấp có đang hoạt động không
            cycle = data.get("cycle", {})
            cycle_is_active = cycle.get("isActive", False)
            
            # Đọc ngày ấp hiện tại và tổng số ngày
            telemetry = data.get("telemetry", {})
            sensors = data.get("sensors", {})
            
            day = telemetry.get("day") or sensors.get("day") or data.get("day") or 1
            total_days = cycle.get("totalDays") or data.get("cycleTotalDays") or 21
            
            # Kiểm tra thời gian kết thúc ấp
            if not cycle_is_active or day > total_days:
                # Không ở trong chu kỳ hoạt động hoặc đã kết thúc
                continue

            # 2. Kiểm tra cấu hình camera
            camera = data.get("camera", {})
            camera_ip = camera.get("ip") or data.get("ipAddress") or data.get("ip")
            if not camera_ip:
                logger.warning(f"Máy ấp {machine_id} đang hoạt động nhưng không có cấu hình IP camera.")
                continue

            # 3. Kiểm tra khoảng thời gian đã trôi qua kể từ lần chụp cuối
            last_capture_time = camera.get("last_capture_time", 0)
            current_time = int(time.time())
            interval = getattr(settings, "CAMERA_CAPTURE_INTERVAL_SECONDS", 10800) # Mặc định 3 giờ (10800 giây)

            if current_time - last_capture_time < interval:
                # Chưa đến thời gian chụp tiếp theo
                continue

            logger.info(f"Đủ điều kiện chụp ảnh định kỳ cho {machine_id}. Lần cuối: {last_capture_time}, Hiện tại: {current_time}")

            # 4. Tải ảnh từ ESP32-CAM
            image_bytes = await fetch_image_from_camera(camera_ip)
            if not image_bytes:
                continue

            # 5. Xác định batchId và phase
            batch_id = cycle.get("batchId") or cycle.get("startDate") or "BATCH_AUTO"
            phase_num = telemetry.get("phase") or sensors.get("phase") or data.get("phase") or 1
            
            # Map phase integer sang string
            if phase_num == 1:
                phase_str = "early"
            elif phase_num == 2:
                phase_str = "middle"
            elif phase_num == 3:
                phase_str = "late"
            else:
                phase_str = "after"

            # 6. Upload ảnh và ghi metadata lên database
            try:
                result = await image_service.process_raw_image(
                    machine_id=machine_id,
                    batch_id=batch_id,
                    incubation_day=day,
                    phase=phase_str,
                    file_content=image_bytes,
                    filename=f"auto_capture_{current_time}.jpg"
                )
                
                # Cập nhật thời gian chụp ảnh cuối cùng lên Firebase
                db_ref.child("incubators").child(machine_id).child("camera").child("last_capture_time").set(current_time)
                logger.info(f"Đã chụp ảnh định kỳ thành công cho {machine_id}: {result['downloadUrl']}")
            except Exception as e:
                logger.error(f"Lỗi khi xử lý lưu ảnh chụp định kỳ cho {machine_id}: {e}")

    except Exception as e:
        logger.error(f"Lỗi khi quét danh sách máy ấp trong bộ lập lịch: {e}")

async def run_periodic_capture():
    """Hàm chạy vòng lặp vô hạn giám sát lịch chụp ảnh"""
    logger.info("Khởi chạy bộ lập lịch chụp ảnh camera định kỳ...")
    # Đợi 10 giây ban đầu để đảm bảo Firebase Admin SDK đã khởi tạo hoàn toàn
    await asyncio.sleep(10)
    
    while True:
        try:
            await check_and_capture_all_cameras()
        except Exception as e:
            logger.error(f"Lỗi hệ thống trong vòng lặp chụp ảnh: {e}")
        
        # Kiểm tra mỗi 30 giây
        await asyncio.sleep(30)
