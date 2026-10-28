---
name: dynamic-activity-sequence-bce
description: Mô hình hóa Động - Activity Diagram có Swimlanes và Sequence Diagram chuẩn phân tích BCE (Boundary-Control-Entity) bằng PlantUML cho MoneyMind. Bao gồm luồng Ghi nhận giao dịch kết hợp Cảnh báo ngân sách (UC004+UC007) và luồng Báo cáo AI tháng có Cache và Fallback (UC010).
---

# Kỹ Năng: Mô Hình Hóa Động - Activity Swimlanes & Sequence BCE

> **Chuyên môn**: Software Interaction Designer & UML Dynamic Modeler
> **Nhiệm vụ**: Xây dựng Sơ đồ Hoạt động (Activity Diagram) có phân làn và Sơ đồ Trình tự (Sequence Diagram) theo chuẩn phân tích BCE cho các luồng nghiệp vụ trọng yếu.

---

## Bộ Nguyên Tắc Bắt Buộc

1. **Sơ đồ Hoạt động BẮT BUỘC dùng Swimlanes (Phân làn)** tối thiểu 3 làn: `[Người dùng]` | `[Giao diện & Controller]` | `[Dịch vụ & CSDL / AI]`.
2. **Sơ đồ Trình tự BẮT BUỘC phân loại đối tượng theo chuẩn BCE**:
   - **Boundary**: Form / Màn hình / Giao diện người dùng.
   - **Control**: Controller điều phối / Service xử lý logic.
   - **Entity**: Bảng dữ liệu / Mô hình CSDL lưu trữ.
   - **External System**: Google Gemini API (khi có tác vụ AI).
3. **Logic xác thực và xử lý CSDL**: Control phải gọi truy vấn Entity trước khi so khớp thông tin. Phải có khối `alt / else` biểu diễn đầy đủ trường hợp Hợp lệ và Bất hợp lệ (Trùng lặp, Sai mật khẩu, Vượt ngân sách, Timeout AI).

---

## 1. Sơ Đồ Hoạt Động Có Phân Làn (Activity Swimlanes)

### Luồng Ghi nhận giao dịch & Kích hoạt cảnh báo ngân sách (UC004 + UC007)

```plantuml
@startuml
skinparam shadowing false
skinparam monochrome false

|Nguoi dung|
start
:Bam chon 'Them giao dich';
:Nhap so tien, chon danh muc va ngay;
:Bam nut 'Luu';

|Giao dien & Controller|
:Tiep nhan yeu cau ghi nhan;
if (Du lieu dau vao hop le?) then (Khong)
    :Hien thi thong bao loi kiem tra;
    |Nguoi dung|
    :Sua lai thong tin;
    detach
else (Hop le)
    |Dich vu & CSDL|
    :Luu ban ghi vao bang giao_dich;
    :Truy van han muc ngan sach thang cua danh muc;
    if (Da thiet lap ngan sach?) then (Co)
        :Tinh tong chi tieu luy ke thang;
        if (Tong chi >= 100% han muc?) then (Do)
            :Tao canh bao Do (Vuot ngan sach);
        else if (Tong chi >= 80% han muc?) then (Vang)
            :Tao canh bao VANG (Nguy co vuot);
        else (An toan)
            :Khong tao canh bao;
        endif
    else (Chua co)
        :Bo qua buoc kiem tra ngan sach;
    endif
    
    |Giao dien & Controller|
    :Cap nhat so du va bieu do Dashboard;
    :Tra ve thong bao luu thanh cong kem canh bao (neu co);
    
    |Nguoi dung|
    :Nhan phan hoi truc quan tren man hinh;
    stop
endif
@enduml
```

---

## 2. Bộ Sơ Đồ Trình Tự Chuẩn Phân Tích BCE (PlantUML)

### UC001: Biểu đồ trình tự Đăng nhập tài khoản

```plantuml
@startuml
skinparam shadowing false
skinparam sequenceMessageAlign center

actor "Nguoi dung" as User
boundary "FormDangNhap" as UI <<Boundary>>
control "DKDangNhap" as Ctrl <<Control>>
entity "nguoi_dung" as DB <<Entity>>

User -> UI : 1: Nhap email & mat khau, bam 'Dang nhap'
activate UI

UI -> Ctrl : 2: guiThongTinDangNhap(email, password)
activate Ctrl

Ctrl -> DB : 3: timNguoiDungTheoEmail(email)
activate DB
DB --> Ctrl : 4: traVeThongTin(nguoi_dung / null)
deactivate DB

alt Nguoi dung khong ton tai
    Ctrl --> UI : 5a: baoLoi("Tai khoan khong ton tai")
    UI --> User : 6a: HienThiLoi("Email chua duoc dang ky")
else Nguoi dung ton tai
    Ctrl -> Ctrl : 5b: kiemTraMatKhau(password, mat_khau_hash)
    alt Mat khau khong khop
        Ctrl --> UI : 6b: baoLoi("Mat khau khong chinh xac")
        UI --> User : 7b: HienThiLoi("Sai mat khau")
    else Mat khau hop le
        Ctrl -> Ctrl : 6c: taoPhienLamViec(JWT_Token)
        Ctrl --> UI : 7c: traVeThanhCong(token, thong_tin_user)
        UI --> User : 8c: chuyenHuongDashboard()
    end
end

deactivate Ctrl
deactivate UI
@enduml
```

---

### UC010: Biểu đồ trình tự Xem báo cáo AI tháng (kèm Caching & Gemini API)

```plantuml
@startuml
skinparam shadowing false
skinparam sequenceMessageAlign center

actor "Nguoi dung" as User
boundary "MhBaoCaoAI" as UI <<Boundary>>
control "DkPhanTichAI" as Ctrl <<Control>>
entity "bao_cao_ai" as CacheDB <<Entity>>
entity "giao_dich" as TxnDB <<Entity>>
boundary "GoogleGeminiAPI" as AI <<External System>>

User -> UI : 1: Yeu cau xem bao cao thang(thang, nam)
activate UI

UI -> Ctrl : 2: layBaoCaoAI(ma_nd, thang, nam)
activate Ctrl

Ctrl -> CacheDB : 3: kiemTraBaoCaoDaCo(ma_nd, thang, nam)
activate CacheDB
CacheDB --> Ctrl : 4: ketQuaCache(ban_ghi_bao_cao / null)
deactivate CacheDB

alt Da co trong Cache (Cache Hit)
    Ctrl --> UI : 5a: traVeBaoCao(noi_dung_tom_tat, goi_y)
    UI --> User : 6a: hienThiBaoCaoNhanh(< 500ms)
else Chua co trong Cache (Cache Miss)
    Ctrl -> TxnDB : 5b: laySoLieuThuChiThang(ma_nd, thang, nam)
    activate TxnDB
    TxnDB --> Ctrl : 6b: danhSachSoLieuTongHop()
    deactivate TxnDB
    
    Ctrl -> Ctrl : 7b: anDanhHoaDuLieu(loai bo PII, dong goi JSON)
    
    Ctrl -> AI : 8b: goiGeminiFlash(system_prompt, json_data)
    activate AI
    
    alt Goi AI thanh cong trong 5s
        AI --> Ctrl : 9b: traVeKetQuaPhanTich(tom_tat, 3_khuyen_nghi)
        Ctrl -> CacheDB : 10b: luuBaoCaoCache(ma_nd, thang_nam, ket_qua)
        Ctrl --> UI : 11b: traVeBaoCaoMoi()
        UI --> User : 12b: hienThiBaoCaoKiemDuyet()
    else Loi ket noi / Qua 5 giay (Fallback)
        AI --> Ctrl : 9c: Timeout / Error
        Ctrl --> UI : 10c: traVeDuLieuMacDinh(Fallback Thong ke co ban)
        UI --> User : 11c: thongBao("AI ban, hien thi tom tat so lieu tu dong")
    end
    deactivate AI
end

deactivate Ctrl
deactivate UI
@enduml
```

---

### UC004: Biểu đồ trình tự Ghi nhận giao dịch & Cảnh báo ngân sách

```plantuml
@startuml
skinparam shadowing false
skinparam sequenceMessageAlign center

actor "Nguoi dung" as User
boundary "FormGiaoDich" as UI <<Boundary>>
control "GiaoDichController" as GDCtrl <<Control>>
control "NganSachService" as NSvc <<Control>>
entity "giao_dich" as GDDB <<Entity>>
entity "ngan_sach" as NSDB <<Entity>>

User -> UI : 1: Nhap so tien, chon danh muc, bam Luu
activate UI

UI -> GDCtrl : 2: taoGiaoDich(so_tien, ma_dm, ngay_gd, ghi_chu)
activate GDCtrl

GDCtrl -> GDCtrl : 3: validateDuLieu(so_tien > 0, ngay hop le)

alt Du lieu khong hop le
    GDCtrl --> UI : 4a: baoLoi(422 Unprocessable Entity)
    UI --> User : 5a: hienThiLoi(tren truong bi sai)
else Du lieu hop le
    GDCtrl -> GDDB : 4b: INSERT INTO giao_dich(...)
    activate GDDB
    GDDB --> GDCtrl : 5b: ma_gd moi
    deactivate GDDB
    
    GDCtrl -> NSvc : 6b: kiemTraCanhBao(ma_nd, ma_dm, so_tien)
    activate NSvc
    
    NSvc -> NSDB : 7b: layHanMucNganSach(ma_nd, ma_dm, thang_nam)
    activate NSDB
    NSDB --> NSvc : 8b: han_muc / null
    deactivate NSDB
    
    alt Chua co ngan sach
        NSvc --> GDCtrl : 9a: khongCoCanhBao()
    else Da co ngan sach
        NSvc -> NSDB : 9b: tinhTongChiThang(ma_nd, ma_dm, thang_nam)
        activate NSDB
        NSDB --> NSvc : 10b: tong_chi_hien_tai
        deactivate NSDB
        
        NSvc -> NSDB : 11b: capNhatSoTienDaChi(ma_ns, so_tien_moi)
        
        alt Tong chi >= 100% han muc
            NSvc --> GDCtrl : 12a: alert(OVER_BUDGET_100)
        else Tong chi >= 80% han muc
            NSvc --> GDCtrl : 12b: alert(WARNING_80_PERCENT)
        else An toan
            NSvc --> GDCtrl : 12c: khongCoCanhBao()
        end
    end
    deactivate NSvc
    
    GDCtrl --> UI : 13: HTTP 201 Created {giao_dich, canh_bao}
    UI --> User : 14: hienThiThanhCong_va_CanhBao()
end

deactivate GDCtrl
deactivate UI
@enduml
```
