# 🧠 Minh Chứng Sử Dụng AI Trong SDLC, Kiểm Chứng Sửa Lỗi & Hướng Dẫn Vấn Đáp

> **Mã tiêu chuẩn đánh giá**: Tiêu chí 5 — Tư duy phản biện và sử dụng AI có trách nhiệm (CLO1, CLO5 — **2.0 Điểm**)  
> **Dự án**: MoneyMind — Quản Lý Tài Chính Cá Nhân Thông Minh Tích Hợp AI  
> **Nội dung bao gồm**:  
> - 5.1 Minh chứng ứng dụng AI trong toàn bộ quy trình SDLC  
> - 5.2 Quá trình kiểm chứng và khắc phục các sai sót/ảo giác (Hallucination) của AI  
> - 5.3 Ngân hàng câu hỏi và kịch bản vấn đáp độc lập từng thành viên  
> - 5.4 Các cải tiến và đóng góp kỹ thuật độc lập của nhóm  

---

## 1. Minh Chứng Ứng Dụng AI Trong Toàn Bộ Chu Trình SDLC (Tiêu chí 5.1)

Trong suốt quá trình xây dựng dự án MoneyMind, nhóm không sử dụng AI như một công cụ sinh code thụ động, mà áp dụng phương pháp **Context Engineering** kết hợp **Prompt Engineering 3 phần** để điều khiển AI hỗ trợ có định hướng trong từng giai đoạn:

| Giai đoạn SDLC | Vai trò của AI Agent | Prompt mẫu đưa vào (Input Context) | Sản phẩm do AI hỗ trợ sinh ra | Phản biện & Đánh giá của nhóm |
| :--- | :--- | :--- | :--- | :--- |
| **1. Khảo sát & Phân tích (BA)** | Lead BA Agent | *"Phân tích nghiệp vụ quản lý tài chính 6 hũ. Hãy đặc tả chi tiết 6 quy tắc nghiệp vụ BR-01..BR-06 và 11 yêu cầu chức năng FR01..FR11 theo chuẩn IEEE 830."* | Tài liệu SRS, bảng quy tắc nghiệp vụ `BR-01` đến `BR-06`. | Nhóm rà soát, bổ sung ràng buộc số tiền tối thiểu 1.000 đ và cơ chế hoàn tiền khi xóa hũ. |
| **2. Thiết kế Kiến trúc & CSDL** | System Architect Agent | *"Thiết kế CSDL chuẩn hóa 3NF gồm 12 bảng cho ứng dụng tài chính. Xuất mã PlantUML Crow's Foot ERD và Class Diagram phân tầng Clean Architecture."* | Mã nguồn PlantUML ERD, mô hình ORM SQLAlchemy 12 bảng. | Nhóm tối ưu lại kiểu dữ liệu số tiền sang `Float/Numeric`, bổ sung khóa ngoại `ondelete='CASCADE'`. |
| **3. Lập trình Backend (Dev)** | Backend Dev Agent | *"Xây dựng FastAPI router cho mục tiêu tiết kiệm. Cần có endpoint nộp tiền, tự động cập nhật phần trăm và gửi thông báo chúc mừng khi đạt 90%/100%."* | Controller `muc_tieu_controller.py`, Service `ngan_sach_service.py`. | Nhóm phát hiện AI quên trừ tiền ví chính khi nộp hũ $\rightarrow$ Viết thêm logic kiểm tra số dư khả dụng. |
| **4. Tích hợp Trí tuệ Nhân tạo** | AI Integration Specialist | *"Tích hợp Gemini 3.8 Flash SDK với cơ chế Cascade Fallback, HTTP Keep-Alive Pool và PII Sanitization loại bỏ 100% thông tin cá nhân."* | Module `ai_service.py` (3900 dòng lệnh) và `privacy_service.py`. | Nhóm bổ sung bộ phân tích tiếng Việt cục bộ (Local Regex) để các lệnh CRUD phản hồi tức thì < 50ms. |
| **5. Kiểm thử & Bảo mật (QA)** | Security Testing Agent | *"Sinh bộ test tự động Pytest kiểm thử SQL Injection (7 payload OWASP), XSS (6 payload), Boundary values và kiểm tra 6 Business Rules."* | 96 automated test cases trong thư mục `tests/`. | Nhóm thiết kế fixture `db_session` cô lập CSDL in-memory để test chạy độc lập và an toàn tuyệt đối. |
| **6. Đóng gói & Triển khai** | DevOps Agent | *"Viết Dockerfile, docker-compose.yml và cấu hình Progressive Web App (PWA) có Service Worker cache offline."* | `Dockerfile`, `manifest.json`, `sw.js`, `ci.yml`. | Nhóm đóng gói thêm dự án Android Native Studio Wrapper với chế độ toàn màn hình không thanh URL. |

> Toàn bộ 13 file Prompt gốc dùng để sinh các thành phần trên được lưu trữ minh bạch tại: [`.agents/skills/PROMPTS.md`](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/.agents/skills/PROMPTS.md).

---

## 2. Quá Trình Kiểm Chứng Và Khắc Phục Sai Sót Của AI (Tiêu chí 5.2)

Trong quá trình phát triển, nhóm đã phát hiện và trực tiếp sửa chữa **4 ca sai sót / ảo giác (Hallucination)** nghiêm trọng do AI tạo ra:

### Ca 1: AI tự ý ghi nhận giao dịch khi người dùng chỉ hỏi ý kiến tham khảo
- **Hiện tượng lỗi**: Khi người dùng nhắn tin hỏi: *"Tôi có nên mua chiếc điện thoại iPhone 15 giá 20 triệu không?"*, AI lúc đầu tự động phân tích câu có `20 triệu` và `mua điện thoại`, sau đó tự ý gọi hàm ghi nhận một khoản chi tiêu 20.000.000 đ vào danh mục Mua sắm!
- **Hậu quả**: Làm sai lệch toàn bộ ngân sách và số dư thực tế của người dùng.
- **Biện pháp kiểm chứng & khắc phục của nhóm**:
  1. Nhóm bổ sung hàm `_kiem_tra_noi_dung_nhay_cam_va_tieu_cuc()` và `_xu_ly_tu_van_kha_nang_chi_tieu()`.
  2. Phân tích intent: Nếu câu nói mang tính chất hỏi ý kiến (*"có nên"*, *"được không"*, *"tư vấn giùm"*), AI chỉ phân tích tỷ lệ số dư khả dụng so với giá món đồ và đưa ra lời khuyên khách quan, tuyệt đối **không tự ý lưu giao dịch**.
  3. Viết test case tự động kiểm chứng: `test_ai_hoi_y_kien_chi_tieu_khong_tu_y_ghi_giao_dich` trong [`tests/test_ai_natural_transactions.py`](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/tests/test_ai_natural_transactions.py).

### Ca 2: Rò rỉ thông tin cá nhân (PII Data Leakage) sang máy chủ bên thứ ba
- **Hiện tượng lỗi**: Phiên bản ban đầu do AI gợi ý đã gửi nguyên vẹn bản ghi từ CSDL sang Google Gemini API, bao gồm cả `email`, `ho_ten`, `ngay_sinh` và `ghi_chu_tu_do`.
- **Hậu quả**: Vi phạm nghiêm trọng đạo luật bảo vệ quyền riêng tư dữ liệu và tiêu chuẩn ISO/IEC 27001.
- **Biện pháp khắc phục của nhóm**:
  1. Tự thiết kế một lớp dịch vụ độc lập: `PrivacyService` ([`app/services/privacy_service.py`](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/services/privacy_service.py)).
  2. Áp dụng quy tắc `BR-03`: Dữ liệu gửi sang Gemini được tổng hợp thành JSON số liệu thuần túy (tổng thu, tổng chi, tỷ lệ chi theo nhóm hũ), loại bỏ hoàn toàn các trường định danh cá nhân.

### Ca 3: Lỗi xóa hũ tiết kiệm làm "bốc hơi" tiền của người dùng
- **Hiện tượng lỗi**: Khi người dùng yêu cầu xóa một mục tiêu tiết kiệm (ví dụ: hũ *"Mua xe máy"* đã tích lũy được 10.000.000 đ), code ban đầu của AI chỉ thực hiện `db.delete(goal)` $\rightarrow$ Toàn bộ 10 triệu đồng tích lũy biến mất khỏi hệ thống mà không được hoàn lại ví chính!
- **Biện pháp khắc phục của nhóm**:
  1. Nhóm cải tiến logic: Trước khi xóa bản ghi `MucTieuTietKiem`, hệ thống đọc `so_tien_hien_tai`, nếu > 0 thì tự động tính toán hoàn trả về số dư ví chính khả dụng.
  2. Tự động sinh một thông báo hệ thống minh bạch: *"💰 Hoàn tiền hũ tiết kiệm về ví chính: Đã hoàn trả 10,000,000 đ về ví chính để bạn sử dụng cho mục đích khác."*
  3. Đổi ghi chú các giao dịch cũ liên quan thành `(đã xoá)` để không bị tính trùng lặp chi tiêu.

### Ca 4: Trích xuất sai số tiền và lẫn lộn danh mục khi mô tả có từ thừa
- **Hiện tượng lỗi**: Với câu lệnh: *"Vừa đưa 50k cho mẹ đi chợ mua đồ ăn trưa"*, AI trích xuất sai tên món là *"mẹ đi chợ mua đồ ăn trưa"* hoặc không nhận diện được `50k = 50.000 đ`.
- **Biện pháp khắc phục của nhóm**:
  1. Nhóm tự lập trình thuật toán xử lý ngôn ngữ tự nhiên: hàm `_lam_sach_mo_ta_giao_dich()` và `_parse_vietnamese_amount()` loại bỏ các đại từ xưng hô thừa, chuẩn hóa các tiếp vĩ ngữ tiền tệ tiếng Việt (`k`, `nghìn`, `ngàn`, `cành`, `lít`, `củ`, `tr`, `triệu`).
  2. Viết bộ 20+ test cases kiểm thử chuyên sâu trong [`tests/test_ai_natural_transactions.py`](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/tests/test_ai_natural_transactions.py).

---

## 3. Ngân Hàng Câu Hỏi & Kịch Bản Vấn Đáp Độc Lập Từng Thành Viên (Tiêu chí 5.3)

Để chuẩn bị chu đáo cho buổi bảo vệ đồ án, dưới đây là bộ câu hỏi trọng tâm phân chia theo từng mảng chuyên môn:

### Mảng 1: Phân Tích Nghiệp Vụ & Cơ Sở Dữ Liệu
- **Câu hỏi 1**: *Tại sao nhóm lại áp dụng quy tắc 6 hũ tài chính? Hệ thống xử lý thế nào khi người dùng chi vượt ngân sách một hũ?*
  - **Trả lời**: Quy tắc 6 hũ giúp chia nhỏ dòng tiền theo tỷ lệ mục đích rõ ràng (Nhu cầu thiết yếu 55%, Tiết kiệm 10%, Giáo dục 10%, Hưởng thụ 10%, Đầu tư 10%, Cho đi 5%). Khi người dùng chi tiêu vượt hạn mức (>100%), hệ thống kích hoạt rào chắn `BR-05`: bắn cảnh báo màu đỏ tức thời và chặn ghi nhận hoặc yêu cầu nâng thêm hạn mức để bảo toàn kỷ luật tài chính.
- **Câu hỏi 2**: *Mô hình CSDL của nhóm đạt chuẩn mấy? Các bảng quan hệ với nhau như thế nào?*
  - **Trả lời**: CSDL đạt chuẩn hóa 3NF (Third Normal Form) gồm 12 bảng không có phụ thuộc bắc cầu. Bảng trung tâm là `nguoi_dung` kết nối 1-N với `danh_muc`, `giao_dich`, `ngan_sach`, `muc_tieu_tiet_kiem`, `bao_cao_ai`. Mọi giao dịch chi tiêu đều liên kết chặt chẽ với danh mục tương ứng theo quy tắc toàn vẹn `BR-01`.

### Mảng 2: Kiến Trúc Phần Mềm & An Toàn Bảo Mật
- **Câu hỏi 3**: *Hệ thống ngăn chặn tấn công SQL Injection và XSS như thế nào?*
  - **Trả lời**: 100% truy vấn dữ liệu sử dụng SQLAlchemy ORM Parameterized Queries, triệt tiêu nguy cơ SQL Injection (đã được kiểm chứng qua 7 payload OWASP trong `test_security_agent.py`). Dữ liệu xuất ra màn hình được escape HTML tự động qua Vanilla JS `textContent` hoặc DOM element creation, không dùng `innerHTML` trên dữ liệu người dùng nhập để chống XSS.
- **Câu hỏi 4**: *Cơ chế quản lý phiên đăng nhập đơn thiết bị (Single Session) hoạt động ra sao?*
  - **Trả lời**: Khi người dùng đăng nhập thành công, server sinh ra một `session_id` ngẫu nhiên (UUIDv4) lưu vào bảng `nguoi_dung` và nhúng vào JWT payload. Mỗi request gửi lên, dependency `get_current_user` đối chiếu `session_id` trong token với `session_id` hiện hành trong CSDL. Nếu tài khoản đăng nhập trên máy khác, `session_id` bị cập nhật mới $\rightarrow$ máy cũ bị kick out ngay lập tức với mã HTTP 401.

### Mảng 3: Trí Tuệ Nhân Tạo & Kiểm Thử
- **Câu hỏi 5**: *Nhóm giải quyết bài toán độ trễ (latency) và chi phí khi gọi Google Gemini API như thế nào?*
  - **Trả lời**: Nhóm áp dụng chiến lược đa tầng:
    1. *Cache CSDL (BR-04)*: Báo cáo tháng được lưu vào bảng `bao_cao_ai`, xem lại trả về ngay < 50ms, không gọi lại LLM.
    2. *HTTP Keep-Alive Connection Pooling*: Tái sử dụng kết nối TLS, giảm thời gian phản hồi còn ~1.2s.
    3. *Cascade Multi-Model Fallback*: Dự phòng giữa Gemini 3.8 Flash và 3.5 Flash-Lite, nếu timeout > 5s tự kích hoạt Circuit Breaker trả về HTTP 503 hoặc fallback tính toán cục bộ.
- **Câu hỏi 6**: *Quy trình kiểm thử của nhóm có điểm gì đặc biệt?*
  - **Trả lời**: Toàn bộ 96 test cases backend chạy trên CSDL SQLite In-Memory với `StaticPool`. Dữ liệu được cô lập tuyệt đối và tự động rollback sau từng test, đảm bảo test suite chạy cực nhanh (< 45 giây) và không làm ô nhiễm dữ liệu thật.

---

## 4. Các Cải Tiến & Đóng Góp Kỹ Thuật Độc Lập Của Nhóm (Tiêu chí 5.4)

Những đóng góp kỹ thuật sáng tạo do nhóm tự nghiên cứu, thiết kế và phát triển độc lập (vượt ra ngoài các gợi ý ban đầu của AI):

1. **Cơ chế Tự Động Kết Chuyển Ngân Sách Sang Tháng Mới (Auto Carryover)**:
   - Tự động nhận diện khi bước sang tháng mới: Lấy số dư chưa tiêu hết của tháng cũ kết chuyển sang tháng mới, tính toán hạn mức cấp bù theo cơ chế thác nước (Waterfall Allocation) khi có nguồn thu nhập mới.
2. **Cơ chế Hoàn Tiền Hũ Tiết Kiệm Về Ví Chính**:
   - Khi xóa mục tiêu tích lũy, hệ thống không xóa mất tiền mà tự động thu hồi toàn bộ số tiền đang có hoàn trả về ví chính kèm thông báo minh bạch.
3. **Đóng Gói Đa Nền Tảng Kép (Dual-Platform Packaging: PWA + Android APK)**:
   - Xây dựng file Service Worker (`sw.js`) và `manifest.json` cho phép cài đặt Web App trực tiếp trên iOS và Desktop.
   - Viết mã nguồn Native Android Studio Wrapper (`android_app/`) với cấu hình WebView tối ưu phần cứng, hỗ trợ vuốt để tải lại trang (SwipeRefreshLayout) và chạy ở chế độ toàn màn hình như một ứng dụng native thực thụ.
4. **Hệ Thống 7 Giờ Sáng Tự Động Quét Cảnh Báo Định Kỳ**:
   - Lập trình Background Worker chạy nền: Đúng 7h00 sáng mỗi ngày tự động kiểm tra các hũ chi tiêu vượt hạn mức hoặc các mục tiêu tiết kiệm sắp cán đích ($\ge 80\%$) để tạo thông báo khích lệ cho người dùng mà không cần reload giao diện.
