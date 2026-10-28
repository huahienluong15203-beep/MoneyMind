# 🎬 Kịch Bản Demo Trực Tiếp Sản Phẩm MoneyMind (5 Phút Thuyết Phục)

> **Mã tiêu chuẩn đánh giá**: Tiêu chí 4.4 — Demo trực tiếp thành công (CLO5 — 2.0 Điểm)  
> **Thời lượng demo**: 05 phút  
> **Mục tiêu**: Trình diễn mượt mà toàn bộ các tính năng cốt lõi, rào chắn an toàn, tác tử tự hành AI và giao diện đa nền tảng.  

---

## 1. Chuẩn Bị Trước Khi Demo (Checklist 2 Phút)

1. **Khởi chạy ứng dụng**:
   - Mở terminal tại thư mục gốc dự án:
     ```bash
     python main.py
     ```
   - Kiểm tra server khởi động thành công tại: `http://127.0.0.1:8000` (hoặc mở trên thiết bị Android qua APK).
2. **Mở sẵn 2 cửa sổ trình duyệt**:
   - Cửa sổ 1 (Chính): Chrome mở giao diện `http://127.0.0.1:8000`.
   - Cửa sổ 2 (Ẩn danh / Thiết bị khác): Dùng để demo tính năng **Đăng nhập đơn thiết bị (Kickout)**.
3. **Tài khoản test chuẩn bị sẵn**:
   - Email: `demo_moneymind@gmail.com`
   - Mật khẩu: `Demo123456`
   - Số dư ví chính ban đầu: `15.000.000 đ`
   - Hạn mức hũ "Ăn uống": `3.000.000 đ` (đã chi: `2.600.000 đ` ~ 86.7% - Đang ở ngưỡng cảnh báo vàng).

---

## 2. Kịch Bản Chi Tiết Từng Bước (05 Phút)

### Phút 00:00 - 00:45: Giới Thiệu & Xác Thực Đa Tầng Bảo Mật
- **Thao tác**:
  1. Đăng nhập vào hệ thống bằng tài khoản `demo_moneymind@gmail.com`.
  2. Mở cửa sổ ẩn danh thứ hai và đăng nhập cùng tài khoản này.
  3. Quay lại cửa sổ 1 và bấm tải lại hoặc thực hiện 1 thao tác.
- **Lời thoại trình bày**:
  > *"Kính thưa quý thầy cô, MoneyMind được thiết kế theo tiêu chuẩn bảo mật tài chính ngân hàng. Trước tiên, em xin trình diễn cơ chế **Quản lý phiên đơn thiết bị (Single Active Session)**. Khi tài khoản vừa được đăng nhập ở thiết bị thứ hai, phiên làm việc trên thiết bị thứ nhất lập tức bị thu hồi để ngăn chặn nguy cơ chiếm quyền điều khiển tài khoản."*

---

### Phút 00:45 - 01:45: Ghi Nhận Chi Tiêu & Kích Hoạt Cảnh Báo Ngân Sách Tức Thời (Real-Time)
- **Thao tác**:
  1. Mở form thêm giao dịch nhanh (+).
  2. Chọn hũ **"Ăn uống"**, nhập số tiền `500.000 đ`, ghi chú: *"Tiệc liên hoan cuối tuần"*. Bấm Lưu.
  3. Hệ thống ngay lập tức kích hoạt Modal cảnh báo màu đỏ: **"🚨 CẢNH BÁO: CHI TIÊU VƯỢT HẠN MỨC NGÂN SÁCH (103%)"**.
  4. Bấm xem Dashboard: Thẻ ngân sách hũ Ăn uống chuyển sang màu đỏ cảnh báo, biểu đồ Chart.js tự động cập nhật cơ cấu chi tiêu.
- **Lời thoại trình bày**:
  > *"Theo quy tắc nghiệp vụ BR-05, hệ thống không chỉ lưu dữ liệu mà tính toán hạn mức tức thì trong cùng 1 chu kỳ request (< 300ms). Khoản chi 500k đã đẩy tổng chi hũ Ăn uống từ 2.6 triệu lên 3.1 triệu, vượt ngưỡng 100% hạn mức 3 triệu, hệ thống lập tức phát cảnh báo đỏ để người dùng kiểm soát dòng tiền."*

---

### Phút 01:45 - 03:00: Trợ Lý AI Tài Chính Tự Hành Bằng Ngôn Ngữ Tự Nhiên (Autonomous Agent)
- **Thao tác**:
  1. Bấm vào biểu tượng Heo tiết kiệm nổi ở góc dưới để mở **Khung chat Trợ lý AI**.
  2. Gõ lệnh 1: *"Hôm nay tôi vừa đổ xăng 50k"* $\rightarrow$ AI lập tức phản hồi: *"Đã ghi nhận chi tiêu 50.000 đ vào danh mục Đi lại"*, số dư ví tự động giảm 50.000 đ.
  3. Gõ lệnh 2: *"Tạo hũ tiết kiệm mua laptop 15 triệu hạn chót 31/12/2026"* $\rightarrow$ AI tạo ngay hũ mới.
  4. Gõ lệnh 3: *"Nộp 1 triệu vào hũ mua laptop"* $\rightarrow$ AI trích 1.000.000 đ từ ví chính nạp vào hũ, thanh tiến độ hiển thị 6.7%.
  5. Thử nghiệm rào chắn an toàn (Guardrail): Gõ *"Hôm nay thời tiết thế nào?"* hoặc *"Tôi nên mua coin nào?"* $\rightarrow$ AI lịch sự từ chối và giải thích chỉ chuyên trách quản lý chi tiêu cá nhân (TC-09).
- **Lời thoại trình bày**:
  > *"Đây là tính năng Autonomous Agent tự hành bằng tiếng Việt đời thường của MoneyMind. Nhờ kỹ thuật Prompt v3 kết hợp bộ phân tích Intent Router cục bộ, AI trích xuất chính xác số tiền, phân loại hũ và thực thi lệnh trực tiếp trong CSDL với tốc độ dưới 1.5 giây, đồng thời tuân thủ rào chắn an toàn từ chối các câu hỏi ngoài luồng."*

---

### Phút 03:00 - 04:00: Cơ Chế Hoàn Tiền Hũ Tiết Kiệm & Kết Chuyển Ngân Sách
- **Thao tác**:
  1. Chuyển sang Tab **Mục Tiêu Tiết Kiệm**.
  2. Bấm nút Xóa hũ *"Mua laptop"* vừa nạp 1 triệu.
  3. Hộp thoại hiện thông báo xác nhận: Hệ thống tự động hoàn trả `1.000.000 đ` về lại số dư ví chính!
  4. Mở chuông thông báo (🔔): Thấy thông báo hệ thống minh bạch: *"💰 Hoàn tiền hũ tiết kiệm về ví chính thành công"*.
- **Lời thoại trình bày**:
  > *"Một đóng góp kỹ thuật độc lập quan trọng của nhóm là cơ chế **Bảo toàn dòng tiền**. Khi người dùng hủy hoặc xóa một mục tiêu tiết kiệm, số tiền đã tích lũy không hề bị mất đi mà được hoàn lại 100% vào ví chính để người dùng tái phân bổ cho các nhu cầu cấp thiết khác."*

---

### Phút 04:00 - 05:00: Báo Cáo AI Tháng Có Cache & Đóng Gói Đa Nền Tảng (PWA / Android)
- **Thao tác**:
  1. Bấm nút **"Xuất Báo Cáo Tài Chính AI Tháng"**.
  2. Lần 1: AI gọi Gemini Flash phân tích, chấm điểm sức khỏe tài chính (VD: `78/100 điểm`) và xuất 3 lời khuyên hành động.
  3. Bấm tải lại báo cáo Lần 2: Phản hồi xuất hiện tức thì trong **20ms** với huy hiệu **"Đã lưu trong Cache DB"** (Tuân thủ tiêu chuẩn TC-07 & BR-04).
  4. Thu nhỏ trình duyệt về kích thước di động hoặc mở bản demo trên ứng dụng Android APK: Giao diện chuyển đổi Responsive mượt mà, đầy đủ icon, bottom bar điều hướng chuẩn Mobile-First.
- **Lời thoại kết luận**:
  > *"Kính thưa quý thầy cô, hệ thống áp dụng cơ chế Caching DB giúp tiết kiệm 100% chi phí API khi xem lại báo cáo cũ. Đồng thời, toàn bộ sản phẩm đã được đóng gói hoàn chỉnh từ Docker backend, PWA cài đặt trực tiếp và Android APK native. Bộ kiểm thử tự động của nhóm đạt 96/96 test cases passed 100%. Em xin kết thúc phần trình diễn và kính mời quý thầy cô đặt câu hỏi!"*
