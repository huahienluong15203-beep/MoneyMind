/**
 * MoneyMind - Quản Lý Ngân Sách Hũ & Cảnh Báo Hạn Mức
 */
            function closeBudgetWarningModal() {
                document.getElementById('budget-warning-modal').classList.add('hidden');
                loadNotifications();
            }


            async function checkLoginBudgetWarnings() {
                // Khi vừa vào giao diện: KHÔNG hiện popup đè màn hình người dùng.
                // Thay vào đó, hệ thống định kỳ 7h00 sáng đã ghi nhận thông báo chưa xem
                // và hiển thị biểu tượng thông báo mới trên chuông 🔔 để người dùng tự bấm vào kiểm tra.
                await loadNotifications();
            }


            function setBudgetModalType(type) {
                document.getElementById('modal-b-type').value = type;
                const btnChi = document.getElementById('modal-b-chi');
                const btnThu = document.getElementById('modal-b-thu');
                const limitWrapper = document.getElementById('modal-b-limit-wrapper');
                const label = document.getElementById('modal-b-limit-label');
                const input = document.getElementById('modal-b-limit');
                if (type === 'chi') {
                    btnChi.className = "flex-1 py-1.5 text-xs font-bold rounded-lg bg-white text-rose-600 shadow-sm transition";
                    btnThu.className = "flex-1 py-1.5 text-xs font-bold rounded-lg text-slate-600 transition";
                    limitWrapper.classList.remove('hidden');
                    if(label) label.innerText = "Hạn mức ngân sách cấp cho hũ (đ):";
                    if(input) input.placeholder = "Ví dụ: 2000000";
                } else {
                    btnThu.className = "flex-1 py-1.5 text-xs font-bold rounded-lg bg-white text-emerald-600 shadow-sm transition";
                    btnChi.className = "flex-1 py-1.5 text-xs font-bold rounded-lg text-slate-600 transition";
                    limitWrapper.classList.remove('hidden');
                    if(label) label.innerText = "Số tiền thu nhập cộng vào ví chính (đ):";
                    if(input) input.placeholder = "Ví dụ: 10000000";
                }
            }

            function openAddBudgetModal() {
                closePlusModal();
                setBudgetModalType('chi');
                document.getElementById('modal-b-name').value = '';
                document.getElementById('modal-b-limit').value = '';
                document.getElementById('add-budget-modal').classList.remove('hidden');
            }
            function closeAddBudgetModal() { document.getElementById('add-budget-modal').classList.add('hidden'); }


            async function submitBudgetModal() {
                const name = document.getElementById('modal-b-name').value.trim();
                const type = document.getElementById('modal-b-type').value;
                const rawAmount = document.getElementById('modal-b-limit').value.trim();
                const amount = parseFloat(rawAmount) || 0;
                if(!name) return showCustomModal("Thiếu tên", "Vui lòng nhập tên hũ / danh mục!", "⚠️");
                if(rawAmount && amount < 1000) return showCustomModal("Số tiền không hợp lệ", "Số tiền / hạn mức tối thiểu là 1.000 đ!", "⚠️");

                const res = await fetch('/danh-muc', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({name, type, budget_limit: amount, amount: amount})
                });

                if(res.ok) {
                    const catData = await res.json();
                    if (type === 'chi' && amount > 0) {
                        const nowYM = new Date().toISOString().slice(0, 7);
                        await fetch('/api/ngan-sach', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                            body: JSON.stringify({ma_dm: catData.ma_dm || catData.id, thang_nam: nowYM, han_muc: amount})
                        }).catch(() => {});
                    }

                    closeAddBudgetModal();
                    document.getElementById('modal-b-name').value = "";
                    document.getElementById('modal-b-limit').value = "";
                    setBudgetModalType('chi');
                    await loadCategories();
                    await loadSummary();
                    await loadTransactions();
                    if(type === 'thu') {
                        showCustomModal("Thành công", `Đã thiết lập danh mục thu "${name}" và cộng ${amount > 0 ? amount.toLocaleString() + ' đ' : ''} vào ví chính!`, "💰");
                    } else {
                        showCustomModal("Thành công", `Đã thiết lập hũ chi tiêu "${name}" và trích ${amount > 0 ? amount.toLocaleString() + ' đ' : ''} từ ví chính!`, "✅");
                    }
                } else {
                    const err = await res.json().catch(() => ({}));
                    showCustomModal("Không thể tạo danh mục", err.detail || "Không thể tạo danh mục/ngân sách!", "❌");
                }
            }


            function renderJarsProgressList() {
                const container = document.getElementById('jars-progress-list');
                container.innerHTML = "";
                const chiCats = allCategories.filter(c => c.type === 'chi' && c.name !== 'Tiết kiệm');
                if(chiCats.length === 0) { container.innerHTML = `<p class="text-[10px] text-slate-400">Chưa có hũ chi tiêu nào.</p>`; return; }

                let spentMap = {};
                allTransactions.forEach(t => { if(t.type === 'chi') spentMap[t.category_id] = (spentMap[t.category_id] || 0) + t.amount; });

                chiCats.forEach(c => {
                    let spent = spentMap[c.id] || 0;
                    let limit = parseFloat(c.budget_limit || c.han_muc || 0) || 0;
                    let remaining = limit > 0 ? (limit - spent) : (spent > 0 ? -spent : 0);
                    let percent = limit > 0 ? Math.round((spent / limit) * 100) : 0;
                    
                    let alertBadge = "";
                    let barColor = "bg-teal-500";

                    if(limit > 0 && percent >= 100) {
                        barColor = "bg-rose-500 animate-pulse";
                        alertBadge = `<span class="bg-rose-100 text-rose-600 text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">🚨 Quá hạn</span>`;
                    } else if(limit > 0 && percent >= 90) {
                        barColor = "bg-amber-500";
                        alertBadge = `<span class="bg-amber-100 text-amber-800 text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">⚠️ Sắp chạm (${percent}%)</span>`;
                    } else if(limit > 0 && percent >= 80) {
                        barColor = "bg-amber-400";
                        alertBadge = `<span class="bg-amber-100 text-amber-800 text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">⚠️ Cảnh báo (${percent}%)</span>`;
                    }

                    const safeName = (c.name || '').replace(/'/g, "\\'");
                    container.innerHTML += `
                        <div onclick="openQuickAddTxForCategory(${c.id}, '${safeName}')" class="bg-white p-3 rounded-2xl border border-slate-200/90 shadow-sm space-y-2 cursor-pointer hover:border-teal-500 hover:shadow-md transition">
                            <!-- Hàng 1: Tên hũ bên trái, Huy hiệu Cảnh báo bên phải (tách biệt hoàn toàn, không bao giờ đè lên nhau) -->
                            <div class="flex justify-between items-center gap-2">
                                <span class="font-bold text-slate-800 text-[13px] truncate">🏺 ${c.name}</span>
                                ${alertBadge}
                            </div>

                            <!-- Hàng 2: Số tiền còn lại bên trái, Hạn mức tổng bên phải -->
                            <div class="flex justify-between items-center text-xs">
                                <div class="whitespace-nowrap">
                                    <span class="text-[11px] text-slate-400 font-medium">Còn:</span> 
                                    <strong class="${remaining < 0 ? 'text-rose-500 font-extrabold' : 'text-teal-600 font-bold'} text-xs ml-0.5">${remaining.toLocaleString()} đ</strong>
                                </div>
                                <div class="whitespace-nowrap text-right text-[10px] text-slate-400">
                                    Hạn mức: <span class="font-semibold text-slate-600">${limit.toLocaleString()} đ</span>
                                </div>
                            </div>
                            <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                                <div class="${barColor} h-full transition-all duration-300" style="width: ${Math.min(percent, 100)}%"></div>
                            </div>
                            <div class="flex justify-between items-center text-[10px] text-slate-400 pt-0.5">
                                <span class="whitespace-nowrap">Đã chi: <strong class="text-slate-600">${spent.toLocaleString()} đ</strong> (${percent}%)</span>
                                <span onclick="event.stopPropagation(); openQuickAddTxForCategory(${c.id}, '${safeName}')" class="text-teal-600 font-semibold whitespace-nowrap hover:text-teal-800 transition flex items-center gap-0.5">
                                    <span>+ Chi tiêu</span>
                                    <span>➔</span>
                                </span>
                            </div>
                        </div>`;
                });
            }

