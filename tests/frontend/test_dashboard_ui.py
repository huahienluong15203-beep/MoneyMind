"""
Kiểm thử tự động giao diện (Frontend E2E Test) - Phân hệ Dashboard & Báo cáo Thống kê
"""
import pytest

try:
    from playwright.sync_api import Page, expect
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Cần cài đặt playwright và pytest-playwright để chạy E2E UI")

def test_hien_thi_khung_dien_thoai_chuan(page: 'Page', base_url: str):
    """Kiểm tra mô phỏng khung điện thoại di động trên PC"""
    page.goto(base_url)
    expect(page.locator("#mobile-frame")).to_be_visible()

def test_cac_nut_chuc_nang_noi(page: 'Page', base_url: str):
    """Kiểm tra cụm nút nổi AI và Thêm nhanh"""
    page.goto(base_url)
    # Kiểm tra sự hiện diện của container nút nổi
    assert page.locator("#floating-bottom-controls").count() >= 1
