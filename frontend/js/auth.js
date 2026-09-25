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


            function openLogoutModal() { document.getElementById('logout-confirm-modal').classList.remove('hidden'); }
            function closeLogoutModal() { document.getElementById('logout-confirm-modal').classList.add('hidden'); }
            function executeLogout() {
                localStorage.removeItem("moneymind_token");
                localStorage.removeItem("access_token");
                token = "";
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
                localStorage.removeItem("moneymind_token");
                token = "";
                document.getElementById('header-container').classList.add('hidden');
                document.getElementById('floating-top-controls').classList.add('hidden');
                const fb = document.getElementById('floating-bottom-controls');
                if(fb) fb.classList.add('hidden');
                document.getElementById('app-container').classList.add('hidden');
                document.getElementById('bottom-nav').classList.add('hidden');
                document.getElementById('onboarding-screen').classList.add('hidden');
                document.getElementById('auth-container').classList.add('hidden');
                document.getElementById('welcome-screen').classList.remove('hidden');
                if (typeof switchSection === 'function') switchSection('quan-ly');
                if (typeof switchManSubTab === 'function') switchManSubTab('ngan-sach');
            }


            function goToAuthMode(mode) {
                currentAuthMode = mode;
                document.getElementById('welcome-screen').classList.add('hidden');
                document.getElementById('auth-container').classList.remove('hidden');
                
                const titleEl = document.getElementById('auth-title');
                const btnEl = document.getElementById('btn-auth-submit');
                const switchEl = document.getElementById('auth-switch-link');
                const confirmBox = document.getElementById('confirm-pass-container');

                if(mode === 'login') {
                    titleEl.innerText = "Đăng nhập tài khoản";
                    btnEl.innerText = "Đăng nhập";
                    switchEl.innerText = "Chưa có tài khoản? Đăng ký ngay";
                    confirmBox.classList.add('hidden');
                } else {
                    titleEl.innerText = "Đăng ký tài khoản";
                    btnEl.innerText = "Đăng ký";
                    switchEl.innerText = "Đã có tài khoản? Đăng nhập";
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
                            return;
                        }
                    }
                    initApp();
                } else {
                    logout();
                }
            }

