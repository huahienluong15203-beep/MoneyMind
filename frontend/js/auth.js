/**
 * MoneyMind - Authentication, Profile, and Security Module
 */
var currentAuthMode = 'register';

            async function handleGoogleLogin(response) {
                const credential = response.credential;
                const res = await fetch('/google-login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({credential: credential})
                });
                if(res.ok) {
                    const d = await res.json();
                    token = d.access_token;
                    localStorage.setItem("moneymind_token", token);
                    startSessionHeartbeat();
                    verifyTokenAndInit();
                } else {
                    showCustomModal("Lỗi", "Đăng nhập Google thất bại!", "❌");
                }
            }


            function openEditProfileModal() {
                const name = document.getElementById('pf-name').innerText;
                const dob = document.getElementById('pf-dob').innerText;
                const occ = document.getElementById('pf-occ').innerText;
                const goal = document.getElementById('pf-goal').innerText;

                document.getElementById('edit-pf-name').value = (name !== 'Chưa cập nhật' && name !== '---') ? name : '';
                document.getElementById('edit-pf-dob').value = (dob !== 'Chưa cập nhật' && dob !== '---') ? dob : '';
                document.getElementById('edit-pf-occ').value = (occ !== 'Chưa cập nhật' && occ !== '---') ? occ : '';
                document.getElementById('edit-pf-goal').value = (goal !== 'Chưa cập nhật' && goal !== '---') ? goal : '';

                document.getElementById('edit-profile-modal').classList.remove('hidden');
            }

            function closeEditProfileModal() {
                document.getElementById('edit-profile-modal').classList.add('hidden');
            }

            async function submitEditProfile() {
                const full_name = document.getElementById('edit-pf-name').value.trim();
                const dob = document.getElementById('edit-pf-dob').value;
                const occupation = document.getElementById('edit-pf-occ').value.trim();
                const goals = document.getElementById('edit-pf-goal').value.trim();

                if(!full_name) return showCustomModal("Thiếu thông tin", "Vui lòng nhập họ và tên của bạn!", "⚠️");

                const res = await fetch('/tai-khoan', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({full_name, dob, occupation, goals})
                });

                if(res.ok) {
                    const u = await res.json();
                    document.getElementById('pf-name').innerText = u.full_name || 'Chưa cập nhật';
                    document.getElementById('pf-dob').innerText = u.dob || 'Chưa cập nhật';
                    document.getElementById('pf-occ').innerText = u.occupation || 'Chưa cập nhật';
                    document.getElementById('pf-goal').innerText = u.goals || 'Chưa cập nhật';
                    closeEditProfileModal();
                    showCustomModal("Thành công", "Đã cập nhật thông tin cá nhân thành công!", "✅");
                } else {
                    let err = await res.json().catch(() => ({}));
                    showCustomModal("Lỗi", err.detail || "Không thể cập nhật thông tin cá nhân!", "❌");
                }
            }


            function togglePasswordModal() { document.getElementById('password-modal').classList.toggle('hidden'); }


            async function updateAccountPassword() {
                const old_pass = document.getElementById('acc-old-pass').value;
                const new_pass = document.getElementById('acc-new-pass').value;
                const confirm_pass = document.getElementById('acc-confirm-pass').value;

                if(!old_pass || !new_pass || !confirm_pass) return showCustomModal("Lỗi", "Vui lòng nhập đầy đủ các trường mật khẩu!", "⚠️");
                if(new_pass !== confirm_pass) return showCustomModal("Lỗi", "Mật khẩu mới và xác nhận mật khẩu không khớp!", "⚠️");

                const res = await fetch('/doi-mat-khau', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({old_pass, new_pass})
                });
                if(res.ok) { 
                    showCustomModal("Thành công", "Đổi mật khẩu thành công!", "✅"); 
                    togglePasswordModal();
                    document.getElementById('acc-old-pass').value = '';
                    document.getElementById('acc-new-pass').value = '';
                    document.getElementById('acc-confirm-pass').value = '';
                } else {
                    showCustomModal("Lỗi", "Mật khẩu hiện tại không chính xác!", "❌");
                }
            }


            function clearClientSessionState() {
                stopSessionHeartbeat();
                localStorage.removeItem("moneymind_token");
                localStorage.removeItem("access_token");
                sessionStorage.removeItem("current_ai_session_id");
                if (typeof currentAiSessionId !== 'undefined') currentAiSessionId = null;
                if (typeof aiChatHistory !== 'undefined') aiChatHistory = [];
                token = "";
                allNotifications = [];
                allTransactions = [];
                allCategories = [];
                allSavingsGoals = [];

                if (typeof renderNotificationsList === 'function') {
                    renderNotificationsList();
                }

                const notifList = document.getElementById('notifications-list');
                if (notifList) {
                    notifList.innerHTML = `
                        <div class="text-center py-10 space-y-2">
                            <span class="text-3xl">📭</span>
                            <p class="text-xs font-bold text-slate-500">Chưa có thông báo hoặc cảnh báo nào</p>
                            <p class="text-[11px] text-slate-400">Các cảnh báo chi tiêu, trích ví và biến động tài chính sẽ được ghi nhận tại đây.</p>
                        </div>
                    `;
                }

                const topBadge = document.getElementById('top-notif-badge');
                if (topBadge) {
                    topBadge.classList.add('hidden');
                    topBadge.style.display = 'none';
                    topBadge.innerText = '';
                }

                const countBadge = document.getElementById('notif-count-badge');
                if (countBadge) countBadge.innerText = '0 thông báo';

                const txList = document.getElementById('tx-list');
                if (txList) txList.innerHTML = '';
                const jarsList = document.getElementById('jars-progress-list');
                if (jarsList) jarsList.innerHTML = '';
                const lookupList = document.getElementById('lookup-tx-list');
                if (lookupList) lookupList.innerHTML = '';
                const mainBal = document.getElementById('main-wallet-balance');
                if (mainBal) mainBal.innerText = '0 đ';
                const totalSpent = document.getElementById('total-spent');
                if (totalSpent) totalSpent.innerText = '0 đ';
                const totalIncome = document.getElementById('total-income');
                if (totalIncome) totalIncome.innerText = '0 đ';
                const pfName = document.getElementById('pf-name');
                if (pfName) pfName.innerText = '---';
            }

            function openLogoutModal() { document.getElementById('logout-confirm-modal').classList.remove('hidden'); }
            function closeLogoutModal() { document.getElementById('logout-confirm-modal').classList.add('hidden'); }
            function executeLogout() {
                clearClientSessionState();
                closeLogoutModal();
                document.getElementById('header-container').classList.add('hidden');
                document.getElementById('floating-top-controls').classList.add('hidden');
                const fb = document.getElementById('floating-bottom-controls');
                if(fb) fb.classList.add('hidden');
                document.getElementById('app-container').classList.add('hidden');
                document.getElementById('bottom-nav').classList.add('hidden');
                document.getElementById('onboarding-screen').classList.add('hidden');
                document.getElementById('auth-container').classList.add('hidden');
                document.getElementById('welcome-screen').classList.remove('hidden');
            }


            function logout() {
                clearClientSessionState();
                const header = document.getElementById('header-container');
                if(header) header.classList.add('hidden');
                const ft = document.getElementById('floating-top-controls');
                if(ft) ft.classList.add('hidden');
                const fb = document.getElementById('floating-bottom-controls');
                if(fb) fb.classList.add('hidden');
                document.getElementById('app-container').classList.add('hidden');
                document.getElementById('bottom-nav').classList.add('hidden');
                document.getElementById('onboarding-screen').classList.add('hidden');
                document.getElementById('auth-container').classList.add('hidden');
                document.getElementById('welcome-screen').classList.remove('hidden');
                currentSection = 'quan-ly';
                if (typeof switchManSubTab === 'function') switchManSubTab('ngan-sach');
            }


            function goToWelcomeScreen() {
                document.getElementById('auth-container').classList.add('hidden');
                document.getElementById('welcome-screen').classList.remove('hidden');
            }

            function goToAuthMode(mode) {
                currentAuthMode = mode;
                const header = document.getElementById('header-container');
                if(header) header.classList.add('hidden');
                const ft = document.getElementById('floating-top-controls');
                if(ft) ft.classList.add('hidden');
                const fb = document.getElementById('floating-bottom-controls');
                if(fb) fb.classList.add('hidden');

                document.getElementById('welcome-screen').classList.add('hidden');
                document.getElementById('auth-container').classList.remove('hidden');
                
                const titleEl = document.getElementById('auth-title');
                const btnEl = document.getElementById('btn-auth-submit');
                const switchEl = document.getElementById('auth-switch-link');
                const forgotBox = document.getElementById('auth-forgot-box');
                const confirmBox = document.getElementById('confirm-pass-container');

                if(mode === 'login') {
                    titleEl.innerText = "Đăng nhập tài khoản";
                    btnEl.innerText = "Đăng nhập";
                    if(forgotBox) forgotBox.classList.remove('hidden');
                    if(switchEl) {
                        switchEl.innerText = "Chưa có tài khoản? Đăng ký ngay";
                        switchEl.className = "text-[11px] text-slate-400 hover:text-teal-600 cursor-pointer";
                    }
                    confirmBox.classList.add('hidden');
                } else {
                    titleEl.innerText = "Đăng ký tài khoản";
                    btnEl.innerText = "Đăng ký";
                    if(forgotBox) forgotBox.classList.add('hidden');
                    if(switchEl) {
                        switchEl.innerText = "Đã có tài khoản? Đăng nhập";
                        switchEl.className = "text-xs text-teal-600 font-bold cursor-pointer";
                    }
                    confirmBox.classList.remove('hidden');
                }
            }

            function toggleAuthMode(e) {
                e.preventDefault();
                currentAuthMode = (currentAuthMode === 'login') ? 'register' : 'login';
                goToAuthMode(currentAuthMode);
            }

            function goToLoginDirect() { goToAuthMode('login'); }
            function startWelcomeAuth() { goToAuthMode('register'); }

            let pendingRegisterData = null;

            async function submitAuth() {
                const email = document.getElementById('auth-email').value.trim().toLowerCase();
                const password = document.getElementById('auth-pass').value;

                if(!email || !password) return showCustomModal("Thiếu thông tin", "Vui lòng nhập đầy đủ Email và Mật khẩu!", "⚠️");

                if(currentAuthMode === 'login') {
                    const res = await fetch('/dang-nhap', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: email, password: password})
                    });
                    if(res.ok) {
                        const d = await res.json();
                        token = d.access_token;
                        setStoredToken(token);
                        startSessionHeartbeat();
                        verifyTokenAndInit();
                    } else {
                        let err = await res.json().catch(() => ({}));
                        showCustomModal("Đăng nhập thất bại", err.detail || "Sai tài khoản hoặc mật khẩu!", "❌");
                    }
                } else {
                    const passConfirm = document.getElementById('auth-pass-confirm').value;
                    const termsChecked = document.getElementById('auth-terms').checked;

                    if(!email.includes('@')) {
                        return showCustomModal("Email không hợp lệ", "Vui lòng nhập địa chỉ email hợp lệ (ví dụ: yourname@gmail.com)!", "⚠️");
                    }
                    if(password !== passConfirm) return showCustomModal("Lỗi", "Mật khẩu nhập lại không khớp!", "⚠️");
                    if(password.length < 4) return showCustomModal("Mật khẩu yếu", "Mật khẩu phải có tối thiểu 4 ký tự!", "⚠️");
                    if(!termsChecked) return showCustomModal("Cần xác nhận", "Vui lòng tích chọn đồng ý với điều khoản dịch vụ!", "⚠️");

                    const submitBtn = document.getElementById('btn-auth-submit');
                    submitBtn.disabled = true;
                    submitBtn.innerText = "Đang gửi mã xác nhận về Gmail...";

                    try {
                        const res = await fetch('/gui-otp-dang-ky', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({email})
                        });
                        const data = await res.json();
                        if(res.ok) {
                            pendingRegisterData = { email, password };
                            document.getElementById('reg-otp-email-display').innerText = email;
                            const otpInput = document.getElementById('reg-otp-code');
                            if (otpInput) {
                                otpInput.value = "";
                                setTimeout(() => otpInput.focus(), 150);
                            }
                            document.getElementById('register-otp-modal').classList.remove('hidden');
                            startOtpResendTimer();
                        } else {
                            showCustomModal("Không thể gửi mã xác nhận", data.detail || "Vui lòng kiểm tra lại địa chỉ email hoặc cấu hình SMTP Gmail!", "❌");
                        }
                    } catch(e) {
                        showCustomModal("Lỗi kết nối", e.message, "❌");
                    } finally {
                        submitBtn.disabled = false;
                        submitBtn.innerText = "Đăng ký";
                    }
                }
            }


            async function submitVerifyRegistrationOtp() {
                if(!pendingRegisterData) return;
                const otp = document.getElementById('reg-otp-code').value.trim();
                if(!otp || otp.length < 4) {
                    return showCustomModal("Thiếu mã OTP", "Vui lòng nhập đầy đủ mã OTP đã được gửi về Gmail của bạn!", "⚠️");
                }

                const btn = document.getElementById('btn-reg-verify-otp');
                btn.disabled = true;
                btn.innerText = "Đang xác thực...";

                try {
                    const res = await fetch('/xac-nhan-dang-ky', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            email: pendingRegisterData.email,
                            password: pendingRegisterData.password,
                            otp: otp
                        })
                    });
                    const data = await res.json();
                    if(res.ok) {
                        clearClientSessionState();
                        token = data.access_token;
                        setStoredToken(token);
                        closeRegisterOtpModal();
                        showCustomModal("Đăng ký thành công", "Tài khoản của bạn đã được kích hoạt thành công!", "🎉", () => {
                            document.getElementById('auth-container').classList.add('hidden');
                            document.getElementById('onboarding-screen').classList.remove('hidden');
                        });
                    } else {
                        showCustomModal("Xác thực thất bại", data.detail || "Mã OTP không chính xác hoặc đã hết hạn!", "❌");
                    }
                } catch(e) {
                    showCustomModal("Lỗi kết nối", e.message, "❌");
                } finally {
                    btn.disabled = false;
                    btn.innerText = "Xác Nhận & Hoàn Tất Đăng Ký";
                }
            }

            var otpResendCountdownInterval = null;
            function startOtpResendTimer() {
                const btn = document.getElementById('btn-reg-resend-otp');
                if (!btn) return;
                let seconds = 60;
                btn.disabled = true;
                btn.className = "text-slate-400 font-semibold cursor-not-allowed text-xs";
                btn.innerText = `Gửi lại sau (${seconds}s)`;
                if (otpResendCountdownInterval) clearInterval(otpResendCountdownInterval);
                otpResendCountdownInterval = setInterval(() => {
                    seconds--;
                    if (seconds <= 0) {
                        clearInterval(otpResendCountdownInterval);
                        btn.disabled = false;
                        btn.className = "text-teal-600 hover:text-teal-700 font-semibold transition cursor-pointer text-xs";
                        btn.innerText = "Gửi lại mã OTP";
                    } else {
                        btn.innerText = `Gửi lại sau (${seconds}s)`;
                    }
                }, 1000);
            }

            async function resendRegistrationOtp() {
                if(!pendingRegisterData) return;
                const btn = document.getElementById('btn-reg-resend-otp');
                btn.disabled = true;
                btn.innerText = "Đang gửi...";
                try {
                    const res = await fetch('/gui-otp-dang-ky', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({email: pendingRegisterData.email})
                    });
                    const data = await res.json();
                    if(res.ok) {
                        startOtpResendTimer();
                        showCustomModal("Đã gửi mã xác nhận", "Mã OTP mới đã được gửi về Gmail của bạn. Vui lòng kiểm tra hộp thư!", "✉️");
                    } else {
                        btn.disabled = false;
                        btn.innerText = "Gửi lại mã OTP";
                        showCustomModal("Lỗi gửi OTP", data.detail || "Không thể gửi lại mã!", "❌");
                    }
                } catch(e) {
                    btn.disabled = false;
                    btn.innerText = "Gửi lại mã OTP";
                    showCustomModal("Lỗi", e.message, "❌");
                }
            }

            function closeRegisterOtpModal() {
                if (otpResendCountdownInterval) clearInterval(otpResendCountdownInterval);
                document.getElementById('register-otp-modal').classList.add('hidden');
            }

            // ==========================================
            // CHỨC NĂNG QUÊN MẬT KHẨU & ĐẶT LẠI QUA GMAIL THẬT
            // ==========================================
            var forgotResendCountdownInterval = null;

            function openForgotPasswordModal(e) {
                if (e) e.preventDefault();
                const currentEmail = (document.getElementById('auth-email')?.value || '').trim();
                const forgotEmailInput = document.getElementById('forgot-email');
                if (forgotEmailInput && currentEmail) {
                    forgotEmailInput.value = currentEmail;
                }
                document.getElementById('forgot-step-1').classList.remove('hidden');
                document.getElementById('forgot-step-2').classList.add('hidden');
                document.getElementById('forgot-password-modal').classList.remove('hidden');
                if (forgotEmailInput) {
                    setTimeout(() => forgotEmailInput.focus(), 150);
                }
            }

            function closeForgotPasswordModal() {
                if (forgotResendCountdownInterval) clearInterval(forgotResendCountdownInterval);
                document.getElementById('forgot-password-modal').classList.add('hidden');
            }

            function backToForgotStep1() {
                if (forgotResendCountdownInterval) clearInterval(forgotResendCountdownInterval);
                document.getElementById('forgot-step-2').classList.add('hidden');
                document.getElementById('forgot-step-1').classList.remove('hidden');
                const emailInput = document.getElementById('forgot-email');
                if (emailInput) setTimeout(() => emailInput.focus(), 150);
            }

            function startForgotOtpResendTimer() {
                const btn = document.getElementById('btn-forgot-resend-otp');
                if (!btn) return;
                let seconds = 60;
                btn.disabled = true;
                btn.className = "text-slate-400 font-semibold cursor-not-allowed text-xs";
                btn.innerText = `Gửi lại sau (${seconds}s)`;
                if (forgotResendCountdownInterval) clearInterval(forgotResendCountdownInterval);
                forgotResendCountdownInterval = setInterval(() => {
                    seconds--;
                    if (seconds <= 0) {
                        clearInterval(forgotResendCountdownInterval);
                        btn.disabled = false;
                        btn.className = "text-teal-600 hover:text-teal-700 font-semibold transition cursor-pointer text-xs";
                        btn.innerText = "Gửi lại mã OTP";
                    } else {
                        btn.innerText = `Gửi lại sau (${seconds}s)`;
                    }
                }, 1000);
            }

            async function submitForgotPasswordRequest() {
                const emailInput = document.getElementById('forgot-email');
                const email = (emailInput ? emailInput.value : "").trim().toLowerCase();

                if (!email || !email.includes('@')) {
                    return showCustomModal("Thiếu thông tin", "Vui lòng nhập địa chỉ Gmail hợp lệ (ví dụ: yourname@gmail.com)!", "⚠️");
                }

                const btn = document.getElementById('btn-forgot-send-otp');
                btn.disabled = true;
                const oldText = btn.innerText;
                btn.innerText = "Đang gửi mã về Gmail...";

                try {
                    const res = await fetch('/quen-mat-khau', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({email: email})
                    });
                    const data = await res.json();
                    if (res.ok) {
                        document.getElementById('forgot-email-display').innerText = email;
                        document.getElementById('forgot-step-1').classList.add('hidden');
                        document.getElementById('forgot-step-2').classList.remove('hidden');
                        const otpInput = document.getElementById('forgot-otp-code');
                        if (otpInput) {
                            otpInput.value = "";
                            setTimeout(() => otpInput.focus(), 150);
                        }
                        document.getElementById('forgot-new-pass').value = "";
                        document.getElementById('forgot-confirm-pass').value = "";
                        startForgotOtpResendTimer();
                        showCustomModal("Đã gửi mã xác nhận", data.thong_bao || `Mã OTP đã được gửi đến hòm thư ${email}. Vui lòng kiểm tra hộp thư đến hoặc mục Thư rác (Spam).`, "✉️");
                    } else {
                        showCustomModal("Không thể gửi mã", data.detail || "Không tìm thấy tài khoản tương ứng với Gmail này!", "❌");
                    }
                } catch (e) {
                    showCustomModal("Lỗi kết nối", e.message || "Không thể kết nối đến máy chủ!", "❌");
                } finally {
                    btn.disabled = false;
                    btn.innerText = oldText;
                }
            }

            async function resendForgotPasswordOtp() {
                const email = document.getElementById('forgot-email-display').innerText.trim().toLowerCase();
                if (!email) return;

                const btn = document.getElementById('btn-forgot-resend-otp');
                btn.disabled = true;
                btn.innerText = "Đang gửi...";

                try {
                    const res = await fetch('/quen-mat-khau', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({email: email})
                    });
                    const data = await res.json();
                    if (res.ok) {
                        startForgotOtpResendTimer();
                        showCustomModal("Đã gửi lại mã", data.thong_bao || "Mã OTP mới đã được gửi về Gmail của bạn. Vui lòng kiểm tra hộp thư!", "✉️");
                    } else {
                        btn.disabled = false;
                        btn.innerText = "Gửi lại mã OTP";
                        showCustomModal("Lỗi gửi mã", data.detail || "Không thể gửi lại mã xác nhận!", "❌");
                    }
                } catch (e) {
                    btn.disabled = false;
                    btn.innerText = "Gửi lại mã OTP";
                    showCustomModal("Lỗi kết nối", e.message, "❌");
                }
            }

            async function submitResetPasswordConfirm() {
                const email = document.getElementById('forgot-email-display').innerText.trim().toLowerCase();
                const otp = document.getElementById('forgot-otp-code').value.trim();
                const newPass = document.getElementById('forgot-new-pass').value;
                const confirmPass = document.getElementById('forgot-confirm-pass').value;

                if (!otp || otp.length < 4) {
                    return showCustomModal("Thiếu mã OTP", "Vui lòng nhập đầy đủ mã OTP đã được gửi về Gmail!", "⚠️");
                }
                if (!newPass || newPass.length < 4) {
                    return showCustomModal("Mật khẩu yếu", "Mật khẩu mới phải có tối thiểu 4 ký tự!", "⚠️");
                }
                if (newPass !== confirmPass) {
                    return showCustomModal("Không trùng khớp", "Mật khẩu mới và xác nhận mật khẩu không trùng khớp!", "⚠️");
                }

                const btn = document.getElementById('btn-forgot-confirm-reset');
                btn.disabled = true;
                const oldText = btn.innerText;
                btn.innerText = "Đang xác thực...";

                try {
                    const res = await fetch('/dat-lai-mat-khau', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            email: email,
                            otp: otp,
                            new_password: newPass
                        })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        closeForgotPasswordModal();
                        document.getElementById('auth-email').value = email;
                        document.getElementById('auth-pass').value = newPass;
                        goToAuthMode('login');
                        showCustomModal("Đặt lại mật khẩu thành công! 🎉", "Mật khẩu của bạn đã được cập nhật. Bạn có thể nhấn 'Đăng nhập' ngay bây giờ!", "✅");
                    } else {
                        showCustomModal("Xác thực thất bại", data.detail || "Mã OTP không chính xác hoặc đã hết hạn!", "❌");
                    }
                } catch (e) {
                    showCustomModal("Lỗi kết nối", e.message || "Không thể kết nối đến máy chủ!", "❌");
                } finally {
                    btn.disabled = false;
                    btn.innerText = oldText;
                }
            }



            function selectOccupation(val, btnEl) {
                const input = document.getElementById('ob-occupation');
                if (input) input.value = val;
                const allBtns = document.querySelectorAll('.ob-occ-btn');
                allBtns.forEach(b => {
                    b.className = "ob-occ-btn p-2.5 rounded-xl border text-xs flex items-center gap-2 transition text-left cursor-pointer border-slate-200 bg-white text-slate-700 hover:border-teal-300 hover:bg-slate-50 font-medium";
                });
                if (btnEl) {
                    btnEl.className = "ob-occ-btn p-2.5 rounded-xl border text-xs flex items-center gap-2 transition text-left cursor-pointer border-teal-500 bg-teal-50/90 text-teal-800 font-bold shadow-xs";
                }
            }

            async function submitOnboarding() {
                const name = document.getElementById('ob-name').value;
                const dob = document.getElementById('ob-dob').value;
                const occupation = document.getElementById('ob-occupation').value;
                const goal = document.getElementById('ob-goal').value;
                const wish = document.getElementById('ob-wish').value;

                if(!name) return showCustomModal("Thiếu thông tin", "Vui lòng nhập họ và tên của bạn!", "⚠️");

                let profileData = {
                    full_name: name, 
                    dob: dob, 
                    occupation: occupation, 
                    goals: goal + " - " + wish
                };

                const res = await fetch('/cap-nhat-ho-so', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify(profileData)
                });

                if(res.ok) {
                    showCustomModal("Hoàn tất", "Hồ sơ của bạn đã được thiết lập thành công!", "🎉");
                    initApp();
                } else {
                    showCustomModal("Lỗi", "Không thể cập nhật hồ sơ cá nhân!", "❌");
                }
            }


            async function loadUserProfile() {
                const res = await fetch('/tai-khoan', {headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    const u = await res.json();
                    const name = u.full_name || 'Chưa cập nhật';
                    const dob = u.dob || 'Chưa cập nhật';
                    const occ = u.occupation || 'Chưa cập nhật';
                    const goal = u.goals || 'Chưa cập nhật';
                    // Tab cũ trong Quản lý
                    if(document.getElementById('pf-name')) document.getElementById('pf-name').innerText = name;
                    if(document.getElementById('pf-dob')) document.getElementById('pf-dob').innerText = dob;
                    if(document.getElementById('pf-occ')) document.getElementById('pf-occ').innerText = occ;
                    if(document.getElementById('pf-goal')) document.getElementById('pf-goal').innerText = goal;
                    // Section Tài khoản mới (bottom nav)
                    if(document.getElementById('pf-name2')) document.getElementById('pf-name2').innerText = name;
                    if(document.getElementById('pf-dob2')) document.getElementById('pf-dob2').innerText = dob;
                    if(document.getElementById('pf-occ2')) document.getElementById('pf-occ2').innerText = occ;
                    if(document.getElementById('pf-goal2')) document.getElementById('pf-goal2').innerText = goal;
                }
            }


            async function verifyTokenAndInit() {
                const res = await fetch('/thong-ke', {headers: {'Authorization': 'Bearer ' + token}});
                if (res.ok) {
                    const profileRes = await fetch('/tai-khoan', {headers: {'Authorization': 'Bearer ' + token}});
                    if(profileRes.ok) {
                        const prof = await profileRes.json();
                        if(!prof.full_name) {
                            document.getElementById('welcome-screen').classList.add('hidden');
                            document.getElementById('auth-container').classList.add('hidden');
                            document.getElementById('onboarding-screen').classList.remove('hidden');
                            startSessionHeartbeat();
                            return;
                        }
                    }
                    initApp();
                    startSessionHeartbeat();
                } else {
                    const reason = res.headers.get('X-Logout-Reason') || '';
                    if (reason === 'concurrent_login') {
                        handleConcurrentKickout();
                    } else {
                        logout();
                    }
                }
            }

            // =================================================================
            // ĐỒNG BỘ PHIÊN ĐĂNG NHẬP ĐƠN THIẾT BỊ (CONCURRENT LOGIN DETECTION)
            // =================================================================
            var sessionHeartbeatTimer = null;
            var isHandlingConcurrentKickout = false;

            function startSessionHeartbeat() {
                stopSessionHeartbeat();
                if (!token) return;

                // Kiểm tra định kỳ mỗi 1 giây (1s) đúng theo yêu cầu người dùng
                sessionHeartbeatTimer = setInterval(async () => {
                    if (!token) {
                        stopSessionHeartbeat();
                        return;
                    }
                    try {
                        const res = await fetch('/check-session', {
                            headers: { 'Authorization': 'Bearer ' + token },
                            cache: 'no-store'
                        });
                        if (res.status === 401 || res.status === 403) {
                            const data = await res.json().catch(() => ({}));
                            const reason = res.headers.get('X-Logout-Reason') || '';
                            const detail = data.detail || '';
                            if (reason === 'concurrent_login' || detail.includes('thiết bị khác') || res.status === 401) {
                                handleConcurrentKickout();
                            }
                        }
                    } catch (e) {
                        // Bỏ qua lỗi rớt mạng chập chờn
                    }
                }, 1000);
            }

            function stopSessionHeartbeat() {
                if (sessionHeartbeatTimer) {
                    clearInterval(sessionHeartbeatTimer);
                    sessionHeartbeatTimer = null;
                }
            }

            function handleConcurrentKickout() {
                if (isHandlingConcurrentKickout) return;
                isHandlingConcurrentKickout = true;

                stopSessionHeartbeat();
                clearClientSessionState();

                // Ẩn tất cả container ứng dụng
                const header = document.getElementById('header-container');
                if (header) header.classList.add('hidden');
                const ft = document.getElementById('floating-top-controls');
                if (ft) ft.classList.add('hidden');
                const fb = document.getElementById('floating-bottom-controls');
                if (fb) fb.classList.add('hidden');
                const app = document.getElementById('app-container');
                if (app) app.classList.add('hidden');
                const bnav = document.getElementById('bottom-nav');
                if (bnav) bnav.classList.add('hidden');
                const onb = document.getElementById('onboarding-screen');
                if (onb) onb.classList.add('hidden');

                // Chuyển ngầm về chế độ đăng nhập
                goToAuthMode('login');

                // Hiển thị modal thông báo đã đăng nhập ở thiết bị khác
                const modal = document.getElementById('concurrent-logout-modal');
                if (modal) {
                    modal.classList.remove('hidden');
                } else {
                    showCustomModal(
                        "Đã đăng nhập ở nơi khác",
                        "Tài khoản của bạn vừa được đăng nhập trên một thiết bị khác. Thiết bị này đã tự động đăng xuất để bảo vệ an toàn tài khoản.",
                        "⚠️"
                    );
                }

                setTimeout(() => {
                    isHandlingConcurrentKickout = false;
                }, 2000);
            }

            function dismissConcurrentModalAndGoLogin() {
                const modal = document.getElementById('concurrent-logout-modal');
                if (modal) modal.classList.add('hidden');
                goToAuthMode('login');
            }


