/**
 * MoneyMind - Trợ Lý AI Tài Chính Thông Minh (Google Gemini Flash Engine)
 */
var currentAiSessionId = null;
var aiSessionEnded = true; // Ban đầu chưa có phiên đang mở

function startNewAiSession(showAlert = false) {
    currentAiSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    aiSessionEnded = false;
    aiChatHistory = [];

    const box = document.getElementById('ai-chat-box');
    if (box) {
        box.innerHTML = `
            <div class="flex gap-2">
                <div class="w-7 h-7 bg-teal-500 text-white rounded-full flex items-center justify-center font-bold text-[10px] shrink-0">AI</div>
                <div class="bg-white p-3 rounded-2xl border border-slate-100 text-slate-700 shadow-sm leading-relaxed">
                    Xin chào! Tôi là Trợ lý AI tài chính cá nhân MoneyMind. Bạn có thể trò chuyện tự nhiên để <strong>ghi nhanh chi tiêu</strong> (ví dụ: <em>"Ăn bánh mì 20k"</em>, <em>"Đổ xăng 50k"</em>, <em>"Nộp 500k vào hũ du lịch"</em>) hoặc hỏi đáp, phân tích ngân sách tài chính cá nhân. Bạn cần mình giúp gì nào? 😊
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
        // Mở modal: nếu vừa thoát ra vào lại -> tự động tính là 1 phiên mới!
        if (aiSessionEnded || !currentAiSessionId) {
            startNewAiSession(false);
        }
        updateAiLogBadge();
        if (currentAiTab === 'logs') {
            loadAiLogs();
        }
    } else {
        // Thoát khỏi modal -> đánh dấu phiên kết thúc
        aiSessionEnded = true;
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
                    <div class="w-7 h-7 bg-teal-500 text-white rounded-full flex items-center justify-center font-bold text-[10px] shrink-0">AI</div>
                    <div class="bg-white p-2.5 rounded-2xl border shadow-sm">
                        <span class="flex gap-1 items-center">
                            <span class="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style="animation-delay:0ms"></span>
                            <span class="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style="animation-delay:150ms"></span>
                            <span class="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style="animation-delay:300ms"></span>
                        </span>
                    </div>
                </div>`;
                box.scrollTop = box.scrollHeight;

                if (!currentAiSessionId || aiSessionEnded) {
                    currentAiSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
                    aiSessionEnded = false;
                }

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
                            <div class="w-7 h-7 bg-teal-500 text-white rounded-full flex items-center justify-center font-bold text-[10px] shrink-0">AI</div>
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

            async function loadAiLogs(dateFilter, keyword) {
                const container = document.getElementById('ai-logs-container');
                if (!container) return;

                const searchInput = document.getElementById('ai-logs-search');
                const dateInput = document.getElementById('ai-logs-date-filter');

                const qDate = typeof dateFilter !== 'undefined' ? dateFilter : (dateInput ? dateInput.value : '');
                const qSearch = typeof keyword !== 'undefined' ? keyword : (searchInput ? searchInput.value.trim() : '');

                container.innerHTML = `
                    <div class="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
                        <span class="animate-spin text-xl">⏳</span>
                        <p class="text-xs">Đang tải nhật ký các phiên trò chuyện...</p>
                    </div>
                `;

                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    let url = '/api/ai/lich-su?limit=200';
                    if (qDate) url += `&ngay=${encodeURIComponent(qDate)}`;
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
                    renderAiLogs(data, qDate, qSearch);
                    updateAiLogBadge();
                } catch(e) {
                    container.innerHTML = `
                        <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-center text-xs">
                            Lỗi kết nối: ${e.message}
                        </div>
                    `;
                }
            }

            function renderAiLogs(data, activeDate, activeKeyword) {
                const container = document.getElementById('ai-logs-container');
                if (!container) return;

                const sessions = data.cac_phien || [];
                if (sessions.length === 0) {
                    let msg = "Bạn chưa có nhật ký tương tác nào với AI.";
                    if (activeDate) msg = `Không có phiên trò chuyện nào trong ngày ${activeDate}.`;
                    if (activeKeyword) msg = `Không tìm thấy phiên trò chuyện nào chứa từ khóa "${activeKeyword}".`;

                    container.innerHTML = `
                        <div class="py-12 flex flex-col items-center justify-center text-slate-400 gap-2 text-center px-4">
                            <span class="text-3xl">📜</span>
                            <p class="text-xs font-semibold text-slate-600">${msg}</p>
                            <p class="text-[11px] text-slate-400">Hãy chuyển sang tab "Trò chuyện" để bắt đầu phiên mới nhé! 😊</p>
                            <button onclick="startNewAiSession(false); switchAiTab('chat');" class="mt-2 px-3.5 py-1.5 bg-teal-50 hover:bg-teal-100 text-teal-700 text-xs font-bold rounded-xl transition border border-teal-200 flex items-center gap-1.5">
                                💬 Bắt đầu trò chuyện ngay
                            </button>
                        </div>
                    `;
                    return;
                }

                let html = '';
                sessions.forEach((s, sIdx) => {
                    const isExpanded = sIdx < 2; // Mở sẵn 2 phiên gần nhất để người dùng tiện xem ngay
                    const safeSessionId = (s.ma_phien || '').replace(/'/g, "\\'");

                    html += `
                        <div class="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden transition mb-3">
                            <!-- HEADER PHIÊN TRÒ CHUYỆN -->
                            <div class="p-3 bg-gradient-to-r from-slate-50/90 to-white flex items-center justify-between border-b border-slate-100 cursor-pointer select-none hover:bg-slate-50 transition" onclick="toggleAiSession(${sIdx})">
                                <div class="flex items-center gap-2 min-w-0 flex-1 pr-2">
                                    <span class="w-7 h-7 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center text-xs shrink-0 font-bold">💬</span>
                                    <div class="min-w-0 flex-1">
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            <span class="text-xs font-bold text-slate-800 truncate max-w-[220px]" title="${s.tieu_de_phien}">${s.tieu_de_phien}</span>
                                            <span class="px-2 py-0.5 bg-teal-50 text-teal-700 font-bold rounded-full text-[10px] shrink-0 border border-teal-100">
                                                ${s.so_luong} tương tác
                                            </span>
                                        </div>
                                        <div class="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1">
                                            <span>🕒 ${s.thoi_gian_hien_thi}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center gap-1 shrink-0" onclick="event.stopPropagation()">
                                    <button onclick="deleteAiSession('${safeSessionId}')" title="Xóa toàn bộ phiên này" class="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg text-xs transition">
                                        🗑️
                                    </button>
                                    <button onclick="toggleAiSession(${sIdx})" title="Thu gọn / Mở rộng" class="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg text-xs transition font-bold" id="ai-session-chevron-${sIdx}">
                                        ${isExpanded ? '▲' : '▼'}
                                    </button>
                                </div>
                            </div>

                            <!-- NỘI DUNG CÁC TIN NHẮN TRONG PHIÊN -->
                            <div id="ai-session-body-${sIdx}" class="p-3 space-y-2.5 bg-slate-50/30 ${isExpanded ? '' : 'hidden'}">
                    `;

                    (s.nhat_ky || []).forEach(log => {
                        const formattedAnswer = formatAIResponse(log.tra_loi);
                        const safeQuestion = (log.cau_hoi || '').replace(/"/g, '&quot;').replace(/'/g, "\\'");
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
                        const badgeClass = badgeColorMap[log.mau] || badgeColorMap.teal;

                        html += `
                            <div class="bg-white border border-slate-200/90 rounded-2xl p-2.5 shadow-2xs hover:border-teal-300 transition space-y-2">
                                <!-- HEADER THẺ TƯƠNG TÁC -->
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center gap-1.5">
                                        <span class="px-2 py-0.5 rounded-lg border text-[10px] font-bold ${badgeClass} flex items-center gap-1">
                                            <span>${log.icon}</span>
                                            <span>${log.ten_hanh_dong}</span>
                                        </span>
                                        <span class="text-[10px] text-slate-400 font-medium">🕒 ${log.thoi_gian}</span>
                                    </div>
                                    <div class="flex items-center gap-1">
                                        <button onclick="reuseAiQuestion('${safeQuestion}')" title="Hỏi lại câu này trong chat" class="p-1 text-teal-600 hover:bg-teal-50 rounded-lg text-xs transition">
                                            💬
                                        </button>
                                        <button onclick="deleteAiLog(${log.ma_log})" title="Xóa bản ghi này" class="p-1 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg text-xs transition">
                                            ✕
                                        </button>
                                    </div>
                                </div>

                                <!-- CÂU HỎI CỦA NGƯỜI DÙNG -->
                                <div class="bg-slate-50 border border-slate-100 rounded-xl p-2 flex items-start gap-2">
                                    <span class="text-xs shrink-0 mt-0.5">👤</span>
                                    <div class="text-[11px] font-semibold text-slate-800 leading-snug break-words flex-1">
                                        "${log.cau_hoi}"
                                    </div>
                                </div>

                                <!-- PHẢN HỒI CỦA AI -->
                                <div class="bg-teal-50/30 border border-teal-100/60 rounded-xl p-2.5 flex items-start gap-2">
                                    <span class="text-xs shrink-0 mt-0.5">🤖</span>
                                    <div class="text-[11px] text-slate-700 leading-relaxed break-words flex-1">
                                        ${formattedAnswer}
                                    </div>
                                </div>
                            </div>
                        `;
                    });

                    html += `
                            </div>
                        </div>
                    `;
                });

                container.innerHTML = html;
            }

            function toggleAiSession(idx) {
                const body = document.getElementById(`ai-session-body-${idx}`);
                const chevron = document.getElementById(`ai-session-chevron-${idx}`);
                if (body) {
                    body.classList.toggle('hidden');
                    if (chevron) {
                        chevron.textContent = body.classList.contains('hidden') ? '▼' : '▲';
                    }
                }
            }

            async function deleteAiSession(maPhien) {
                if (!maPhien) return;
                if (!confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử trong phiên trò chuyện này không?")) return;
                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    const res = await fetch(`/api/ai/lich-su?ma_phien=${encodeURIComponent(maPhien)}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    });
                    if (res.ok) {
                        loadAiLogs();
                        updateAiLogBadge();
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
                const dateInput = document.getElementById('ai-logs-date-filter');
                const qDate = dateInput ? dateInput.value : '';

                const confirmMsg = qDate
                    ? `Bạn có chắc muốn xóa tất cả các phiên tương tác trong ngày ${qDate} không?`
                    : "Bạn có chắc chắn muốn xóa TOÀN BỘ nhật ký các phiên trò chuyện với AI không?";

                if (!confirm(confirmMsg)) return;

                try {
                    const authToken = typeof token !== 'undefined' ? token : (localStorage.getItem('token') || '');
                    let url = '/api/ai/lich-su';
                    if (qDate) url += `?ngay=${encodeURIComponent(qDate)}`;

                    const res = await fetch(url, {
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

            function setAiLogQuickFilter(type) {
                const dateInput = document.getElementById('ai-logs-date-filter');
                const pAll = document.getElementById('pill-filter-all');
                const pToday = document.getElementById('pill-filter-today');
                const pYesterday = document.getElementById('pill-filter-yesterday');

                // Reset pills styling
                [pAll, pToday, pYesterday].forEach(p => {
                    if (p) {
                        p.className = "px-2.5 py-1 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded-lg transition";
                    }
                });

                const now = new Date();
                const formatYMD = d => {
                    const y = d.getFullYear();
                    const m = String(d.getMonth() + 1).padStart(2, '0');
                    const day = String(d.getDate()).padStart(2, '0');
                    return `${y}-${m}-${day}`;
                };

                if (type === 'all') {
                    if (dateInput) dateInput.value = '';
                    if (pAll) pAll.className = "px-2.5 py-1 bg-teal-50 text-teal-700 font-bold rounded-lg border border-teal-200 transition";
                    loadAiLogs('');
                } else if (type === 'today') {
                    const todayStr = formatYMD(now);
                    if (dateInput) dateInput.value = todayStr;
                    if (pToday) pToday.className = "px-2.5 py-1 bg-teal-50 text-teal-700 font-bold rounded-lg border border-teal-200 transition";
                    loadAiLogs(todayStr);
                } else if (type === 'yesterday') {
                    const yDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                    const yStr = formatYMD(yDate);
                    if (dateInput) dateInput.value = yStr;
                    if (pYesterday) pYesterday.className = "px-2.5 py-1 bg-teal-50 text-teal-700 font-bold rounded-lg border border-teal-200 transition";
                    loadAiLogs(yStr);
                }
            }

            function filterAiLogsByDate() {
                const dateInput = document.getElementById('ai-logs-date-filter');
                loadAiLogs(dateInput ? dateInput.value : '');
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

        
