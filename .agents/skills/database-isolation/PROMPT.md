# 🔒 PROMPT GUIDE — database-isolation

> **Skill:** Cách Ly CSDL Trong Kiểm Thử — SQLite In-Memory & Auto-Rollback  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Senior Backend Engineer chuyên Testing Isolation & SQLAlchemy.
Hãy tạo file SKILL.md cho skill 'database-isolation' trong MoneyMind.

Nội dung bắt buộc:

1. Vấn đề khi thiếu isolation:
   - Test A viết dữ liệu vào DB thật → Test B đọc nhầm dữ liệu của A
   - Test fail → dữ liệu rác còn trong DB production → debug khó
   - Tests phụ thuộc vào nhau → không chạy độc lập được

2. Giải pháp SQLite In-Memory:
   - DATABASE_URL = "sqlite:///:memory:" — tạo mới hoàn toàn trong RAM
   - Mỗi test function có DB riêng → hoàn toàn cô lập
   - Test kết thúc → DB tự hủy → không cần cleanup thủ công

3. Implement conftest.py đầy đủ (code block):
   - engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
   - Fixture db_session scope="function":
     + Base.metadata.create_all(engine) — tạo tables
     + yield session — chạy test
     + session.rollback() — hoàn tác mọi thứ
     + Base.metadata.drop_all(engine) — xóa tables
   - Fixture override_get_db: FastAPI dependency override
   - Fixture test_app: TestClient với override_get_db
   - Fixture user_token: tự động tạo user + login + trả JWT
   - Fixture authenticated_client: httpx.AsyncClient với Bearer header

4. Ví dụ test sử dụng isolation (code block):
   - test_them_giao_dich: POST → assert HTTP 201 → kiểm tra DB in-memory
   - test_xoa_giao_dich: DELETE → assert HTTP 200 → kiểm tra DB không còn record

5. Cách debug khi test fail:
   - pytest --pdb: dừng tại điểm fail, inspect db_session
   - pytest -s: hiển thị print statements

Định dạng: YAML frontmatter + Markdown, có code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE

### 2A. Tạo conftest.py Hoàn Chỉnh Với Tất Cả Fixtures

```
Hãy đọc `.agents/skills/database-isolation/SKILL.md`.
Viết lại file tests/conftest.py hoàn chỉnh với đầy đủ fixtures cho MoneyMind.

Yêu cầu:
- Import đúng: FastAPI app từ main.py, Base từ app/core/database.py
- engine: SQLite in-memory với StaticPool (chia sẻ connection trong cùng session)
  from sqlalchemy.pool import StaticPool
  engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
- SessionLocal = sessionmaker(bind=engine)
- Fixtures:
  @pytest.fixture(scope="function")
  def db_session(): ...  (tạo tables → yield → rollback → drop tables)

  @pytest.fixture(scope="function")
  def test_app(db_session): ...  (override dependency get_db)

  @pytest.fixture(scope="function")
  async def async_client(test_app): ...  (httpx.AsyncClient)

  @pytest.fixture(scope="function")
  async def user_token(async_client): ...  (đăng ký + đăng nhập → return token str)

  @pytest.fixture(scope="function")
  async def authenticated_client(async_client, user_token): ...  (thêm header Bearer)

Dùng: pytest-asyncio, httpx>=0.24.0, SQLAlchemy 2.0
```

### 2B. Thêm Fixture Tạo Dữ Liệu Test Mẫu

```
Hãy đọc `.agents/skills/database-isolation/SKILL.md`.
Thêm các fixtures dữ liệu mẫu vào conftest.py.

Fixtures cần thêm:
@pytest.fixture
async def sample_danh_muc(authenticated_client):
    # Tạo 6 danh mục mẫu (1 per hũ) → return list[dict]

@pytest.fixture
async def sample_ngan_sach(authenticated_client, sample_danh_muc):
    # Tạo ngân sách 5,000,000đ cho danh mục Ăn uống → return dict

@pytest.fixture
async def sample_giao_dich(authenticated_client, sample_danh_muc):
    # Tạo 3 giao dịch chi mẫu → return list[dict]

@pytest.fixture
async def sample_muc_tieu(authenticated_client):
    # Tạo mục tiêu "Du lịch Đà Nẵng" 5,000,000đ → return dict

Các fixture này dùng lại authenticated_client → đảm bảo cô lập per-test.
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — SQLite In-Memory vs SQLite File

```
Sinh Flowchart (Mermaid.js flowchart LR) so sánh 2 chiến lược test DB:

Nhánh trái — SQLite File (KHÔNG nên dùng):
- Test viết vào tai_chinh_test.db
- Test A: INSERT user → Test B: đọc thấy user của A
- Test fail → dữ liệu rác còn lại → phải cleanup thủ công
- Tests phụ thuộc vào thứ tự chạy

Nhánh phải — SQLite In-Memory (KHUYẾN NGHỊ):
- Test tạo sqlite:///:memory: riêng
- Test A: INSERT user → Test B: DB rỗng hoàn toàn
- Test kết thúc → DB tự hủy → không cần cleanup
- Tests độc lập, chạy song song được

Kết quả: In-Memory nhanh hơn 10x, an toàn hơn, không side-effect
```

### 3B. Sequence Diagram — Auto-Rollback Mechanism

```
Sinh Sequence Diagram cho cơ chế auto-rollback của fixture db_session:

1. pytest bắt đầu test: test_them_giao_dich
2. pytest setup fixture db_session (scope=function):
   a. engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
   b. Base.metadata.create_all(engine) — tạo 8 bảng
   c. session = SessionLocal()
   d. yield session (test bắt đầu chạy)
3. Test body:
   a. POST /api/giao-dich/ {so_tien: 500000, loai: chi}
   b. DB in-memory: INSERT INTO giao_dich
   c. assert response.status_code == 201
4. pytest teardown fixture db_session:
   a. session.rollback() — xóa INSERT của test vừa chạy
   b. session.close()
   c. Base.metadata.drop_all(engine) — xóa tất cả tables
   d. engine.dispose() — đóng connection pool
5. DB in-memory bị giải phóng khỏi RAM
6. Test tiếp theo: bắt đầu lại từ bước 2 với DB mới hoàn toàn

Participant: Pytest, FixtureDbSession, SQLiteInMemory, FastAPIApp, TestBody
```
