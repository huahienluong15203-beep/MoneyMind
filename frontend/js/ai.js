/**
 * MoneyMind - Trợ Lý AI Tài Chính Thông Minh (Google Gemini Flash Engine)
 */
            function toggleAiModal() { document.getElementById('ai-modal').classList.toggle('hidden'); }

            function formatAIResponse(text) {
                // Render markdown-like formatting
                return text
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/🎯|💰|📊|✅|❌|⚠️|🌟|💡|📈|📉|🏆/g, '<span style="display:inline-block">$&</span>')
                    .replace(/•/g, '<span class="text-teal-500 font-bold">•</span>')
                    .replace(/\n/g, '<br>')
                    .replace(/\|(.*?)\|/g, '<span class="font-mono text-xs bg-slate-100 px-1 rounded">$1</span>');
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
        
