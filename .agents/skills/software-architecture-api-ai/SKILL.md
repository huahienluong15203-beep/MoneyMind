---
name: software-architecture-api-ai
description: Thiết kế Kiến trúc Phần mềm Clean Architecture/MVC, Bảng đặc tả RESTful API 11 endpoints và Tích hợp Google Gemini Flash an toàn cho MoneyMind. Bao gồm thuật toán PII Sanitization, System Prompt chuẩn hóa, chiến lược Caching, Fallback Timeout 5s và Rate Limiting.
---

# Kỹ Năng: Kiến Trúc Phần Mềm, RESTful API & Tích Hợp AI

> **Chuyên môn**: Lead Software Architect & AI Integration Specialist
> **Nhiệm vụ**: Thiết kế kiến trúc tổng thể mã nguồn, danh sách hợp đồng RESTful API và đặc tả giải pháp tích hợp Google Gemini Flash an toàn.

---

## Bộ Nguyên Tắc Bắt Buộc

1. **Chuẩn RESTful API**: Endpoint danh từ số nhiều hoặc theo ngữ cảnh phân hệ, đồng nhất tuyệt đối với mã chức năng (VD: dùng `/api/v1/thong-ke/tong-quan`, không được lệch sang `/dashboard/summary`).
2. **An toàn dữ liệu AI (PII Protection)**: Cấm tuyệt đối việc truyền thông tin định danh (họ tên, email, sdt) sang bên thứ ba. Dữ liệu chỉ được gửi dưới dạng JSON số liệu đã ẩn danh.
3. **Thiết kế chống nghẽn và chi phí**: Bắt buộc có cơ chế Rate Limiting, Timeout (5s), Caching và Fallback khi Gemini API gặp sự cố.

---

## 1. Cấu Trúc Tổ Chức Dự Án (Clean Architecture / MVC)

```text
project/
├── app/                          # Backend FastAPI (Python 3.11+)
│   ├── core/                     # Cấu hình hệ thống, biến môi trường, bảo mật JWT
│   │   ├── config.py
│   │   └── security.py
│   ├── db/                       # Kết nối CSDL và kịch bản di chuyển Alembic
│   │   ├── session.py
│   │   └── base.py
│   ├── models/                   # SQLAlchemy ORM Entities (Khớp 100% Skill 4)
│   │   ├── nguoi_dung.py
│   │   ├── danh_muc.py
│   │   ├── giao_dich.py
│   │   ├── ngan_sach.py
│   │   ├── muc_tieu_tiet_kiem.py
│   │   ├── bao_cao_ai.py
│   │   └── dat_lai_mat_khau.py
│   ├── schemas/                  # Pydantic Schemas (Request/Response DTOs)
│   │   ├── auth_schema.py
│   │   ├── giao_dich_schema.py
│   │   └── ai_schema.py
│   ├── services/                 # Lớp nghiệp vụ chuyên sâu (Business Services)
│   │   ├── auth_service.py
│   │   ├── ngan_sach_service.py
│   │   ├── privacy_service.py    # Tầng lọc PII Sanitization
│   │   └── ai_service.py         # Tích hợp Google Gemini Flash SDK
│   ├── controllers/              # FastAPI Routers (RESTful API Endpoints)
│   │   ├── auth_controller.py
│   │   ├── giao_dich_controller.py
│   │   ├── ngan_sach_controller.py
│   │   ├── thong_ke_controller.py
│   │   └── ai_controller.py
│   └── main.py                   # Điểm khởi chạy ứng dụng
├── tests/                        # Bộ kiểm thử tự động Pytest (Khớp Skill 7)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 2. Bảng Đặc Tả Hợp Đồng RESTful API

| Method & Endpoint | Use Case | Mô tả nghiệp vụ | Request Body (Schema) | Mã HTTP Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/dang-ky` | UC001 | Đăng ký tài khoản người dùng mới | `{"email", "mat_khau", "ho_ten"}` | 201 Created, 400 Bad Request |
| `POST /api/v1/auth/dang-nhap` | UC001 | Đăng nhập và nhận cặp JWT Token | `{"email", "mat_khau"}` | 200 OK, 401 Unauthorized |
| `POST /api/v1/auth/quen-mat-khau` | UC001 | Yêu cầu sinh mã OTP khôi phục mật khẩu | `{"email"}` | 200 OK, 404 Not Found |
| `POST /api/v1/auth/dat-lai-mat-khau` | UC001 | Xác thực OTP và đổi mật khẩu mới | `{"email", "otp", "mat_khau_moi"}` | 200 OK, 400 Bad Request |
| `GET /api/v1/giao-dich` | UC004, UC005 | Lấy danh sách giao dịch kèm lọc | Query: `?thang=&nam=&danh_muc=` | 200 OK, 401 Unauthorized |
| `POST /api/v1/giao-dich` | UC004, UC007 | Ghi nhận giao dịch & kích hoạt cảnh báo | `{"so_tien", "ma_dm", "ngay_gd", "ghi_chu"}` | 201 Created (kèm cả warning), 400 |
| `PUT /api/v1/giao-dich/{ma_gd}` | UC004 | Cập nhật thông tin giao dịch hiện có | `{"so_tien", "ma_dm", "ngay_gd", "ghi_chu"}` | 200 OK, 403 Forbidden, 404 |
| `DELETE /api/v1/giao-dich/{ma_gd}` | UC004 | Xóa giao dịch (chỉ giao dịch của mình) | Không có | 200 OK, 403 Forbidden, 404 |
| `POST /api/v1/ngan-sach` | UC006 | Thiết lập hạn mức ngân sách tháng | `{"ma_dm", "thang_nam", "han_muc"}` | 201 Created, 400 Bad Request |
| `GET /api/v1/thong-ke/tong-quan` | UC009 | Số liệu Dashboard, Pie chart, Bar chart | Query: `?thang=&nam=` | 200 OK, 401 Unauthorized |
| `GET /api/v1/ai/bao-cao-thang` | UC010 | Lấy báo cáo phân tích AI tháng (có Cache) | Query: `?thang=&nam=` | 200 OK, 503 Service Unavailable |
| `GET /api/v1/ai/goi-y-ngan-sach` | UC011 | Gợi ý hạn mức phân bổ ngân sách AI | Query: `?thang_tiep_theo=` | 200 OK, 503 Service Unavailable |
| `POST /api/v1/ai/hoi-dap` | UC012 | Hỏi đáp hội thoại tự nhiên với Chatbot | `{"cau_hoi": "Thang nay tieu gi nhieu?"}` | 200 OK, 400, 503 Unavailable |

---

## 3. Thiết Kế Tích Hợp Google Gemini Flash & Bảo Mật PII

### Thuật toán Ẩn danh hóa dữ liệu (Privacy Shield):

```python
def an_danh_hoa_du_lieu(ma_nd: str, thang: int, nam: int, db) -> dict:
    """
    PII Sanitization Layer - Loại bỏ hoàn toàn thông tin định danh cá nhân
    trước khi gửi sang Google Gemini API.
    """
    # Bước 1: Truy vấn dữ liệu chi tiêu trong tháng từ CSDL
    giao_dich_list = db.query(GiaoDich).filter(
        GiaoDich.ma_nd == ma_nd,
        extract('month', GiaoDich.ngay_gd) == thang,
        extract('year', GiaoDich.ngay_gd) == nam
    ).all()
    
    # Bước 2: Gom nhóm (Aggregate) theo từng danh mục
    co_cau = {}
    for gd in giao_dich_list:
        ten_dm = gd.danh_muc.ten_dm  # Chỉ giữ tên danh mục, không lấy ID
        co_cau[ten_dm] = co_cau.get(ten_dm, 0) + float(gd.so_tien)
    
    tong_chi = sum(co_cau.values())
    
    # Bước 3: LOẠI BỎ TRIỆT ĐỂ: ma_nd, ho_ten, email, chuỗi ghi chú tự do
    # Chỉ giữ tên danh mục và tổng tiền
    ket_qua = {
        "tong_thu": ...,  # Tổng thu nhập tháng
        "tong_chi": tong_chi,
        "co_cau_chi_tieu": [
            {"danh_muc": ten, "so_tien": int(so), "ty_le": round(so/tong_chi*100, 1)}
            for ten, so in co_cau.items()
        ],
        "ngan_sach_vuot": [...]  # Danh sách danh mục vượt ngân sách (tên, không ID)
    }
    
    return ket_qua
```

### Cấu trúc System Prompt & User Prompt chuẩn hóa:

```python
SYSTEM_PROMPT = """
Bạn là Trợ lý Phân tích Tài chính Cá nhân thông minh, bảo mật và chính xác.
Quy tắc phản hồi bắt buộc:
1. Chỉ dựa trên dữ liệu số liệu JSON được cung cấp trong phần USER; tuyệt đối không bịa đặt hoặc suy đoán số liệu ngoài ngữ cảnh.
2. Trả lời bằng tiếng Việt thân thiện, súc tích, mang tính xây dựng.
3. Không trả lời các câu hỏi ngoài phạm vi tài chính cá nhân (từ chối lịch sự nếu người dùng hỏi về đầu tư mạo hiểm, chính trị, code...).
4. Định dạng đầu ra bắt buộc:
   - Một đoạn tóm tắt xu hướng chi tiêu tối đa 4 câu.
   - Đúng 3 lời khuyên hành động cụ thể để tiết kiệm tiền, mỗi lời khuyên không quá 20 từ.
"""

USER_PROMPT_TEMPLATE = """
Dữ liệu chi tiêu tháng {thang}/{nam} (Đã ẩn danh hóa):
{
  "tong_thu": 15000000,
  "tong_chi": 6800000,
  "co_cau_chi_tieu": [
    {"danh_muc": "An uong", "so_tien": 3200000, "ty_le": 47.0},
    {"danh_muc": "Tien nha", "so_tien": 2000000, "ty_le": 29.4},
    {"danh_muc": "Giai tri", "so_tien": 1600000, "ty_le": 23.6}
  ],
  "ngan_sach_vuot": ["An uong"]
}
"""
```

### Cơ chế Xử lý sự cố & Giới hạn chi phí (Resilience & Cost Optimization):

```python
import asyncio
from google.generativeai import GenerativeModel

async def goi_gemini_flash(system_prompt: str, context_json: dict) -> str:
    """
    Gọi Gemini Flash với Timeout 5s và Fallback tự động.
    Rate Limiting: Tối đa 10 câu hỏi chatbot / phút / người dùng.
    """
    try:
        # Timeout cứng 5.0 giây theo NFR-03
        result = await asyncio.wait_for(
            _call_gemini_api(system_prompt, context_json),
            timeout=5.0
        )
        return result
    except asyncio.TimeoutError:
        # Fallback: Trả về thống kê cơ bản từ Rule-based Engine
        return _rule_based_fallback(context_json)
    except Exception as e:
        if "429" in str(e) or "503" in str(e):
            return _rule_based_fallback(context_json)
        raise

def _rule_based_fallback(context_json: dict) -> str:
    """Fallback thân thiện: Thống kê cơ bản từ dữ liệu tĩnh khi AI không khả dụng."""
    return (
        "Trợ lý AI đang bận, dưới đây là thống kê tự động từ hệ thống.\n"
        f"Tổng chi tháng này: {context_json['tong_chi']:,.0f} VND. "
        "Vui lòng thử lại sau vài phút để nhận phân tích chi tiết."
    )
```

### Rate Limiting với SlowAPI:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v1/ai/hoi-dap")
@limiter.limit("10/minute")  # Tối đa 10 câu hỏi/phút/người dùng
async def hoi_dap_chatbot(request: Request, req: ChatRequest, ...):
    ...
```
