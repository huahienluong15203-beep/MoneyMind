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
                const now = new Date();
                const today = typeof getLocalDateString === 'function' ? getLocalDateString() : `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
                const curTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
                const dateEl = document.getElementById('modal-tx-date');
                const timeEl = document.getElementById('modal-tx-time');
                if (dateEl) dateEl.value = today;
                if (timeEl) timeEl.value = curTime;
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

                // Reset ô nhập và gán ngày hôm nay mặc định
                document.getElementById('modal-tx-amount').value = "";
                document.getElementById('modal-tx-note').value = "";
                const now = new Date();
                const today = typeof getLocalDateString === 'function' ? getLocalDateString() : `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
                const curTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
                const dateEl = document.getElementById('modal-tx-date');
                const timeEl = document.getElementById('modal-tx-time');
                if (dateEl) dateEl.value = today;
                if (timeEl) timeEl.value = curTime;

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
                    if(document.getElementById('so-du')) document.getElementById('so-du').innerText = d.so_du.toLocaleString() + " đ";
                    if(document.getElementById('tong-thu')) document.getElementById('tong-thu').innerText = d.tong_thu.toLocaleString() + " đ";
                    if(document.getElementById('tong-chi')) document.getElementById('tong-chi').innerText = d.tong_chi.toLocaleString() + " đ";
                    // Cập nhật tổng trong hũ sau khi có data
                    updateTongTrongHu();
                }
            }


            // Tính lại tổng trong hũ trực tiếp từ frontend data
            // Đảm bảo nhất quán với renderJarsProgressList()
            function updateTongTrongHu() {
                const el = document.getElementById('tong-trong-hu');
                if (!el) return;

                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

                // Chỉ lấy danh mục chi (không bao gồm Tiết kiệm)
                const chiCats = (allCategories || []).filter(c => (c.type === 'chi' || c.loai_dm === 'chi') && c.name !== 'Tiết kiệm');

                let tongConLai = 0;
                chiCats.forEach(c => {
                    const catId = c.id || c.ma_dm;
                    // Tính hạn mức hiệu dụng (giống với renderJarsProgressList)
                    let limit = parseFloat(c.budget_limit !== undefined ? c.budget_limit : (c.han_muc || 0)) || 0;
                    let rollover = parseFloat(c.so_du_chuyen_sang || 0) || 0;
                    let effectiveLimit = limit > 0 ? limit : (rollover > 0 ? rollover : 0);

                    if (effectiveLimit <= 0) return; // Chưa đặt hạn mức, bỏ qua

                    // Tính chi tíeu trong tháng hiện tại
                    const spent = (allTransactions || []).reduce((sum, t) => {
                        const tDate = t.date || t.ngay_gd || '';
                        const isChi = (t.type === 'chi' || t.loai_gd === 'chi');
                        const isCat = (t.category_id == catId || t.ma_dm == catId);
                        const isThisMonth = tDate.startsWith(currentYM);
                        // Bỏ qua giao dịch tiết kiệm
                        const note = (t.note || t.ghi_chu || '').toLowerCase();
                        const isSavings = note.includes('tiết kiệm') || note.includes('trích quỹ') || note.includes('mục tiêu');
                        if (isChi && isCat && isThisMonth && !isSavings) {
                            return sum + (t.amount !== undefined ? t.amount : (t.so_tien || 0));
                        }
                        return sum;
                    }, 0);

                    const remaining = Math.max(0, effectiveLimit - spent);
                    tongConLai += remaining;
                });

                el.innerText = tongConLai.toLocaleString('vi-VN') + ' đ';
            }


            async function loadTransactions() {
                const res = await fetch('/giao-dich', {headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    allTransactions = await res.json();
                    applyLookupFilter();
                    renderJarsProgressList();
                    updateTongTrongHu(); // Cập nhật tổng trong hũ sau khi có giao dịch mới
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
                
                const now = new Date();
                const curH = String(now.getHours()).padStart(2, '0');
                const curM = String(now.getMinutes()).padStart(2, '0');
                const curS = String(now.getSeconds()).padStart(2, '0');
                const timePart = `${curH}:${curM}:${curS}`;
                const todayStr = typeof getLocalDateString === 'function' ? getLocalDateString() : `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
                const chosenDate = txDate || todayStr;
                const fullDateTime = `${chosenDate}T${timePart}`;

                const res = await fetch('/giao-dich', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({amount, type, category_id, note, date: fullDateTime, ngay_gd: fullDateTime})
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

                    if (type === 'chi') {
                        const now = new Date();
                        const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                        let spent = allTransactions.filter(t => {
                            const tDate = t.date || t.ngay_gd || '';
                            return (t.category_id == category_id || t.ma_dm == category_id) && 
                                   (t.type === 'chi' || t.loai_gd === 'chi') &&
                                   tDate.startsWith(currentYM);
                        }).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
                        if (data.canh_bao && data.canh_bao.so_tien_da_chi > spent) {
                            spent = data.canh_bao.so_tien_da_chi;
                        }

                        let pct = limit > 0 ? Math.round((spent / limit) * 100) : (spent > 0 ? 100 : 0);
                        let isVuot = (limit > 0 && spent > limit) || (limit <= 0 && spent > 0) || (data.canh_bao && data.canh_bao.vuot_ngan_sach);
                        let isSapCham = limit > 0 && pct >= 90;

                        const topupBtn = document.getElementById('budget-warning-topup-btn');
                        const closeBtn = document.getElementById('budget-warning-close-btn');

                        if (isVuot || isSapCham || (data.canh_bao && data.canh_bao.co_canh_bao)) {
                            let catName = targetCat ? targetCat.name : (data.canh_bao && data.canh_bao.ten_dm ? data.canh_bao.ten_dm : "khoản chi");
                            let title = isVuot 
                                ? (limit > 0 ? `🚨 CẢNH BÁO: HŨ "${catName}" VƯỢT HẠN MỨC (${pct}%)!` : `🚨 CẢNH BÁO: HŨ "${catName}" VƯỢT HẠN MỨC!`)
                                : `⚠️ CẢNH BÁO: HŨ "${catName}" ĐÃ CHI TIÊU ĐẠT ${pct}% HẠN MỨC!`;
                            let icon = isVuot ? "🛑" : "⚠️";
                            let msg = isVuot
                                ? (limit > 0 
                                    ? `✅ Đã ghi nhận giao dịch thành công!\n\n🚨 CẢNH BÁO: Hũ "${catName}" đã chi tiêu vượt quá hạn mức (${spent.toLocaleString()} đ / ${limit.toLocaleString()} đ, đạt ${pct}%).\n\n⚠️ YÊU CẦU: Bạn đã vượt quá hạn mức cho phép, vui lòng chi tiêu ít lại và dừng các khoản chi tiêu không cần thiết!`
                                    : `✅ Đã ghi nhận giao dịch thành công!\n\n🚨 CẢNH BÁO: Hũ "${catName}" chưa được cấp hạn mức trong tháng này nhưng đã phát sinh chi tiêu ${spent.toLocaleString()} đ.\n\n💡 Vui lòng vào tab Ngân Sách Hũ → bấm vào hũ → "Thêm hạn mức" để thiết lập hạn mức cho hũ này!`)
                                : `✅ Đã ghi nhận giao dịch thành công!\n\n⚠️ CẢNH BÁO: Hũ "${catName}" đã chi tiêu đạt ${pct}% hạn mức (${spent.toLocaleString()} đ / ${limit.toLocaleString()} đ).\n\n⚠️ YÊU CẦU: Bạn đang sắp chạm hạn mức cho phép, vui lòng chi tiêu ít lại và tiết kiệm chi tiêu!`;

                            await loadNotifications();

                            document.getElementById('budget-warning-title').innerText = title;
                            document.getElementById('budget-warning-text').innerText = msg;
                            document.getElementById('budget-warning-icon').innerText = icon;
                            if (topupBtn) {
                                topupBtn.classList.remove('hidden');
                                topupBtn.innerText = "+ Thêm hạn mức";
                                const editCatId = targetCat ? (targetCat.id || targetCat.ma_dm) : category_id;
                                const editCatName = targetCat ? targetCat.name : catName;
                                const safeName = (editCatName || '').replace(/'/g, "\\'");
                                topupBtn.onclick = function() {
                                    closeBudgetWarningModal();
                                    if (typeof openEditCategoryModal === 'function') {
                                        openEditCategoryModal(editCatId, safeName, 'chi', limit > 0 ? limit : spent);
                                    }
                                };
                            }
                            if (closeBtn) closeBtn.innerText = "Đã hiểu";
                            document.getElementById('budget-warning-modal').classList.remove('hidden');
                            return;
                        }
                    }

                    // --- Giao dịch THU: hỏi người dùng có muốn bổ sung vào hũ không ---
                    if (type === 'thu') {
                        let canConfirm = false;
                        let shortage_list = [];
                        let total_shortage = 0;
                        let available_wallet = 0;

                        if (data.phan_bo_hu && data.phan_bo_hu.can_confirm) {
                            const kiem_tra = data.phan_bo_hu.kiem_tra || {};
                            shortage_list = kiem_tra.shortage_list || [];
                            total_shortage = kiem_tra.total_shortage || 0;
                            available_wallet = kiem_tra.available_wallet || 0;
                            canConfirm = shortage_list.length > 0;
                        } else {
                            // Fallback kiểm tra trực tiếp
                            try {
                                let chkRes = await fetch('/api/ngan-sach/kiem-tra-hu-thieu', {headers: {'Authorization': 'Bearer ' + token}});
                                if (!chkRes.ok) chkRes = await fetch('/ngan-sach/kiem-tra-hu-thieu', {headers: {'Authorization': 'Bearer ' + token}});
                                if (chkRes.ok) {
                                    const chkData = await chkRes.json();
                                    if (chkData.co_hu_thieu && chkData.shortage_list && chkData.shortage_list.length > 0) {
                                        shortage_list = chkData.shortage_list;
                                        total_shortage = chkData.total_shortage || 0;
                                        available_wallet = chkData.available_wallet || 0;
                                        canConfirm = true;
                                    }
                                }
                            } catch(e) {}
                        }

                        if (canConfirm && shortage_list.length > 0) {
                            let shortageLines = shortage_list.map(h =>
                                `  • Hũ "${h.name}": đang có ${(h.current_limit||0).toLocaleString()} đ / định mức ${(h.target_limit||0).toLocaleString()} đ (thiếu ${(h.shortage||0).toLocaleString()} đ)`
                            ).join('\n');

                            let msgText = `💰 Đã nạp +${amount.toLocaleString()} đ vào ví chính thành công.\n\n` +
                                `📋 Hiện tại có các hũ chi tiêu chưa đủ hạn mức của tháng trước:\n${shortageLines}\n\n` +
                                `💡 Tổng tiền còn thiếu: ${total_shortage.toLocaleString()} đ | Số dư ví chính khả dụng: ${available_wallet.toLocaleString()} đ\n\n` +
                                `Bạn có muốn hệ thống tự động trừ từ ví chính để bổ sung cho các danh mục còn thiếu cho đúng theo hạn mức của tháng trước không?\n\n` +
                                `• Bấm "Có, bổ sung ngay" → tự trừ từ ví chính cấp đủ cho các hũ\n` +
                                `• Bấm "Không, để sau" → giữ nguyên tiền trong ví chính`;

                            await loadNotifications();
                            showTopupConfirmModal(msgText, shortage_list, amount);
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

            // ====== POPUP XÁC NHẬN BỔ SUNG VÀO HŨ ======
            function showTopupConfirmModal(msgText, shortage_list, thu_amount) {
                const modal = document.getElementById('topup-confirm-modal');
                if (!modal) {
                    if (confirm(msgText.replace(/\n/g, '\n'))) {
                        doTopupJars();
                    }
                    return;
                }
                const msgEl = document.getElementById('topup-confirm-msg');
                if (msgEl) msgEl.innerText = msgText;
                modal.classList.remove('hidden');
                window._pendingTopupShortage = shortage_list;
            }

            function closeTopupConfirmModal() {
                const modal = document.getElementById('topup-confirm-modal');
                if (modal) modal.classList.add('hidden');
                window._pendingTopupShortage = null;
                showCustomModal("Đã giữ nguyên ví chính", "Số tiền vừa nạp được giữ nguyên trong ví chính. Bạn có thể tự điều chỉnh và bổ sung hạn mức cho từng hũ bất kỳ lúc nào trong tab Ngân Sách Hũ.", "💰");
            }

            async function doTopupJars() {
                const modal = document.getElementById('topup-confirm-modal');
                if (modal) modal.classList.add('hidden');
                window._pendingTopupShortage = null;
                try {
                    let res = await fetch('/api/ngan-sach/bo-sung-hu', {
                        method: 'POST',
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                    if (!res.ok) {
                        res = await fetch('/ngan-sach/bo-sung-hu', {
                            method: 'POST',
                            headers: {'Authorization': 'Bearer ' + token}
                        });
                    }
                    if (res.ok) {
                        const data = await res.json();
                        await loadSummary();
                        await loadTransactions();
                        await loadCategories();
                        await loadNotifications();
                        const fully = data.fully_topped || [];
                        const partial = data.partially_topped || [];
                        let resultMsg = '✅ Đã bổ sung hạn mức từ ví chính vào các hũ!\n\n';
                        if (fully.length > 0) {
                            resultMsg += '✅ Hũ đã đủ hạn mức:\n';
                            fully.forEach(f => {
                                resultMsg += `  • Hũ "${f.name}": +${(f.topup||0).toLocaleString()} đ → ${(f.current||0).toLocaleString()}/${(f.target||0).toLocaleString()} đ (100%)\n`;
                            });
                        }
                        const stillShort = partial.filter(p => (p.shortage||0) > 0);
                        if (stillShort.length > 0) {
                            resultMsg += '\n⚠️ Hũ vẫn còn thiếu (ví chính hết tiền giữa chừng):\n';
                            stillShort.forEach(p => {
                                const pct = p.target > 0 ? Math.round((p.current/p.target)*100) : 0;
                                resultMsg += `  • Hũ "${p.name}": +${(p.topup||0).toLocaleString()} đ → ${(p.current||0).toLocaleString()}/${(p.target||0).toLocaleString()} đ (${pct}%) — còn thiếu ${(p.shortage||0).toLocaleString()} đ\n`;
                            });
                        }
                        showCustomModal('💧 Bổ sung hũ thành công', resultMsg, '✅');
                    } else {
                        showCustomModal('Lỗi', 'Không thể bổ sung vào các hũ!', '❌');
                    }
                } catch(e) {
                    showCustomModal('Lỗi', 'Không thể kết nối server!', '❌');
                }
            }



