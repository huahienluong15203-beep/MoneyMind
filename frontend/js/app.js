/**
 * MoneyMind - Main App Controller, Navigation Tabs & Initialization
 */
            function switchSection(sec) {
                currentSection = sec;
                ['quan-ly', 'thong-bao', 'lich-su', 'thong-ke', 'tai-khoan'].forEach(s => {
                    const el = document.getElementById('section-' + s);
                    if(el) el.classList.add('hidden');
                    const btn = document.getElementById('nav-btn-' + s);
                    if(btn) btn.className = "flex-1 flex flex-col items-center gap-1 text-slate-400 hover:text-slate-600 font-semibold text-[11px] transition";
                });
                const activeSec = document.getElementById('section-' + sec);
                if(activeSec) activeSec.classList.remove('hidden');
                const activeBtn = document.getElementById('nav-btn-' + sec);
                if(activeBtn) activeBtn.className = "flex-1 flex flex-col items-center gap-1 text-teal-600 font-bold text-[11px] transition";

                const topNotifBtn = document.getElementById('top-notif-btn');
                if(topNotifBtn) {
                    if(sec === 'thong-bao') {
                        topNotifBtn.className = "w-8 h-8 bg-teal-500 text-white rounded-full flex items-center justify-center text-sm shadow-md transition-all active:scale-95 relative";
                    } else if(sec === 'quan-ly') {
                        topNotifBtn.className = "w-8 h-8 bg-white/95 hover:bg-white text-teal-700 rounded-full flex items-center justify-center text-sm shadow-md border border-white/40 transition-all active:scale-95 relative";
                    } else {
                        topNotifBtn.className = "w-8 h-8 bg-slate-100 hover:bg-teal-50 hover:text-teal-600 text-slate-600 rounded-full flex items-center justify-center text-sm shadow-sm border border-slate-200/90 transition-all active:scale-95 relative";
                    }
                }

                const header = document.getElementById('header-container');
                  const ft = document.getElementById('floating-top-controls');
                  const fb = document.getElementById('floating-bottom-controls');

                  if (token && sec === 'quan-ly') {
                      if (header) header.classList.remove('hidden');
                      if (ft) ft.classList.remove('hidden');
                      if (fb) fb.classList.remove('hidden');
                      loadSummary();
                      loadCategories();
                      loadTransactions();
                  } else {
                      // Ẩn Header thẻ xanh và Chuông thông báo trên tất cả các trang khác ngoài Quản lý
                      if (header) header.classList.add('hidden');
                      if (ft) ft.classList.add('hidden');
                      if (sec === 'thong-bao' || sec === 'tai-khoan') {
                          if (fb) fb.classList.add('hidden');
                      } else {
                          if (fb) fb.classList.remove('hidden');
                      }
                  }

                  if(sec === 'thong-ke') {
                    Promise.all([loadCategories(), loadTransactions(), loadSavingsGoals()]).then(() => {
                        updateReportSummary();
                    });
                }
                if(sec === 'lich-su') {
                    if (typeof initLookupDateInput === 'function') initLookupDateInput();
                    loadTransactions();
                                        applyLookupFilter();
                }
                if(typeof loadNotifications === 'function') loadNotifications();
                if(sec === 'tai-khoan') loadUserProfile();
            }


            function switchManSubTab(tab) {
                ['ngan-sach', 'danh-muc', 'tiet-kiem'].forEach(t => {
                    document.getElementById('man-' + t).classList.add('hidden');
                    document.getElementById('msub-' + (t === 'ngan-sach' ? 'ns' : (t === 'danh-muc' ? 'dm' : 'tk'))).className = "flex-1 py-1.5 rounded-lg text-slate-600";
                });
                document.getElementById('man-' + tab).classList.remove('hidden');
                document.getElementById('msub-' + (tab === 'ngan-sach' ? 'ns' : (tab === 'danh-muc' ? 'dm' : 'tk'))).className = "flex-1 py-1.5 rounded-lg bg-white text-teal-600 shadow-sm";
                
                loadSummary();
                if(tab === 'ngan-sach') {
                    if (typeof loadCategories === 'function') loadCategories();
                    renderJarsProgressList();
                    if (typeof loadNotifications === 'function') loadNotifications();
                }
                if(tab === 'danh-muc') {
                    if (typeof loadCategories === 'function') loadCategories();
                    renderCategoriesCrudList();
                }
                if(tab === 'tiet-kiem') {
                    initSavingsPickers();
                    const today = getLocalDateString();
                    if(document.getElementById('sg-deadline')) document.getElementById('sg-deadline').setAttribute('min', today);
                    if (typeof loadSavingsGoals === 'function') loadSavingsGoals();
                    else renderSavingsGoalsList();
                }
            }


            function setupNumberInputsValidation() {
                const targetIds = [
                    'modal-tx-amount',
                    'edit-tx-amount',
                    'deposit-amount-input',
                    'modal-edit-limit',
                    'modal-b-limit',
                    'cat-limit-input',
                    'sg-target',
                    'edit-savings-target'
                ];

                const inputSet = new Set();
                targetIds.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) inputSet.add(el);
                });
                document.querySelectorAll('input.money-input, [data-type="money"]').forEach(el => inputSet.add(el));

                inputSet.forEach(input => {
                    input.setAttribute('inputmode', 'numeric');
                    input.setAttribute('pattern', '[0-9]*');
                    input.setAttribute('autocomplete', 'off');

                    // Chặn gõ chữ, ký tự âm (-), dấu cộng (+), chữ e/E, phím cách và số 0 ở đầu
                    input.addEventListener('keydown', function(e) {
                        const allowedNavKeys = [
                            'Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
                            'Tab', 'Enter', 'Home', 'End'
                        ];
                        if (allowedNavKeys.includes(e.key) || e.ctrlKey || e.metaKey) {
                            return;
                        }
                        // Chỉ cho phép các chữ số từ 0 đến 9
                        if (!/^[0-9]$/.test(e.key)) {
                            e.preventDefault();
                            return;
                        }
                        // Tuyệt đối không cho phép gõ số 0 ở vị trí đầu tiên
                        if (e.key === '0') {
                            const val = this.value || '';
                            const start = typeof this.selectionStart === 'number' ? this.selectionStart : 0;
                            // Nếu ô trống, hoặc con trỏ đang ở đầu chuỗi (start === 0)
                            if (val === '' || start === 0) {
                                e.preventDefault();
                                return;
                            }
                        }
                    });

                    // Làm sạch và định dạng ngay lập tức: tối đa 12 chữ số, thêm dấu chấm phân cách hàng nghìn
                    input.addEventListener('input', function() {
                        formatMoneyInput(this, 12);
                    });

                    // Xử lý dán dữ liệu: chỉ giữ lại chữ số, tối đa 12 số và định dạng dấu chấm
                    input.addEventListener('paste', function(e) {
                        e.preventDefault();
                        const pasteData = (e.clipboardData || window.clipboardData).getData('text') || '';
                        const sanitized = pasteData.replace(/\D/g, '').replace(/^0+/, '');
                        if (sanitized) {
                            this.value = sanitized;
                            formatMoneyInput(this, 12);
                            this.dispatchEvent(new Event('input'));
                        }
                    });

                    input.addEventListener('drop', function(e) {
                        e.preventDefault();
                    });
                });
            }


            async function initApp() {
                if(!token) return;
                document.getElementById('welcome-screen').classList.add('hidden');
                document.getElementById('onboarding-screen').classList.add('hidden');
                document.getElementById('auth-container').classList.add('hidden');
                document.getElementById('header-container').classList.remove('hidden');
                document.getElementById('floating-top-controls').classList.remove('hidden');
                const fb = document.getElementById('floating-bottom-controls');
                if(fb) fb.classList.remove('hidden');
                document.getElementById('app-container').classList.remove('hidden');
                document.getElementById('bottom-nav').classList.remove('hidden');

                // Luôn mở trang Quản lý và subtab Ngân Sách Hũ đầu tiên sau khi đăng nhập
                switchSection('quan-ly');
                switchManSubTab('ngan-sach');

                loadSummary();
                await loadCategories();
                await loadSavingsGoals();
                await loadTransactions();
                await loadNotifications();
                await checkLoginBudgetWarnings();
                renderJarsProgressList();
                checkNewMonthWelcome();
                if (typeof startSessionHeartbeat === 'function') startSessionHeartbeat();
            }

            async function checkNewMonthWelcome() {
                if (!token) return;
                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                const storageKey = `moneymind_new_month_welcomed_${currentYM}`;
                
                // 1. Kiểm tra nhanh ở localStorage trước
                if (localStorage.getItem(storageKey)) {
                    return;
                }

                // 2. Kiểm tra đồng bộ từ server theo tài khoản (cho cả điện thoại & laptop)
                try {
                    const res = await fetch('/api/user/welcome-status', {
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.already_welcomed) {
                            localStorage.setItem(storageKey, "true");
                            return;
                        }
                    }
                } catch (e) {
                    console.log("Kiểm tra trạng thái chào tháng mới:", e);
                }

                // 3. Nếu chưa từng xem trên bất kỳ thiết bị nào -> mới hiển thị modal
                const titleEl = document.getElementById('new-month-title');
                if (titleEl) {
                    titleEl.innerText = `Chào Tháng ${now.getMonth() + 1}/${now.getFullYear()}!`;
                }
                const modal = document.getElementById('new-month-welcome-modal');
                if (modal) {
                    modal.classList.remove('hidden');
                }
            }

            async function markMonthAsWelcomed() {
                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                const storageKey = `moneymind_new_month_welcomed_${currentYM}`;
                localStorage.setItem(storageKey, "true");
                
                // Đồng bộ lên server để tất cả thiết bị khác (laptop, điện thoại) không bao giờ hiện lại nữa
                if (token) {
                    try {
                        await fetch('/api/user/mark-welcome-month', {
                            method: 'POST',
                            headers: { 'Authorization': 'Bearer ' + token }
                        });
                    } catch (e) {
                        console.error("Lỗi đồng bộ trạng thái chào tháng mới:", e);
                    }
                }
            }

            function closeNewMonthModal() {
                const modal = document.getElementById('new-month-welcome-modal');
                if (modal) modal.classList.add('hidden');
                markMonthAsWelcomed();
            }

            function closeNewMonthModalAndGoToBudget() {
                closeNewMonthModal();
                switchSection('quan-ly');
                switchManSubTab('ngan-sach');
            }


            window.onload = function() {
                const now = new Date();
                const today = getLocalDateString();
                const curTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
                if(document.getElementById('modal-tx-date')) document.getElementById('modal-tx-date').value = today;
                if(document.getElementById('modal-tx-time')) document.getElementById('modal-tx-time').value = curTime;
                initSavingsPickers();
                if(document.getElementById('sg-deadline')) document.getElementById('sg-deadline').setAttribute('min', today);
                if(document.getElementById('edit-savings-deadline')) document.getElementById('edit-savings-deadline').setAttribute('min', today);
                
                // Khởi tạo chặn nhập số âm, ký tự đặc biệt và chữ cho tất cả các ô nhập số tiền / hạn mức
                setupNumberInputsValidation();

                if (token) {
                    initApp();
                    verifyTokenAndInit();
                }
            }

// =============================================================================
// HỖ TRỢ PHÍM ENTER: THAO TÁC TIỆN LỢI TỰ ĐỘNG NHƯ CLICK CHUỘT TRÊN MỌI FORM & MODAL
// =============================================================================
document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter') return;

    // Nếu đang focus trên chính nút button, để trình duyệt tự kích hoạt click tự nhiên, không can thiệp đúp
    if (e.target && e.target.tagName === 'BUTTON') return;

    // 1. Textarea: Nếu là ô nhập trợ lý AI, Enter để gửi tin nhắn (Shift+Enter để xuống dòng)
    if (e.target && e.target.tagName === 'TEXTAREA') {
        if (e.target.id === 'ai-input') {
            if (e.shiftKey) return; // Cho phép xuống dòng
            e.preventDefault();
            const sendBtn = document.getElementById('ai-send-btn');
            if (sendBtn) sendBtn.click();
            else if (typeof sendAiMessage === 'function') sendAiMessage();
            return;
        }
        return; // Các textarea khác (ghi chú dài) giữ nguyên Enter xuống dòng
    }

    // 2. ƯU TIÊN CAO NHẤT: CÁC MODAL THÔNG BÁO HOẶC XÁC NHẬN ĐANG MỞ
    // a) Custom Modal thông báo chung (Z-INDEX 9999)
    const customModal = document.getElementById('custom-modal');
    if (customModal && !customModal.classList.contains('hidden')) {
        e.preventDefault();
        closeCustomModal();
        return;
    }

    // b) Modal xác nhận đăng xuất
    const logoutModal = document.getElementById('logout-confirm-modal');
    if (logoutModal && !logoutModal.classList.contains('hidden')) {
        e.preventDefault();
        executeLogout();
        return;
    }

    // c) Modal xác nhận xóa giao dịch
    const delTxModal = document.getElementById('delete-tx-modal');
    if (delTxModal && !delTxModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof confirmDeleteTransactionAction === 'function') confirmDeleteTransactionAction();
        return;
    }

    // d) Modal xác nhận xóa danh mục & hoàn tiền
    const delCatModal = document.getElementById('confirm-delete-cat-modal');
    if (delCatModal && !delCatModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof executeDeleteCategory === 'function') executeDeleteCategory();
        return;
    }

    // e) Modal xác nhận xóa mục tiêu tiết kiệm
    const delSgModal = document.getElementById('delete-savings-modal');
    if (delSgModal && !delSgModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof confirmDeleteSavingsGoalAction === 'function') confirmDeleteSavingsGoalAction();
        return;
    }

    // f) Modal cảnh báo đăng nhập thiết bị khác
    const concurrentModal = document.getElementById('concurrent-logout-modal');
    if (concurrentModal && !concurrentModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof dismissConcurrentModalAndGoLogin === 'function') dismissConcurrentModalAndGoLogin();
        return;
    }

    // g) Modal chi tiết thông báo
    const notifDetailModal = document.getElementById('notification-detail-modal');
    if (notifDetailModal && !notifDetailModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof closeNotificationDetailModal === 'function') closeNotificationDetailModal();
        return;
    }

    // h) Modal chào tháng mới
    const newMonthModal = document.getElementById('new-month-welcome-modal');
    if (newMonthModal && !newMonthModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof closeNewMonthModal === 'function') closeNewMonthModal();
        return;
    }

    // 3. NẾU ĐANG FOCUS VÀO INPUT CỤ THỂ
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) {
        const inputId = e.target.id;

        // a) Đăng nhập & Đăng ký tài khoản:
        if (inputId === 'auth-email') {
            e.preventDefault();
            const passInput = document.getElementById('auth-pass');
            if (passInput && !passInput.value) {
                passInput.focus();
                return;
            }
            const submitBtn = document.getElementById('btn-auth-submit');
            if (submitBtn) submitBtn.click();
            else if (typeof submitAuth === 'function') submitAuth();
            return;
        }

        if (inputId === 'auth-pass') {
            e.preventDefault();
            if (typeof currentAuthMode !== 'undefined' && currentAuthMode === 'register') {
                const confirmPass = document.getElementById('auth-pass-confirm');
                if (confirmPass && !confirmPass.value) {
                    confirmPass.focus();
                    return;
                }
            }
            const submitBtn = document.getElementById('btn-auth-submit');
            if (submitBtn) submitBtn.click();
            else if (typeof submitAuth === 'function') submitAuth();
            return;
        }

        if (inputId === 'auth-pass-confirm') {
            e.preventDefault();
            const submitBtn = document.getElementById('btn-auth-submit');
            if (submitBtn) submitBtn.click();
            else if (typeof submitAuth === 'function') submitAuth();
            return;
        }

        // b) Onboarding 5 bước:
        if (inputId === 'ob-name' || inputId === 'ob-dob') {
            e.preventDefault();
            if (typeof nextOnboardingStep === 'function') nextOnboardingStep();
            return;
        }
        if (inputId === 'ob-wish') {
            e.preventDefault();
            if (typeof submitOnboarding === 'function') submitOnboarding();
            return;
        }

        // c) OTP xác nhận đăng ký:
        if (inputId === 'reg-otp-code') {
            e.preventDefault();
            if (typeof submitVerifyRegistrationOtp === 'function') submitVerifyRegistrationOtp();
            return;
        }

        // d) Quên mật khẩu:
        if (inputId === 'forgot-email') {
            e.preventDefault();
            if (typeof submitForgotPasswordRequest === 'function') submitForgotPasswordRequest();
            return;
        }
        if (['forgot-otp-code', 'forgot-new-pass', 'forgot-confirm-pass'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitResetPasswordConfirm === 'function') submitResetPasswordConfirm();
            return;
        }

        // e) Đổi mật khẩu tài khoản cá nhân:
        if (['acc-old-pass', 'acc-new-pass', 'acc-confirm-pass'].includes(inputId)) {
            e.preventDefault();
            if (typeof updateAccountPassword === 'function') updateAccountPassword();
            return;
        }

        // f) Chỉnh sửa hồ sơ cá nhân:
        if (['edit-pf-name', 'edit-pf-dob', 'edit-pf-occ'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitEditProfile === 'function') submitEditProfile();
            return;
        }

        // g) Thêm giao dịch thu / chi (Modal Thêm giao dịch):
        if (['modal-tx-amount', 'modal-tx-date', 'modal-tx-note'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitModalTransaction === 'function') submitModalTransaction();
            return;
        }

        // h) Chỉnh sửa giao dịch:
        if (['edit-tx-amount', 'edit-tx-date', 'edit-tx-note'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitEditTransaction === 'function') submitEditTransaction();
            return;
        }

        // i) Thêm ngân sách / hũ chi tiêu:
        if (['modal-b-name', 'modal-b-limit'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitBudgetModal === 'function') submitBudgetModal();
            return;
        }

        // j) Chỉnh sửa danh mục & hạn mức:
        if (['modal-edit-name', 'modal-edit-limit'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitEditCategory === 'function') submitEditCategory();
            return;
        }

        // k) Trích tiền vào quỹ tiết kiệm:
        if (inputId === 'deposit-amount-input') {
            e.preventDefault();
            if (typeof submitSavingsDeposit === 'function') submitSavingsDeposit();
            return;
        }

        // l) Chỉnh sửa mục tiêu tiết kiệm:
        if (['edit-savings-title', 'edit-savings-target', 'edit-savings-deadline'].includes(inputId)) {
            e.preventDefault();
            if (typeof submitEditSavings === 'function') submitEditSavings();
            return;
        }

        // m) Thêm mục tiêu tiết kiệm mới (tab Tiết kiệm):
        if (['sg-title', 'sg-target', 'sg-deadline'].includes(inputId)) {
            e.preventDefault();
            if (typeof createSavingsGoal === 'function') createSavingsGoal();
            return;
        }

        // n) Ô tìm kiếm & lọc giao dịch:
        if (inputId === 'lookup-keyword') {
            e.preventDefault();
            if (typeof applyLookupFilter === 'function') applyLookupFilter();
            return;
        }

        // o) Tổng quát: Nếu input nằm trong modal bất kỳ, kích hoạt nút hành động chính
        const parentModal = e.target.closest('div[id$="-modal"], #add-budget-modal, #plus-action-modal');
        if (parentModal && !parentModal.classList.contains('hidden')) {
            const primaryBtn = parentModal.querySelector('button.bg-teal-600, button.bg-teal-500, button.bg-emerald-600, button.bg-rose-600, button.bg-rose-500, button[type="submit"]');
            if (primaryBtn) {
                e.preventDefault();
                primaryBtn.click();
                return;
            }
        }
    }

    // 4. NẾU CÓ MODAL NỘI DUNG ĐANG MỞ VÀ KHÔNG FOCUS VÀO INPUT CỤ THỂ
    const openModals = Array.from(document.querySelectorAll('div[id$="-modal"]:not(.hidden)'));
    if (openModals.length > 0) {
        const topModal = openModals[openModals.length - 1];
        const primaryBtn = topModal.querySelector('button.bg-teal-600, button.bg-teal-500, button.bg-emerald-600, button.bg-rose-600, button.bg-rose-500');
        if (primaryBtn) {
            e.preventDefault();
            primaryBtn.click();
            return;
        }
    }
});
