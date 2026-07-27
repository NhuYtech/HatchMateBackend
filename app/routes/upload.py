from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from app.services.image_service import image_service
from app.services.ai_service import ai_service

router = APIRouter()

@router.post("/upload-incubator-image")
async def upload_incubator_image(
    machineId: str = Form(..., description="Mã máy ấp trứng (VD: MATG01)"),
    batchId: str = Form(..., description="Mã lô ấp trứng (VD: BATCH001)"),
    incubationDay: int = Form(..., description="Ngày ấp trứng hiện tại (VD: 5)"),
    phase: str = Form(..., description="Giai đoạn ấp trứng (VD: early, middle, late)"),
    capturedAt: str | None = Form(None, description="Thời gian chụp ảnh định dạng ISO string (Tùy chọn)"),
    file: UploadFile = File(..., description="Tệp ảnh chụp từ camera (.jpg, .png)")
):
    # 1. Kiểm tra tính hợp lệ của tham số đầu vào (Validate input)
    if not machineId or not machineId.strip():
        raise HTTPException(status_code=422, detail="machineId không được phép trống")
        
    if not batchId or not batchId.strip():
        raise HTTPException(status_code=422, detail="batchId không được phép trống")
        
    if incubationDay < 0:
        raise HTTPException(status_code=422, detail="incubationDay không được phép nhỏ hơn 0")
        
    if not phase or not phase.strip():
        raise HTTPException(status_code=422, detail="phase không được phép trống")

    # 2. Chuyển tiếp luồng xử lý tới ImageService
    result = await image_service.process_upload(
        machine_id=machineId.strip(),
        batch_id=batchId.strip(),
        incubation_day=incubationDay,
        phase=phase.strip(),
        file=file,
        captured_at=capturedAt.strip() if capturedAt else None
    )

    # 3. Trả về phản hồi thành công
    return {
        "success": True,
        "message": "Image uploaded successfully",
        "data": result
    }

@router.post("/predict")
async def predict_incubator_eggs(
    file: UploadFile = File(..., description="Tệp ảnh chụp từ camera (.jpg, .png)")
):
    """
    Endpoint nhận diện và đếm số lượng trứng bằng mô hình AI.
    Trả về cấu hình JSON chuẩn cho Web Dashboard.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không tìm thấy file ảnh")

    content_type = file.content_type
    if content_type and not content_type.startswith("image/") and content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail="Tệp tải lên phải là hình ảnh")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Nội dung file ảnh rỗng")

    return ai_service.predict(content)


