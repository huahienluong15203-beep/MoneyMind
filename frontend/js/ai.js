/**
 * MoneyMind - Trợ Lý AI Tài Chính Thông Minh (Google Gemini Flash Engine)
 */
var currentAiSessionId = sessionStorage.getItem('current_ai_session_id') || null;

function getOrCreateAiSessionId() {
    if (!currentAiSessionId) {
        currentAiSessionId = sessionStorage.getItem('current_ai_session_id');
        if (!currentAiSessionId) {
            currentAiSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
            sessionStorage.setItem('current_ai_session_id', currentAiSessionId);
        }
    }
    return currentAiSessionId;
}

function startNewAiSession(showAlert = false) {
    currentAiSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    sessionStorage.setItem('current_ai_session_id', currentAiSessionId);
    aiChatHistory = [];

    const box = document.getElementById('ai-chat-box');
    if (box) {
        box.innerHTML = `
            <div class="flex gap-2">
                <div class="w-7 h-7 rounded-full overflow-hidden shrink-0 shadow-xs border border-teal-100">
                    <img src="./icons/piggy-bank.png" alt="AI" class="w-full h-full object-cover">
                </div>
                <div class="bg-white p-3 rounded-2xl border border-slate-100 text-slate-700 shadow-sm leading-relaxed">
                    Xin chào! Tôi là Trợ lý AI tài chính cá nhân MoneyMind. Bạn có thể trò chuyện tự nhiên để <strong>ghi nhanh chi tiêu</strong> (ví dụ: <em>"Ăn bánh mì 20k"</em>, <em>"Đổ xăng 50k"</em>, <em>"Nộp 500k vào mục tiêu du lịch"</em>) hoặc hỏi đáp, phân tích ngân sách tài chính cá nhân. Bạn cần mình giúp gì nào? 😊
                </div>
            </div>
        `;
    }
    const input = document.getElementById('ai-input');
    if (input) {
        input.value = '';
        input.focus();
    }
    if (typeof currentAiTab !== 'undefined' && currentAiTab === 'logs') {
        switchAiTab('chat');
    }
    if (showAlert && typeof showCustomToast === 'function') {
        showCustomToast("Đã bắt đầu phiên trò chuyện mới! 💬", "info");
    }
    updateAiLogBadge();
}

function toggleAiModal() {
    const modal = document.getElementById('ai-modal');
    if (!modal) return;
    modal.classList.toggle('hidden');
    if (!modal.classList.contains('hidden')) {
        // Mở modal: Sử dụng phiên hiện tại (không tạo phiên mới khi chỉ đóng/mở modal)
        getOrCreateAiSessionId();
        updateAiLogBadge();
        if (currentAiTab === 'logs') {
            loadAiLogs();
        }
    } else {
        // Đóng modal qua nút [X]:
        // TUYỆT ĐỐI KHÔNG kết thúc phiên, giữ nguyên phiên hiện tại
        if (typeof loadSummary === 'function') loadSummary();
        if (typeof loadSavingsGoals === 'function') loadSavingsGoals();
        if (typeof loadCategories === 'function') loadCategories();
        if (typeof loadTransactions === 'function') loadTransactions();
        if (typeof loadNotifications === 'function') loadNotifications();
    }
}

            function formatAIResponse(text) {
                if (!text) return '';
                // 1. Chống lỗi nuốt thẻ: Escape ký tự < và > để trình duyệt không hiểu nhầm là thẻ HTML
                let safe = text
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');

                // 2. Định dạng Markdown tiêu đề
                safe = safe.replace(/^### (.*$)/gim, '<div class="font-bold text-sm text-teal-800 mt-2 mb-1">$1</div>');
                safe = safe.replace(/^## (.*$)/gim, '<div class="font-bold text-base text-teal-900 mt-2 mb-1">$1</div>');

                // 3. Định dạng in đậm và in nghiêng
                safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>');
                safe = safe.replace(/\*(.*?)\*/g, '<em class="text-slate-600">$1</em>');

                // 4. Định dạng gạch đầu dòng Markdown (* hoặc - hoặc •)
                safe = safe.replace(/^[\*\-•] (.*$)/gim, '<div class="flex gap-1.5 items-start my-0.5"><span class="text-teal-500 font-bold shrink-0">•</span><span>$1</span></div>');

                // 5. Định dạng emoji
                safe = safe.replace(/🎯|💰|📊|✅|❌|⚠️|🌟|💡|📈|📉|🏆|🍜|🎈|🍽️/g, '<span style="display:inline-block">$&</span>');

                // 6. Định dạng đường kẻ ngang ---
                safe = safe.replace(/^---$/gim, '<hr class="my-2 border-slate-200">');

                // 7. Định dạng bảng hoặc ký tự pipe |
                safe = safe.replace(/\|(.*?)\|/g, '<span class="font-mono text-xs bg-slate-100 px-1 rounded">$1</span>');

                // 8. Xuống dòng
                safe = safe.replace(/\n\n+/g, '<br><br>').replace(/\n/g, '<br>');

                return safe;
            }



            function quickAskAi(q) {
                const input = document.getElementById('ai-input');
                if (input) {
                    input.value = q;
                    sendAiMessage();
                }
            }


var aiChatHistory = [];

            async function sendAiMessage() {
                const input = document.getElementById('ai-input');
                const text = input.value.trim();
                if(!text) return;
                const box = document.getElementById('ai-chat-box');
                const sendBtn = document.getElementById('ai-send-btn');
                
                // Hiển thị tin nhắn người dùng
                box.innerHTML += `<div class="flex gap-2 justify-end"><div class="bg-teal-500 text-white p-2.5 rounded-2xl shadow-sm max-w-[85%] text-xs leading-relaxed">${text}</div></div>`;
                input.value = "";
                input.disabled = true;
                if(sendBtn) { sendBtn.disabled = true; sendBtn.innerHTML = '⏳'; }
                box.scrollTop = box.scrollHeight;

                // Ghi nhận lịch sử hội thoại
                aiChatHistory.push({ role: 'user', content: text });

                // Hiển thị typing indicator
                const typingId = 'typing-' + Date.now();
                box.innerHTML += `<div id="${typingId}" class="flex gap-2 items-end">
                    <div class="w-7 h-7 rounded-full overflow-hidden shrink-0 shadow-xs border border-teal-100">
                        <img src="./icons/piggy-bank.png" alt="AI" class="w-full h-full object-cover">
                    </div>
                    <div class="bg-white p-2.5 rounded-2xl border shadow-sm">
                        <span class="flex gap-1 items-center">
                            <span class="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style="animation-delay:0ms"></span>
                            <span class="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style="animation-delay:150ms"></span>
                            <span class="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style="animation-delay:300ms"></span>
                        </span>
                    </div>
                </div>`;
                box.scrollTop = box.scrollHeight;

                const sessionId = getOrCreateAiSessionId();

                try {
                    const res = await fetch('/ai-tro-ly', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                        body: JSON.stringify({
                            cau_hoi: text,
                            lich_su_chat: aiChatHistory.slice(-8),
                            ma_phien: currentAiSessionId
                        })
                    });
                    
                    // Xóa typing indicator
                    const typingEl = document.getElementById(typingId);
                    if(typingEl) typingEl.remove();
                    
                    if(res.ok) {
                        const d = await res.json();
                        const answerText = d.tra_loi || '';
                        aiChatHistory.push({ role: 'assistant', content: answerText });
                        if (aiChatHistory.length > 12) {
                            aiChatHistory = aiChatHistory.slice(-12);
                        }

                        const formatted = formatAIResponse(answerText);
                        box.innerHTML += `<div class="flex gap-2 items-end">
                            <div class="w-7 h-7 rounded-full overflow-hidden shrink-0 shadow-xs border border-teal-100">
                                <img src="./icons/piggy-bank.png" alt="AI" class="w-full h-full object-cover">
                            </div>
                            <div class="bg-white p-2.5 rounded-2xl border text-slate-700 shadow-sm max-w-[85%] text-xs leading-relaxed" style="word-break: break-word;">${formatted}</div>
                        </div>`;

                        // Tự động làm mới dữ liệu nền khi AI có thực hiện thay đổi số liệu
                        if (d.giao_dich_moi) {
                            setTimeout(() => {
                                if (typeof loadSummary === 'function') loadSummary();
                                if (typeof loadSavingsGoals === 'function') loadSavingsGoals();
                                if (typeof loadCategories === 'function') loadCategories();
                                if (typeof loadTransactions === 'function') loadTransactions();
                                if (typeof loadNotifications === 'function') loadNotifications();
                            }, 50);
                        }
                        updateAiLogBadge();
                    } else {
                        const err = await res.json().catch(() => ({}));
                        box.innerHTML += `<div class="flex gap-2 items-end">
                            <div class="w-7 h-7 bg-rose-500 text-white rounded-full flex items-center justify-center text-[10px] shrink-0">!</div>
                            <div class="bg-rose-50 p-2.5 rounded-2xl border border-rose-200 text-rose-700 shadow-sm max-w-[85%] text-xs">${err.detail || 'Đã có lỗi xảy ra, vui lòng thử lại!'}</div>
                        </div>`;
                    }
                } catch(e) {
                    const typingEl = document.getElementById(typingId);
                    if(typingEl) typingEl.remove();
                    box.innerHTML += `<div class="flex gap-2 items-end">
                        <div class="w-7 h-7 bg-rose-500 text-white rounded-full flex items-center justify-center text-[10px] shrink-0">!</div>
                        <div class="bg-rose-50 p-2.5 rounded-2xl border border-rose-200 text-rose-700 shadow-sm max-w-[85%] text-xs">Lỗi kết nối: ${e.message}</div>
                    </div>`;
                } finally {
                    input.disabled = false;
                    input.focus();
                    if(sendBtn) { sendBtn.disabled = false; sendBtn.innerHTML = 'Gửi'; }
                    box.scrollTop = box.scrollHeight;
                }
            }

            // =========================================================================
            // QUẢN LÝ NHẬT KÝ TƯƠNG TÁC AI THEO TỪNG NGÀY (AI INTERACTION LOGS)
            // =========================================================================

            var currentAiTab = 'chat';
            var aiLogSearchTimeout = null;

            function switchAiTab(tabName) {
                currentAiTab = tabName;
                const chatTabBtn = document.getElementById('ai-tab-btn-chat');
                const logsTabBtn = document.getElementById('ai-tab-btn-logs');
                const chatView = document.getElementById('ai-view-chat');
                const logsView = document.getElementById('ai-view-logs');

                if (tabName === 'chat') {
                    if (chatTabBtn) {
                        chatTabBtn.className = "flex-1 py-1.5 px-3 rounded-xl text-xs font-bold text-teal-700 bg-white shadow-xs transition flex items-center justify-center gap-1.5";
                    }
                    if (logsTabBtn) {
                        logsTabBtn.className = "flex-1 py-1.5 px-3 rounded-xl text-xs font-bold text-slate-500 hover:text-slate-700 transition flex items-center justify-center gap-1.5";
                    }
                    if (chatView) chatView.classList.remove('hidden');
                    if (logsView) logsView.classList.add('hidden');
                } else {
                    if (chatTabBtn) {
                        chatTabBtn.className = "flex-1 py-1.5 px-3 rounded-xl text-xs font-bold text-slate-500 hover:text-slate-700 transition flex items-center justify-center gap-1.5";
                    }
                    if (logsTabBtn) {
                        logsTabBtn.className = "flex-1 py-1.5 px-3 rounded-xl text-xs font-bold text-teal-700 bg-white shadow-xs transition flex items-center justify-center gap-1.5";
                    }
                    if (chatView) chatView.classList.add('hidden');
                    if (logsView) logsView.classList.remove('hidden');
                    loadAiLogs();
                }
            }

            async function updateAiLogBadge() {
                const badge = document.getElementById('ai-logs-badge');
                if (!badge) return;
                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    if (!authToken) return;
                    const res = await fetch('/api/ai/lich-su?limit=1', {
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        const total = (typeof data.tong_so_phien !== 'undefined') ? data.tong_so_phien : (data.tong_so || 0);
                        if (total > 0) {
                            badge.textContent = total > 99 ? '99+' : total;
                            badge.classList.remove('hidden');
                        } else {
                            badge.classList.add('hidden');
                        }
                    }
                } catch(e) {}
            }

            async function loadAiLogs(keyword) {
                const container = document.getElementById('ai-logs-container');
                if (!container) return;

                const searchInput = document.getElementById('ai-logs-search');
                const qSearch = typeof keyword !== 'undefined' ? keyword : (searchInput ? searchInput.value.trim() : '');

                container.innerHTML = `
                    <div class="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
                        <span class="animate-spin text-xl">⏳</span>
                        <p class="text-xs">Đang tải 10 nhật ký gần nhất...</p>
                    </div>
                `;

                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    let url = '/api/ai/lich-su?limit=10';
                    if (qSearch) url += `&tu_khoa=${encodeURIComponent(qSearch)}`;

                    const res = await fetch(url, {
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    });

                    if (!res.ok) {
                        container.innerHTML = `
                            <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-center text-xs">
                                Không thể tải nhật ký. Vui lòng thử lại sau.
                            </div>
                        `;
                        return;
                    }

                    const data = await res.json();
                    renderAiLogs(data, qSearch);
                    updateAiLogBadge();
                } catch(e) {
                    container.innerHTML = `
                        <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-center text-xs">
                            Lỗi kết nối: ${e.message}
                        </div>
                    `;
                }
            }

            var currentAiSessionsData = [];

            function escapeHtml(str) {
                if (!str) return '';
                return String(str)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
            }

            function renderAiLogs(data, activeKeyword) {
                const container = document.getElementById('ai-logs-container');
                if (!container) return;

                const sessions = data.cac_phien || [];
                currentAiSessionsData = sessions;

                if (sessions.length === 0) {
                    let msg = "Bạn chưa có nhật ký tương tác nào với AI.";
                    if (activeKeyword) msg = `Không tìm thấy nhật ký nào chứa từ khóa "${activeKeyword}".`;

                    container.innerHTML = `
                        <div class="py-12 flex flex-col items-center justify-center text-slate-400 gap-2 text-center px-4">
                            <span class="text-3xl">📜</span>
                            <p class="text-xs font-semibold text-slate-600">${msg}</p>
                            <p class="text-[11px] text-slate-400">Hãy chuyển sang tab "Trò chuyện" để bắt đầu phiên mới nhé! 😊</p>
                            <button onclick="startNewAiSession(false); switchAiTab('chat');" class="mt-2 px-3.5 py-1.5 bg-teal-50 hover:bg-teal-100 text-teal-700 text-xs font-bold rounded-xl transition border border-teal-200 flex items-center gap-1.5 cursor-pointer">
                                💬 Bắt đầu trò chuyện ngay
                            </button>
                        </div>
                    `;
                    return;
                }

                // Danh sách 10 nhật ký tương tác gần nhất
                let html = `<div class="space-y-2">`;

                sessions.forEach((s, sIdx) => {
                    const safeSessionId = (s.ma_phien || '').replace(/'/g, "\\'");
                    const firstLog = (s.nhat_ky && s.nhat_ky[0]) ? s.nhat_ky[0] : null;
                    const mainIcon = firstLog ? (firstLog.icon || '💬') : '💬';
                    const mainBadge = firstLog ? (firstLog.ten_hanh_dong || 'Trò chuyện') : 'Trò chuyện';
                    const mainColor = firstLog ? (firstLog.mau || 'teal') : 'teal';

                    const badgeColorMap = {
                        emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
                        amber: "bg-amber-50 text-amber-700 border-amber-200",
                        rose: "bg-rose-50 text-rose-700 border-rose-200",
                        sky: "bg-sky-50 text-sky-700 border-sky-200",
                        teal: "bg-teal-50 text-teal-700 border-teal-200",
                        indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
                        purple: "bg-purple-50 text-purple-700 border-purple-200",
                        cyan: "bg-cyan-50 text-cyan-700 border-cyan-200",
                        slate: "bg-slate-100 text-slate-700 border-slate-200"
                    };
                    const badgeClass = badgeColorMap[mainColor] || badgeColorMap.teal;
                    const safeTitle = escapeHtml(s.tieu_de_phien || 'Cuộc trò chuyện');

                    html += `
                        <div onclick="resumeAiSessionByIdx(${sIdx})"
                             class="group p-2.5 bg-white hover:bg-teal-50/50 active:bg-teal-100/40 border border-slate-200/90 hover:border-teal-300 rounded-2xl shadow-2xs hover:shadow-xs transition-all duration-150 cursor-pointer select-none flex items-center justify-between gap-2.5">
                            <!-- Left: Icon -->
                            <div class="w-8 h-8 rounded-xl bg-teal-50 group-hover:bg-teal-100 text-teal-600 border border-teal-200/80 flex items-center justify-center text-sm shrink-0 font-bold transition">
                                ${mainIcon}
                            </div>

                            <!-- Middle: Title & Meta -->
                            <div class="min-w-0 flex-1">
                                <div class="text-xs font-bold text-slate-800 group-hover:text-teal-700 truncate leading-snug transition" title="${safeTitle}">
                                    ${safeTitle}
                                </div>
                                <div class="text-[10px] text-slate-400 mt-1 flex items-center gap-1.5 whitespace-nowrap overflow-hidden text-ellipsis">
                                    <span>🕒 ${s.thoi_gian_hien_thi}</span>
                                    <span class="text-slate-300">•</span>
                                    <span class="px-1.5 py-0.2 rounded border text-[9px] font-bold ${badgeClass}">
                                        ${mainBadge}
                                    </span>
                                    ${s.so_luong > 1 ? `<span class="text-teal-600 font-semibold text-[9px]">(${s.so_luong} tin)</span>` : ''}
                                </div>
                            </div>

                            <!-- Right: Actions (Sleek Trash & Indicator) -->
                            <div class="flex items-center gap-1 shrink-0" onclick="event.stopPropagation()">
                                <button onclick="deleteAiSession('${safeSessionId}')"
                                        title="Xóa nhật ký này"
                                        class="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl text-xs transition cursor-pointer">
                                    🗑️
                                </button>
                                <span class="text-slate-300 group-hover:text-teal-500 group-hover:translate-x-0.5 transition-all text-xs font-bold pr-0.5">
                                    ›
                                </span>
                            </div>
                        </div>
                    `;
                });

                html += `</div>`;
                container.innerHTML = html;
            }

            function resumeAiSessionByIdx(sIdx) {
                if (!currentAiSessionsData || !currentAiSessionsData[sIdx]) return;
                const sessionData = currentAiSessionsData[sIdx];

                currentAiSessionId = sessionData.ma_phien;
                sessionStorage.setItem('current_ai_session_id', currentAiSessionId);

                // Khôi phục bộ nhớ đệm cho AI để tiếp tục hội thoại có ngữ cảnh
                aiChatHistory = [];

                const box = document.getElementById('ai-chat-box');
                if (box) {
                    let chatHtml = `
                        <div class="p-2 mb-2 bg-gradient-to-r from-teal-50 to-emerald-50/60 border border-teal-200/80 rounded-2xl flex items-center justify-between gap-2 shadow-2xs">
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="w-6 h-6 rounded-lg bg-teal-500 text-white flex items-center justify-center text-xs shrink-0 font-bold">💬</span>
                                <div class="min-w-0">
                                    <div class="text-[11px] font-bold text-teal-900 truncate">${escapeHtml(sessionData.tieu_de_phien || 'Cuộc trò chuyện')}</div>
                                    <div class="text-[9px] text-teal-600">🕒 Đang tiếp tục phiên: ${sessionData.thoi_gian_hien_thi}</div>
                                </div>
                            </div>
                            <button onclick="startNewAiSession(true)" title="Tạo cuộc trò chuyện mới hoàn toàn" class="px-2 py-1 bg-white hover:bg-teal-100 text-teal-700 border border-teal-200 text-[10px] font-bold rounded-lg transition shrink-0 cursor-pointer">
                                + Mới
                            </button>
                        </div>
                    `;

                    (sessionData.nhat_ky || []).forEach(log => {
                        aiChatHistory.push({ role: 'user', content: log.cau_hoi });
                        aiChatHistory.push({ role: 'assistant', content: log.tra_loi });

                        // Tin nhắn của người dùng
                        chatHtml += `
                            <div class="flex gap-2 justify-end">
                                <div class="bg-teal-500 text-white p-2.5 rounded-2xl shadow-sm max-w-[85%] text-xs leading-relaxed">
                                    ${escapeHtml(log.cau_hoi)}
                                </div>
                            </div>
                        `;

                        // Tin nhắn phản hồi của AI
                        const formatted = formatAIResponse(log.tra_loi);
                        chatHtml += `
                            <div class="flex gap-2 items-end">
                                <div class="w-7 h-7 rounded-full overflow-hidden shrink-0 shadow-xs border border-teal-100">
                                    <img src="./icons/piggy-bank.png" alt="AI" class="w-full h-full object-cover">
                                </div>
                                <div class="bg-white p-2.5 rounded-2xl border text-slate-700 shadow-sm max-w-[85%] text-xs leading-relaxed" style="word-break: break-word;">
                                    ${formatted}
                                </div>
                            </div>
                        `;
                    });

                    box.innerHTML = chatHtml;
                    box.scrollTop = box.scrollHeight;
                }

                // Chuyển sang tab Trò chuyện
                switchAiTab('chat');

                // Focus vào input chat
                const input = document.getElementById('ai-input');
                if (input) {
                    input.placeholder = `Nhập để tiếp tục trò chuyện...`;
                    input.focus();
                }

                if (typeof showCustomToast === 'function') {
                    showCustomToast("Đã mở lại cuộc trò chuyện! Bạn có thể tiếp tục nhắn tin với AI.", "info");
                }
            }

            function toggleAiSession(idx) {
                resumeAiSessionByIdx(idx);
            }

            async function deleteAiSession(maPhien) {
                if (!maPhien) return;
                if (!confirm("Bạn có chắc chắn muốn xóa bản ghi nhật ký này không?")) return;
                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    const res = await fetch(`/api/ai/lich-su?ma_phien=${encodeURIComponent(maPhien)}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    });
                    if (res.ok) {
                        if (currentAiSessionId === maPhien) {
                            startNewAiSession(false);
                        }
                        loadAiLogs();
                        updateAiLogBadge();
                        if (typeof showCustomToast === 'function') {
                            showCustomToast("Đã xóa nhật ký trò chuyện thành công! 🗑️", "info");
                        }
                    } else {
                        alert("Không thể xóa phiên trò chuyện.");
                    }
                } catch(e) {
                    alert("Lỗi kết nối: " + e.message);
                }
            }


            function reuseAiQuestion(q) {
                switchAiTab('chat');
                const input = document.getElementById('ai-input');
                if (input) {
                    input.value = q;
                    input.focus();
                }
            }

            async function deleteAiLog(maLog) {
                if (!confirm("Bạn có chắc muốn xóa bản ghi nhật ký tương tác này không?")) return;
                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    const res = await fetch(`/api/ai/lich-su/${maLog}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    });
                    if (res.ok) {
                        loadAiLogs();
                        updateAiLogBadge();
                    } else {
                        alert("Không thể xóa bản ghi nhật ký.");
                    }
                } catch(e) {
                    alert("Lỗi kết nối: " + e.message);
                }
            }

            async function clearAllAiLogs() {
                if (!confirm("Bạn có chắc chắn muốn xóa toàn bộ 10 nhật ký tương tác gần nhất với AI không?")) return;

                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    const res = await fetch('/api/ai/lich-su', {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    });

                    if (res.ok) {
                        loadAiLogs();
                        updateAiLogBadge();
                    } else {
                        alert("Không thể xóa nhật ký.");
                    }
                } catch(e) {
                    alert("Lỗi kết nối: " + e.message);
                }
            }

            function debounceAiLogSearch() {
                clearTimeout(aiLogSearchTimeout);
                aiLogSearchTimeout = setTimeout(() => {
                    loadAiLogs();
                }, 300);
            }

            function refreshAiLogs() {
                loadAiLogs();
            }

            // Gọi khởi tạo badge khi tải trang
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(updateAiLogBadge, 1500);
            });

        
