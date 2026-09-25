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
                if (sec === 'quan-ly') {
                    header.classList.remove('hidden');
                    loadSummary();
                    loadCategories();
                    loadTransactions();
                } else {
                    header.classList.add('hidden');
                }

                if(sec === 'thong-ke') {
                    Promise.all([loadCategories(), loadTransactions(), loadSavingsGoals()]).then(() => {
                        updateReportSummary();
                    });
                }
                if(sec === 'lich-su') {
                    loadTransactions();
                    applyLookupFilter();
                }
                if(sec === 'thong-bao') loadNotifications();
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
                if(tab === 'ngan-sach') renderJarsProgressList();
                if(tab === 'danh-muc') renderCategoriesCrudList();
                if(tab === 'tiet-kiem') {
                    initSavingsPickers();
                    const today = getLocalDateString();
                    if(document.getElementById('sg-deadline')) document.getElementById('sg-deadline').setAttribute('min', today);
                    renderSavingsGoalsList();
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

                    // Làm sạch ngay lập tức: chỉ giữ chữ số và xóa sạch số 0 ở đầu
                    input.addEventListener('input', function() {
                        const sanitized = this.value.replace(/[^0-9]/g, '').replace(/^0+/, '');
                        if (this.value !== sanitized) {
                            this.value = sanitized;
                        }
                    });

                    // Xử lý dán dữ liệu: chỉ giữ lại chữ số và loại bỏ số 0 ở đầu
                    input.addEventListener('paste', function(e) {
                        e.preventDefault();
                        const pasteData = (e.clipboardData || window.clipboardData).getData('text') || '';
                        const sanitized = pasteData.replace(/[^0-9]/g, '');
                        if (sanitized) {
                            const start = typeof this.selectionStart === 'number' ? this.selectionStart : 0;
                            const end = typeof this.selectionEnd === 'number' ? this.selectionEnd : 0;
                            const currentVal = this.value || '';
                            const newVal = (currentVal.substring(0, start) + sanitized + currentVal.substring(end)).replace(/^0+/, '');
                            this.value = newVal;
                            this.selectionStart = this.selectionEnd = Math.min(newVal.length, start + sanitized.length);
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
            }


            window.onload = function() {
                const today = getLocalDateString();
                if(document.getElementById('modal-tx-date')) document.getElementById('modal-tx-date').value = today;
                initSavingsPickers();
                if(document.getElementById('sg-deadline')) document.getElementById('sg-deadline').setAttribute('min', today);
                if(document.getElementById('edit-savings-deadline')) document.getElementById('edit-savings-deadline').setAttribute('min', today);
                
                // Khởi tạo chặn nhập số âm, ký tự đặc biệt và chữ cho tất cả các ô nhập số tiền / hạn mức
                setupNumberInputsValidation();

                if (token) verifyTokenAndInit();
            }
