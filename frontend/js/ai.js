/**
 * MoneyMind - Trợ Lý AI Tài Chính Thông Minh (Google Gemini Flash Engine)
 */
            function toggleAiModal() {
                const modal = document.getElementById('ai-modal');
                if (!modal) return;
                modal.classList.toggle('hidden');
                if (modal.classList.contains('hidden')) {
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

                try {
                    const res = await fetch('/ai-tro-ly', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                        body: JSON.stringify({
                            cau_hoi: text,
                            lich_su_chat: aiChatHistory.slice(-8)
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

                        // Tự động làm mới toàn bộ dữ liệu hệ thống (số dư ví, hũ tiết kiệm, danh mục, giao dịch, thông báo)
                        if (typeof loadSummary === 'function') loadSummary();
                        if (typeof loadSavingsGoals === 'function') loadSavingsGoals();
                        if (typeof loadCategories === 'function') loadCategories();
                        if (typeof loadTransactions === 'function') loadTransactions();
                        if (typeof loadNotifications === 'function') loadNotifications();
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
        
