# Smart Hatch System Camera Processing Backend

Backend được xây dựng bằng **Python + FastAPI** phục vụ nhận diện và xử lý hình ảnh chụp từ Camera ESP32-S3 trong máy ấp trứng, tự động tải lên **Firebase Storage** và đồng bộ metadata vào **Firebase Realtime Database**.

---

## 1. Cấu trúc thư mục dự án

```text
HatchMateBackend/
│── app/
│   ├── routes/
│   │   ├── __init__.py
│   │   └── upload.py            # API Route nhận dữ liệu từ ESP32/Client
│   ├── services/
│   │   ├── __init__.py
│   │   └── image_service.py     # Logic xử lý nghiệp vụ upload & db sync
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py           # Tiện ích định dạng file/datetime
│   ├── __init__.py
│   ├── config.py                # Đọc cấu hình .env (Pydantic settings)
│   ├── firebase_service.py      # Khởi tạo Firebase Admin SDK Singleton
│   └── main.py                  # Entrypoint chính khởi tạo FastAPI
│── requirements.txt             # Định nghĩa thư viện cài đặt
│── .env.example                 # Mẫu cấu hình môi trường
```

---

## 2. Hướng dẫn cài đặt & Khởi chạy

### Bước 1: Khởi tạo môi trường ảo Python (Virtual Environment)
Trong thư mục `HatchMateBackend/`, thực hiện chạy lệnh:

* **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Bước 2: Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

### Bước 3: Thiết lập cấu hình biến môi trường
1. Sao chép tệp mẫu cấu hình:
   ```bash
   cp .env.example .env
   ```
2. Mở tệp `.env` vừa tạo và cập nhật các thông số liên quan đến Firebase của bạn:
   - `FIREBASE_DATABASE_URL`: Đường dẫn Realtime Database của bạn.
   - `FIREBASE_STORAGE_BUCKET`: Tên bucket Storage (không chứa gs://).
   - `FIREBASE_CREDENTIALS_PATH`: Đặt tệp khóa bí mật JSON `firebase-credentials.json` của bạn vào thư mục `HatchMateBackend/app/` và cấu hình đường dẫn tương ứng trong `.env`.

### Bước 4: Khởi chạy Server Uvicorn
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Khi chạy thành công, tài liệu API tương tác tự động sẽ có sẵn tại: `http://localhost:8000/docs`.

---

## 3. Ví dụ kiểm thử qua cURL

Sử dụng lệnh sau để mô phỏng ESP32-S3 hoặc Client gửi một tệp ảnh kèm metadata lên máy chủ:

* **Mẫu cURL lệnh chạy trên Linux / macOS / Git Bash:**
  ```bash
  curl -X 'POST' \
    'http://localhost:8000/api/upload-incubator-image' \
    -H 'accept: application/json' \
    -H 'Content-Type: multipart/form-data' \
    -F 'machineId=MATG01' \
    -F 'batchId=BATCH001' \
    -F 'incubationDay=5' \
    -F 'phase=middle' \
    -F 'file=@/duong/dan/anh/mau.jpg;type=image/jpeg'
  ```

* **Mẫu cURL lệnh chạy trên Windows PowerShell (cần thay đường dẫn ảnh thật):**
  ```powershell
  $Form = @{
      machineId = 'MATG01'
      batchId = 'BATCH001'
      incubationDay = '5'
      phase = 'middle'
      file = Get-Item -Path "C:\duong\dan\anh\mau.jpg"
  }
  Invoke-RestMethod -Uri 'http://localhost:8000/api/upload-incubator-image' -Method Post -Form $Form
  ```

---

## 4. Ví dụ Phản hồi (API Responses)

### A. Phản hồi thành công (200 OK)
```json
{
  "success": true,
  "message": "Image uploaded successfully",
  "data": {
    "imageId": "4e72c842-881b-4f51-b8d4-ae235c43d838",
    "machineId": "MATG01",
    "batchId": "BATCH001",
    "storagePath": "incubators/MATG01/batches/BATCH001/images/raw/2026-07-10_08-00-00.jpg",
    "downloadUrl": "https://storage.googleapis.com/hatchmate-iot.appspot.com/incubators/MATG01/batches/BATCH001/images/raw/2026-07-10_08-00-00.jpg",
    "capturedAt": "2026-07-10T08:00:00Z",
    "incubationDay": 5,
    "phase": "middle"
  }
}
```

### B. Phản hồi lỗi Tham số/Xác thực (422 Unprocessable Entity)
```json
{
  "detail": "machineId không được phép trống"
}
```

### C. Phản hồi lỗi Định dạng file (400 Bad Request)
```json
{
  "detail": "Định dạng tệp không hợp lệ. Chỉ chấp nhận tệp ảnh (.jpg, .jpeg, .png)"
}
```
