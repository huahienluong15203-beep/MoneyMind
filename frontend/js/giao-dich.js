/**
 * MoneyMind - Giao Dịch (Thu & Chi), Thêm Nhanh, Chi Tiêu Hũ
 */
            function openPlusModal() { document.getElementById('plus-action-modal').classList.remove('hidden'); }
            function closePlusModal() { document.getElementById('plus-action-modal').classList.add('hidden'); }


            function setModalTxType(type) {
                document.getElementById('modal-tx-type').value = type;
                const btnChi = document.getElementById('btn-tx-type-chi');
                const btnThu = document.getElementById('btn-tx-type-thu');
                if (type === 'chi') {
                    btnChi.className = "py-2 rounded-lg bg-rose-500 text-white shadow-sm transition flex items-center justify-center gap-1";
                    btnThu.className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";
                } else {
                    btnThu.className = "py-2 rounded-lg bg-emerald-500 text-white shadow-sm transition flex items-center justify-center gap-1";
                    btnChi.className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";
                }
                updateModalCategoryDropdown(type);
            }


            function selectModalCategory(catId) {
                const hiddenInput = document.getElementById('modal-tx-category');
                if (hiddenInput) hiddenInput.value = catId;
                
                const allChips = document.querySelectorAll('.category-chip-btn');
                allChips.forEach(btn => {
                    const isSelected = btn.getAttribute('data-cat-id') == catId;
                    if (isSelected) {
                        btn.className = "category-chip-btn py-2.5 px-3 rounded-xl border-2 border-teal-500 bg-teal-50 text-teal-800 font-bold shadow-xs flex items-center justify-between transition-all scale-[1.02]";
                        const check = btn.querySelector('.chip-check');
                        if (check) check.classList.remove('hidden');
                    } else {
                        btn.className = "category-chip-btn py-2.5 px-3 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold transition-all flex items-center justify-between";
                        const check = btn.querySelector('.chip-check');
                        if (check) check.classList.add('hidden');
                    }
                });
            }

            function updateModalCategoryDropdown(type, selectedId = null) {
                const container = document.getElementById('modal-tx-category-chips');
                const hiddenInput = document.getElementById('modal-tx-category');
                if (!container || !hiddenInput) return;
                
                container.innerHTML = '';
                const filtered = allCategories.filter(c => c.type === type && c.name.toLowerCase() !== 'tiết kiệm' && (!c.ten_dm || c.ten_dm.toLowerCase() !== 'tiết kiệm'));
                
                if (filtered.length === 0) {
                    hiddenInput.value = '';
                    container.innerHTML = `<div class="col-span-2 py-3 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">Chưa có danh mục ${type === 'chi' ? 'chi' : 'thu'} nào</div>`;
                    return;
                }
                
                let activeId = selectedId;
                if (!activeId || !filtered.some(c => c.id == activeId)) {
                    activeId = filtered[0].id;
                }
                hiddenInput.value = activeId;
                
                filtered.forEach(c => {
                    const isSelected = (c.id == activeId);
                    const icon = type === 'chi' ? '🏺' : '💰';
                    const chipBtn = document.createElement('button');
                    chipBtn.type = 'button';
                    chipBtn.setAttribute('data-cat-id', c.id);
                    chipBtn.onclick = () => selectModalCategory(c.id);
                    
                    if (isSelected) {
                        chipBtn.className = "category-chip-btn py-2.5 px-3 rounded-xl border-2 border-teal-500 bg-teal-50 text-teal-800 font-bold shadow-xs flex items-center justify-between transition-all scale-[1.02]";
                    } else {
                        chipBtn.className = "category-chip-btn py-2.5 px-3 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold transition-all flex items-center justify-between";
                    }
                    
                    chipBtn.innerHTML = `
                        <span class="flex items-center gap-1.5 truncate">
                            <span class="text-sm shrink-0">${icon}</span>
                            <span class="truncate text-[11px]">${c.name}</span>
                        </span>
                        <span class="chip-check text-teal-600 text-xs font-bold ${isSelected ? '' : 'hidden'}">✓</span>
                    `;
                    container.appendChild(chipBtn);
                });
            }


            function openAddTransactionModal() {
                closePlusModal();
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('modal-tx-date').value = today;
                document.getElementById('modal-tx-amount').value = '';
                document.getElementById('modal-tx-note').value = '';
                setModalTxType('chi');
                document.getElementById('add-tx-modal').classList.remove('hidden');
            }
            function closeAddTransactionModal() { document.getElementById('add-tx-modal').classList.add('hidden'); }


            function openQuickAddTxForCategory(catId, catName) {
                selectedCategoryId = catId;
                
                // Thiết lập loại giao dịch là chi
                document.getElementById('modal-tx-type').value = 'chi';
                const btnChi = document.getElementById('btn-tx-type-chi');
                const btnThu = document.getElementById('btn-tx-type-thu');
                if (btnChi) btnChi.className = "py-2 rounded-lg bg-rose-500 text-white shadow-sm transition flex items-center justify-center gap-1";
                if (btnThu) btnThu.className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";

                // Cập nhật danh mục và chọn đúng hũ
                updateModalCategoryDropdown('chi', catId);
                const select = document.getElementById('modal-tx-category');
                if (select) select.value = catId;

                // Reset ô nhập và gán ngày mặc định
                document.getElementById('modal-tx-amount').value = "";
                document.getElementById('modal-tx-note').value = "";
                const today = new Date().toISOString().split('T')[0];
                const dateEl = document.getElementById('modal-tx-date');
                if (dateEl && !dateEl.value) dateEl.value = today;

                document.getElementById('add-tx-modal').classList.remove('hidden');
                setTimeout(() => {
                    const amt = document.getElementById('modal-tx-amount');
                    if (amt) amt.focus();
                }, 100);
            }

            let currentSection = 'quan-ly';


            async function loadSummary() {
                const res = await fetch('/thong-ke', {headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    const d = await res.json();
                    document.getElementById('so-du').innerText = d.so_du.toLocaleString() + " đ";
                    document.getElementById('tong-thu').innerText = d.tong_thu.toLocaleString() + " đ";
                    document.getElementById('tong-chi').innerText = d.tong_chi.toLocaleString() + " đ";
                }
            }


            async function loadTransactions() {
                const res = await fetch('/giao-dich', {headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    allTransactions = await res.json();
                    applyLookupFilter();
                    renderJarsProgressList();
                }
            }


            async function submitModalTransaction() {
                const type = document.getElementById('modal-tx-type').value;
                const amount = parseFloat(document.getElementById('modal-tx-amount').value);
                const category_id = parseInt(document.getElementById('modal-tx-category').value);
                const note = document.getElementById('modal-tx-note').value.trim();
                const txDate = document.getElementById('modal-tx-date').value;

                if (!category_id || isNaN(category_id)) return showCustomModal("Thiếu danh mục", "Vui lòng chọn danh mục phù hợp!", "⚠️");
                if (!amount || isNaN(amount) || amount < 1000) return showCustomModal("Số tiền không hợp lệ", "Số tiền giao dịch tối thiểu là 1.000 đ!", "⚠️");
                
                const res = await fetch('/giao-dich', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({amount, type, category_id, note, date: txDate ? txDate + 'T12:00:00' : new Date().toISOString()})
                });

                if(res.ok) {
                    const data = await res.json();
                    closeAddTransactionModal();
                    document.getElementById('modal-tx-amount').value = "";
                    document.getElementById('modal-tx-note').value = "";
                    await loadSummary();
                    await loadTransactions();
                    await loadCategories();
                    if (typeof updateReportSummary === 'function') updateReportSummary();

                    // Kiểm tra cảnh báo chi tiêu từ 90% trở lên hoặc vượt hạn mức
                    let targetCat = allCategories.find(c => c.id == category_id);
                    let limit = 0;
                    if (targetCat && targetCat.budget_limit > 0) {
                        limit = targetCat.budget_limit;
                    } else if (data.canh_bao && data.canh_bao.han_muc > 0) {
                        limit = data.canh_bao.han_muc;
                    }

                    if (type === 'chi' && limit > 0) {
                        let spent = allTransactions.filter(t => (t.category_id == category_id || t.ma_dm == category_id) && (t.type === 'chi' || t.loai_gd === 'chi')).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
                        if (data.canh_bao && data.canh_bao.so_tien_da_chi > spent) {
                            spent = data.canh_bao.so_tien_da_chi;
                        }

                        let pct = Math.round((spent / limit) * 100);
                        if (pct >= 90 || (data.canh_bao && (data.canh_bao.co_canh_bao || data.canh_bao.vuot_ngan_sach))) {
                            let catName = targetCat ? targetCat.name : (data.canh_bao && data.canh_bao.ten_dm ? data.canh_bao.ten_dm : "khoản chi");
                            let title = (pct >= 100 || (data.canh_bao && data.canh_bao.vuot_ngan_sach)) ? `🚨 CẢNH BÁO: HŨ "${catName}" VƯỢT HẠN MỨC (${pct}%)!` : `⚠️ CẢNH BÁO: HŨ "${catName}" ĐÃ CHI TIÊU ĐẠT ${pct}% HẠN MỨC!`;
                            let icon = (pct >= 100 || (data.canh_bao && data.canh_bao.vuot_ngan_sach)) ? "🛑" : "⚠️";
                            let msg = (pct >= 100 || (data.canh_bao && data.canh_bao.vuot_ngan_sach))
                                ? `✅ Đã ghi nhận giao dịch thành công!\n\n🚨 CẢNH BÁO: Hũ "${catName}" đã chi tiêu vượt quá hạn mức (${spent.toLocaleString()} đ / ${limit.toLocaleString()} đ, đạt ${pct}%).\n\n⚠️ YÊU CẦU: Bạn đã vượt quá hạn mức cho phép, vui lòng chi tiêu ít lại và dừng các khoản chi tiêu không cần thiết!`
                                : `✅ Đã ghi nhận giao dịch thành công!\n\n⚠️ CẢNH BÁO: Hũ "${catName}" đã chi tiêu đạt ${pct}% hạn mức (${spent.toLocaleString()} đ / ${limit.toLocaleString()} đ).\n\n⚠️ YÊU CẦU: Bạn đang sắp chạm hạn mức cho phép, vui lòng chi tiêu ít lại và tiết kiệm chi tiêu!`;

                            // Tải lại thông báo (đã được backend ghi nhận duy nhất 1 bản ghi cảnh báo)
                            await loadNotifications();

                            document.getElementById('budget-warning-title').innerText = title;
                            document.getElementById('budget-warning-text').innerText = msg;
                            document.getElementById('budget-warning-icon').innerText = icon;
                            document.getElementById('budget-warning-modal').classList.remove('hidden');
                            return;
                        }
                    }

                    showCustomModal("Thành công", type === 'chi' ? "Đã ghi nhận khoản chi vào hũ thành công!" : "Đã cộng thu nhập vào ví chính thành công!", "✅");
                } else {
                    closeAddTransactionModal();
                    let errData = await res.json().catch(() => ({}));
                    let errText = errData.detail || "Không thể thực hiện giao dịch!";
                    showCustomModal("Lỗi giao dịch", errText, "❌");
                }
            }

