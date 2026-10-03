/**
 * MoneyMind - Quản Lý Ngân Sách Hũ & Cảnh Báo Hạn Mức
 */
            function closeBudgetWarningModal() {
                const modal = document.getElementById('budget-warning-modal');
                if (modal) modal.classList.add('hidden');
                const topupBtn = document.getElementById('budget-warning-topup-btn');
                if (topupBtn) {
                    topupBtn.classList.add('hidden');
                    topupBtn.onclick = null;
                }
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
                        if (amount > 0) {
                            // Kiểm tra các hũ còn thiếu hạn mức tháng này để hỏi người dùng
                            try {
                                let chkRes = await fetch('/api/ngan-sach/kiem-tra-hu-thieu', {headers: {'Authorization': 'Bearer ' + token}});
                                if (!chkRes.ok) chkRes = await fetch('/ngan-sach/kiem-tra-hu-thieu', {headers: {'Authorization': 'Bearer ' + token}});
                                if (chkRes.ok) {
                                    const chkData = await chkRes.json();
                                    if (chkData.co_hu_thieu && chkData.shortage_list && chkData.shortage_list.length > 0) {
                                        let shortageLines = chkData.shortage_list.map(h =>
                                            `  • Hũ "${h.name}": đang có ${(h.current_limit||0).toLocaleString()} đ / định mức ${(h.target_limit||0).toLocaleString()} đ (thiếu ${(h.shortage||0).toLocaleString()} đ)`
                                        ).join('\n');
                                        let msgText = `💰 Đã cộng +${amount.toLocaleString()} đ vào ví chính từ danh mục thu "${name}".\n\n` +
                                            `📋 Phát hiện các hũ chi tiêu tháng này chưa đủ định mức của tháng trước:\n${shortageLines}\n\n` +
                                            `💡 Tổng thiếu: ${(chkData.total_shortage||0).toLocaleString()} đ | Ví chính khả dụng: ${(chkData.available_wallet||0).toLocaleString()} đ\n\n` +
                                            `Bạn có muốn hệ thống tự động trừ từ ví chính để bổ sung cho các hũ còn thiếu theo đúng hạn mức tháng trước không?`;
                                        if (typeof showTopupConfirmModal === 'function') {
                                            showTopupConfirmModal(msgText, chkData.shortage_list, amount);
                                            return;
                                        }
                                    }
                                }
                            } catch(e) {}
                        }
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
                if(!container) return;
                container.innerHTML = "";
                const chiCats = allCategories.filter(c => (c.type === 'chi' || c.loai_dm === 'chi') && c.name !== 'Tiết kiệm');
                if(chiCats.length === 0) { container.innerHTML = `<p class="text-[10px] text-slate-400">Chưa có hũ chi tiêu nào.</p>`; return; }

                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                const titleHeader = document.getElementById('jars-month-title');
                if (titleHeader) {
                    titleHeader.innerHTML = `🏺 Hũ Ngân Sách (Tháng ${now.getMonth() + 1}/${now.getFullYear()})`;
                }

                let spentMap = {};
                allTransactions.forEach(t => {
                    const tDate = t.date || t.ngay_gd || '';
                    const isChi = (t.type === 'chi' || t.loai_gd === 'chi');
                    if (isChi && tDate.startsWith(currentYM)) {
                        const catId = t.category_id || t.ma_dm;
                        const amt = t.amount !== undefined ? t.amount : (t.so_tien || 0);
                        spentMap[catId] = (spentMap[catId] || 0) + amt;
                    }
                });

                chiCats.forEach(c => {
                    const catId = c.id || c.ma_dm;
                    let spent = spentMap[catId] || 0;
                    let limit = parseFloat(c.budget_limit || 0) || 0;
                    let rollover = parseFloat(c.so_du_chuyen_sang || 0) || 0;
                    let capMoi = parseFloat(c.han_muc_cap_moi || 0) || 0;
                    let daCap = (c.da_cap_han_muc === true) || (limit > 0) || (capMoi > 0);
                    let effectiveLimit = limit > 0 ? limit : (rollover > 0 ? rollover : 0);
                    let remaining = effectiveLimit > 0 ? (effectiveLimit - spent) : 0;
                    let percent = effectiveLimit > 0 ? Math.round((spent / effectiveLimit) * 100) : 0;
                    
                    let alertBadge = "";
                    let barColor = "bg-teal-500";
                    let isOverBudget = effectiveLimit > 0 && remaining < 0;

                    if (isOverBudget) {
                        barColor = "bg-rose-500 animate-pulse";
                        alertBadge = `<span class="bg-rose-100 text-rose-600 text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">🚨 Quá hạn ${effectiveLimit > 0 ? `(${percent}%)` : ''}</span>`;
                    } else if (effectiveLimit > 0 && percent >= 90) {
                        barColor = "bg-amber-500";
                        alertBadge = `<span class="bg-amber-100 text-amber-800 text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">⚠️ Sắp chạm (${percent}%)</span>`;
                    } else if (effectiveLimit > 0 && percent >= 80) {
                        barColor = "bg-amber-400";
                        alertBadge = `<span class="bg-amber-100 text-amber-800 text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">⚠️ Cảnh báo (${percent}%)</span>`;
                    } else if (effectiveLimit <= 0) {
                        barColor = spent > 0 ? "bg-teal-400" : "bg-slate-200";
                        alertBadge = `<span class="bg-slate-100 text-slate-500 text-[9px] font-medium px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap">Chưa đặt hạn mức</span>`;
                    }

                    const safeName = (c.name || '').replace(/'/g, "\\'");
                    const suggestLimit = c.han_muc_goc || c.han_muc || effectiveLimit || 0;

                    // Chỉ khi thực sự có hạn mức và bị quá mức mới hiển thị thông báo vượt hạn mức
                    let overBudgetNoticeHtml = "";
                    if (isOverBudget) {
                        const overAmount = Math.abs(remaining);
                        overBudgetNoticeHtml = `
                            <div class="flex items-center justify-between bg-rose-50/90 border border-rose-200/90 px-2.5 py-1.5 rounded-xl text-xs gap-2" onclick="event.stopPropagation()">
                                <div class="flex items-center gap-1.5 text-rose-700 text-[11px] font-semibold truncate">
                                    <span>⚠️</span>
                                    <span class="truncate">Vượt hạn mức <strong>${overAmount.toLocaleString()} đ</strong></span>
                                </div>
                                <button type="button" onclick="event.stopPropagation(); if(typeof openEditCategoryModal === 'function') openEditCategoryModal(${catId}, '${safeName}', 'chi', ${suggestLimit});" class="text-[10px] font-bold bg-rose-600 hover:bg-rose-700 text-white px-2 py-0.5 rounded-lg shadow-2xs whitespace-nowrap transition cursor-pointer shrink-0">
                                    + Thêm hạn mức
                                </button>
                            </div>
                        `;
                    }

                    const progressWidth = effectiveLimit > 0 ? Math.min(percent, 100) : 0;

                    container.innerHTML += `
                        <div onclick="openQuickAddTxForCategory(${catId}, '${safeName}')" class="bg-white p-3 rounded-2xl border border-slate-200/90 shadow-2xs space-y-2 cursor-pointer hover:border-teal-500 hover:shadow-md transition">
                            <!-- Hàng 1: Tên hũ & Huy hiệu -->
                            <div class="flex justify-between items-center gap-2">
                                <span class="font-bold text-slate-800 text-[13px] truncate">🏺 ${c.name}</span>
                                ${alertBadge}
                            </div>

                            ${overBudgetNoticeHtml}

                            <!-- Hàng 2: Số tiền còn lại/quá mức & Hạn mức -->
                            <div class="flex justify-between items-center text-xs">
                                <div class="text-[11px] truncate">
                                    <span class="${isOverBudget ? 'text-rose-500 font-semibold' : 'text-slate-400 font-medium'}">${isOverBudget ? 'Quá mức:' : 'Còn lại:'}</span>
                                    <strong class="${isOverBudget ? 'text-rose-600 font-extrabold' : 'text-teal-600 font-bold'} ml-0.5">${isOverBudget ? '-' + Math.abs(remaining).toLocaleString() + ' đ' : (effectiveLimit > 0 ? remaining.toLocaleString() + ' đ' : '0 đ')}</strong>
                                </div>
                                <div class="text-[11px] text-slate-400 shrink-0 text-right">
                                    Hạn mức: <strong class="text-slate-600">${effectiveLimit > 0 ? effectiveLimit.toLocaleString() + ' đ' : 'Chưa đặt'}</strong>
                                </div>
                            </div>

                            <!-- Hàng 3: Thanh tiến độ -->
                            <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                                <div class="${barColor} h-full transition-all duration-300" style="width: ${progressWidth}%"></div>
                            </div>

                            <!-- Hàng 4: Đã chi & Nút chi tiêu -->
                            <div class="flex justify-between items-center text-[10px] text-slate-400 pt-0.5">
                                <span class="truncate">Đã chi: <strong class="text-slate-600">${spent.toLocaleString()} đ</strong> ${effectiveLimit > 0 ? `(${percent}%)` : ''}</span>
                                <span onclick="event.stopPropagation(); openQuickAddTxForCategory(${catId}, '${safeName}')" class="text-teal-600 font-semibold whitespace-nowrap hover:text-teal-800 transition flex items-center gap-0.5 shrink-0">
                                    <span>+ Chi tiêu</span>
                                    <span>➔</span>
                                </span>
                            </div>
                        </div>`;
                });
            }

            function goToRolloverLookup() {
                if (typeof switchSection === 'function') {
                    switchSection('lich-su');
                }
                setTimeout(() => {
                    if (typeof setLookupType === 'function') {
                        setLookupType('refund');
                    }
                }, 50);
            }

