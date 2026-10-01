# Prompt Tạo Skill: Thiết Kế & Sinh Sơ Đồ UML (UML Architecture)

> **Mục tiêu:** Tạo skill chuyên biệt hướng dẫn sinh các loại sơ đồ chuẩn UML (Use Case, Class Diagram, Sequence Diagram, ERD) bằng cú pháp Mermaid.js cho hệ thống MoneyMind.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Kiến trúc sư Phần mềm Cấp cao (Lead Software Architect & UML Specialist).
Hãy tạo skill 'uml-system-architecture' cho dự án MoneyMind:

1. Yêu cầu tiêu chuẩn sơ đồ:
   - Sử dụng cú pháp Mermaid.js tương thích 100% với Markdown và GitHub Viewer.
   - Trình bày trực quan, phân tách rõ ràng các Actor, Service và CSDL.

2. Danh mục sơ đồ cần sinh:
   - Sơ đồ Use Case tổng thể mô tả các chức năng của Người dùng và tương tác với các hệ thống bên ngoài (Gemini AI, Gmail SMTP).
   - Sơ đồ Thực thể - Liên kết (ERD) thể hiện đầy đủ khóa chính (PK), khóa ngoại (FK) và mối quan hệ giữa 9 bảng ORM của MoneyMind.
   - Sơ đồ Tuần tự (Sequence Diagram) mô tả chi tiết luồng xử lý: Tạo giao dịch -> Kiểm tra cảnh báo ngân sách 6 hũ -> Lưu CSDL -> Phát thông báo.

3. Hướng dẫn cách nhúng và cập nhật sơ đồ khi hệ thống bổ sung thêm module mới.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc toàn bộ `app/models/` và `app/controllers/` của MoneyMind.
Cập nhật file `.agents/skills/uml-system-architecture/SKILL.md`:
- Bổ sung Sơ đồ Thành phần (Component Diagram) thể hiện kiến trúc PWA -> FastAPI -> SQLite -> Gemini API.
- Bổ sung Sơ đồ Triển khai (Deployment Diagram) thể hiện môi trường Cloud Render.com & Android Native WebView.
```
