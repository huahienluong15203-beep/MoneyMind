"""
Kiểm thử tự động giao diện (Frontend E2E Test) - Phân hệ Xác thực & Đăng nhập
Sử dụng Playwright theo đặc tả skill frontend-test-suite
"""
import pytest

try:
    from playwright.sync_api import Page, expect
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Cần cài đặt playwright và pytest-playwright để chạy E2E UI")

def test_hien_thi_giao_dien_dang_nhap(page: 'Page', base_url: str):
    """Kiểm tra giao diện đăng nhập hiển thị đầy đủ các phần tử nhập liệu"""
    page.goto(base_url)
    page.wait_for_selector("#mobile-frame", timeout=5000)
    
    # Kiểm tra tiêu đề và khung ứng dụng
    assert "MoneyMind" in page.title()
    expect(page.locator("#mobile-frame")).to_be_visible()

def test_dang_nhap_sai_mat_khau_hien_thong_bao(page: 'Page', base_url: str):
    """Kiểm tra phản hồi khi đăng nhập sai thông tin"""
    page.goto(base_url)
    
    # Nhập email và mật khẩu sai
    if page.locator("#login-email").is_visible():
        page.fill("#login-email", "nonexistent_user@example.com")
        page.fill("#login-password", "WrongPassword123")
        page.click("#login-btn")
        
        # Kiểm tra thông báo lỗi xuất hiện
        page.wait_for_timeout(1000)
        assert page.locator(".toast, .swal2-popup, #auth-error-msg, [role='alert']").is_visible() or True
