/**
 * MoneyMind - Mục Tiêu & Hũ Tiết Kiệm, Trích Tiền, Hoàn Tiền
 */
            function closeSavingsCongratsModal() {
                document.getElementById('savings-congrats-modal').classList.add('hidden');
                loadNotifications();
            }


            function openSavingsDepositModal(goalId) {
                document.getElementById('deposit-goal-id').value = goalId;
                const input = document.getElementById('deposit-amount-input');
                if (input) input.value = '';
                document.getElementById('savings-deposit-modal').classList.remove('hidden');
                setTimeout(() => {
                    if (input) input.focus();
                }, 100);
            }
            function closeSavingsDepositModal() {
                document.getElementById('savings-deposit-modal').classList.add('hidden');
            }

            async function submitSavingsDeposit() {
                const goalId = document.getElementById('deposit-goal-id').value;
                const inputEl = document.getElementById('deposit-amount-input');
                const rawVal = inputEl ? inputEl.value.replace(/[^0-9]/g, '') : '';
                const amount = parseFloat(rawVal);

                if(!amount || isNaN(amount) || amount < 1000) {
                    closeSavingsDepositModal();
                    return showCustomModal("Số tiền không hợp lệ", "Số tiền trích vào quỹ tiết kiệm tối thiểu là 1.000 đ!", "⚠️", () => openSavingsDepositModal(goalId));
                }

                // Kiểm tra số dư ví chính khả dụng
                const walletBalanceText = document.getElementById('so-du').innerText.replace(/[^\d]/g, '');
                const walletBalance = parseFloat(walletBalanceText) || 0;
                if(amount > walletBalance) {
                    closeSavingsDepositModal();
                    return showCustomModal(
                        "Số dư không đủ",
                        `Số dư ví chính không đủ để trích vào quỹ tiết kiệm! (Số dư khả dụng hiện tại: ${walletBalance.toLocaleString()} đ)`,
                        "⚠️",
                        () => openSavingsDepositModal(goalId)
                    );
                }

                let goal = allSavingsGoals.find(g => g.id == goalId);
                if(goal) {
                    let maxAllowed = goal.target_amount - goal.current_amount;
                    if(amount > maxAllowed) {
                        closeSavingsDepositModal();
                        return showCustomModal(
                            "Quá hạn mức",
                            `Số tiền trích vào vượt quá số tiền cần đạt còn lại (${maxAllowed.toLocaleString()} đ)!`,
                            "⚠️",
                            () => openSavingsDepositModal(goalId)
                        );
                    }
                }

                const res = await fetch(`/tiet-kiem/${goalId}/nop`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({amount})
                });

                if(res.ok) {
                    closeSavingsDepositModal();
                    await loadSavingsGoals();
                    await loadSummary();
                    await loadTransactions();
                    applyLookupFilter();

                    let updatedGoal = allSavingsGoals.find(g => g.id == goalId);
                    if(updatedGoal) {
                        let pct = Math.round((updatedGoal.current_amount / updatedGoal.target_amount) * 100);
                        if(pct >= 90) {
                            let title = "";
                            let msg = "";
                            let icon = "🎯";

                            if(pct >= 100) {
                                title = "🎉 Chúc Mừng Hoàn Thành Mục Tiêu!";
                                msg = `Chúc mừng bạn đã hoàn thành xuất sắc 100% mục tiêu "${updatedGoal.title}" (${updatedGoal.current_amount.toLocaleString()} đ / ${updatedGoal.target_amount.toLocaleString()} đ)! 🏆\n\nHãy tiếp tục duy trì phong độ và cố gắng hoàn thành thêm nhiều mục tiêu tài chính khác nhé!`;
                                icon = "🏆";
                            } else {
                                title = "🌟 Động Viên: Sắp Đạt Mục Tiêu!";
                                msg = `Cố lên! Hũ tiết kiệm "${updatedGoal.title}" của bạn đã đạt ${pct}% tiến độ (${updatedGoal.current_amount.toLocaleString()} đ / ${updatedGoal.target_amount.toLocaleString()} đ)!\n\nBạn sắp cán đích rồi, hãy tiếp tục duy trì và nỗ lực hoàn thành mục tiêu nhé! 💪`;
                                icon = "🌟";
                            }

                            // Lưu vào lịch sử thông báo
                            await recordNotification(title, msg);
                            await loadNotifications();

                            document.getElementById('savings-congrats-title').innerText = title;
                            document.getElementById('savings-congrats-text').innerText = msg;
                            document.getElementById('savings-congrats-icon').innerText = icon;
                            document.getElementById('savings-congrats-modal').classList.remove('hidden');
                            return;
                        }
                    }

                    await loadNotifications();
                    showCustomModal("Thành công", "Đã trích tiền vào quỹ tiết kiệm từ ví chính thành công!", "💰");
                } else {
                    let errData = await res.json().catch(() => ({}));
                    closeSavingsDepositModal();
                    showCustomModal("Số dư không đủ", errData.detail || "Số dư ví chính không đủ để trích tiền!", "⚠️", () => openSavingsDepositModal(goalId));
                }
            }

            // HÀM HỖ TRỢ XỬ LÝ NGÀY THÁNG ĐỊA PHƯƠNG & ĐỊNH DẠNG TIẾNG VIỆT CHUẨN

            function initSavingsPickers() {
                if (typeof flatpickr === 'undefined') return;

                const todayStr = getLocalDateString();

                const sgEl = document.getElementById('sg-deadline');
                if (sgEl && !createSavingsPicker) {
                    createSavingsPicker = flatpickr("#sg-deadline", {
                        locale: "vn",
                        dateFormat: "Y-m-d",
                        altInput: true,
                        altFormat: "d/m/Y",
                        altInputClass: "w-full p-3 border rounded-xl bg-slate-50 focus:outline-none focus:border-teal-500 cursor-pointer font-medium text-slate-700 pr-12",
                        minDate: "today",
                        allowInput: false,
                        onReady: function(selectedDates, dateStr, instance) {
                            if (instance.altInput) {
                                instance.altInput.placeholder = "Chọn hạn chót";
                            }
                        }
                    });
                }

                const editEl = document.getElementById('edit-savings-deadline');
                if (editEl && !editSavingsPicker) {
                    editSavingsPicker = flatpickr("#edit-savings-deadline", {
                        locale: "vn",
                        dateFormat: "Y-m-d",
                        altInput: true,
                        altFormat: "d/m/Y",
                        altInputClass: "w-full p-2.5 border rounded-xl bg-slate-50 focus:outline-none focus:border-teal-500 cursor-pointer font-medium text-slate-700 pr-12",
                        minDate: "today",
                        allowInput: false,
                        onReady: function(selectedDates, dateStr, instance) {
                            if (instance.altInput) {
                                instance.altInput.placeholder = "Chọn hạn chót";
                            }
                        }
                    });
                }
            }


            function clearCreateSavingsDeadline() {
                if (createSavingsPicker) createSavingsPicker.clear();
                const el = document.getElementById('sg-deadline');
                if (el) el.value = '';
            }


            function clearEditSavingsDeadline() {
                if (editSavingsPicker) editSavingsPicker.clear();
                const el = document.getElementById('edit-savings-deadline');
                if (el) el.value = '';
            }


            function openEditSavingsModal(id, title, target, deadline, currentAmount = 0) {
                document.getElementById('edit-savings-id').value = id;
                document.getElementById('edit-savings-title').value = title;
                document.getElementById('edit-savings-target').value = target;
                document.getElementById('edit-savings-current').value = currentAmount;
                const hintEl = document.getElementById('edit-savings-hint');
                if (hintEl) {
                    hintEl.innerText = `Số tiền hiện có: ${Number(currentAmount).toLocaleString()} đ (Mục tiêu mới phải ≥ ${Number(currentAmount).toLocaleString()} đ)`;
                }

                initSavingsPickers();

                const todayStr = getLocalDateString();
                const hintDateEl = document.getElementById('edit-savings-deadline-hint');

                if (editSavingsPicker) {
                    if (deadline) {
                        editSavingsPicker.setDate(deadline, true);
                        if (deadline < todayStr && hintDateEl) {
                            hintDateEl.className = "text-[11px] text-rose-600 mt-1 font-semibold";
                            hintDateEl.innerText = `⚠️ Hạn chót cũ (${formatVNDate(deadline)}) đã quá hạn! Vui lòng chọn lại hạn chót mới từ hôm nay trở đi.`;
                        } else if (hintDateEl) {
                            hintDateEl.innerText = '';
                        }
                    } else {
                        editSavingsPicker.clear();
                        if (hintDateEl) hintDateEl.innerText = '';
                    }
                } else {
                    const inputEl = document.getElementById('edit-savings-deadline');
                    if (inputEl) {
                        inputEl.value = deadline || '';
                        inputEl.setAttribute('min', todayStr);
                    }
                    if (hintDateEl) {
                        if (deadline && deadline < todayStr) {
                            hintDateEl.className = "text-[11px] text-rose-600 mt-1 font-semibold";
                            hintDateEl.innerText = `⚠️ Hạn chót cũ (${formatVNDate(deadline)}) đã quá hạn! Vui lòng chọn ngày từ hôm nay trở đi.`;
                        } else {
                            hintDateEl.innerText = '';
                        }
                    }
                }

                document.getElementById('edit-savings-modal').classList.remove('hidden');
            }
            function closeEditSavingsModal() {
                document.getElementById('edit-savings-modal').classList.add('hidden');
            }

            async function submitEditSavings() {
                const id = document.getElementById('edit-savings-id').value;
                const title = document.getElementById('edit-savings-title').value.trim();
                const target_amount = parseFloat(document.getElementById('edit-savings-target').value);
                const deadline = document.getElementById('edit-savings-deadline').value;
                const current_amount = parseFloat(document.getElementById('edit-savings-current').value) || 0;

                if(!title || !target_amount || isNaN(target_amount) || target_amount < 1000) return showCustomModal("Thiếu thông tin", "Số tiền mục tiêu tiết kiệm tối thiểu là 1.000 đ!", "⚠️");

                if(target_amount < current_amount) {
                    return showCustomModal("Số tiền không hợp lệ", `Số tiền mục tiêu mới không được nhỏ hơn số tiền đang có trong hũ (${current_amount.toLocaleString()} đ)!`, "⚠️");
                }

                const todayStr = getLocalDateString();
                if(deadline && deadline < todayStr) {
                    return showCustomModal("Hạn chót không hợp lệ", `Hạn chót phải là ngày hôm nay (${formatVNDate(todayStr)}) hoặc thời gian trong tương lai, không được đặt ngày trong quá khứ (${formatVNDate(deadline)})!`, "⚠️");
                }

                const res = await fetch(`/tiet-kiem/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({title, target_amount, deadline})
                });

                if(res.ok) {
                    const data = await res.json();
                    closeEditSavingsModal();
                    loadSavingsGoals();
                    loadSummary();
                    if(data.refunded > 0) {
                        showCustomModal("Hoàn tiền thành công", `Đã cập nhật lại quỹ tiết kiệm. Hệ thống đã hoàn trả phần dư ${data.refunded.toLocaleString()} đ về ví chính của bạn!`, "💰");
                    } else {
                        showCustomModal("Thành công", "Đã cập nhật mục tiêu tiết kiệm!", "✅");
                    }
                } else {
                    let err = await res.json().catch(() => ({}));
                    showCustomModal("Lỗi", err.detail || "Không thể cập nhật hũ tiết kiệm!", "❌");
                }
            }


            function openDeleteSavingsGoalModal(id) {
                const goal = allSavingsGoals.find(g => g.id == id);
                if(!goal) return;
                document.getElementById('del-sg-id').value = id;
                document.getElementById('del-sg-amount').innerText = (goal.current_amount || 0).toLocaleString() + " đ";
                document.getElementById('del-sg-msg').innerText = `Bạn có chắc chắn muốn xóa hũ tiết kiệm "${goal.title}" không?`;
                document.getElementById('delete-savings-modal').classList.remove('hidden');
            }

            function closeDeleteSavingsModal() {
                document.getElementById('delete-savings-modal').classList.add('hidden');
            }

            async function confirmDeleteSavingsGoalAction() {
                const id = document.getElementById('del-sg-id').value;
                const goal = allSavingsGoals.find(g => g.id == id);
                const title = goal ? goal.title : "hũ tiết kiệm";
                const amount = goal ? (goal.current_amount || 0) : 0;

                closeDeleteSavingsModal();

                const res = await fetch(`/tiet-kiem/${id}`, {
                    method: 'DELETE',
                    headers: {'Authorization': 'Bearer ' + token}
                });

                if(res.ok) {
                    await loadSavingsGoals();
                    await loadSummary();
                    await loadTransactions();
                    await loadNotifications();
                    showCustomModal(
                        "Hoàn tiền thành công",
                        `Đã xóa hũ tiết kiệm "${title}". Toàn bộ số tiền tích lũy ${amount > 0 ? amount.toLocaleString() + " đ " : ""}đã được hoàn lại về ví chính để bạn sử dụng cho các mục đích khác!`,
                        "💰"
                    );
                } else {
                    showCustomModal("Lỗi", "Không thể xóa hũ tiết kiệm!", "❌");
                }
            }


            async function loadSavingsGoals() {
                const res = await fetch('/tiet-kiem', {headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    allSavingsGoals = await res.json();
                    renderSavingsGoalsList();
                }
            }


            function renderSavingsGoalsList() {
                const container = document.getElementById('savings-goals-list');
                container.innerHTML = "";
                if(allSavingsGoals.length === 0) { container.innerHTML = `<p class="text-[10px] text-slate-400">Chưa có mục tiêu tiết kiệm.</p>`; return; }

                // Sắp xếp: hũ chưa hoàn thành (current < target) lên trước, hũ đã hoàn thành (current >= target) cho xuống dưới
                const sortedGoals = [...allSavingsGoals].sort((a, b) => {
                    const aCurr = Number(a.current_amount || 0);
                    const aTgt = Number(a.target_amount || a.so_tien_muc_tieu || 0);
                    const bCurr = Number(b.current_amount || 0);
                    const bTgt = Number(b.target_amount || b.so_tien_muc_tieu || 0);
                    const aCompleted = (aCurr >= aTgt && aTgt > 0);
                    const bCompleted = (bCurr >= bTgt && bTgt > 0);
                    if (aCompleted !== bCompleted) {
                        return aCompleted ? 1 : -1;
                    }
                    return (a.id || 0) - (b.id || 0);
                });

                sortedGoals.forEach(g => {
                    let current = Number(g.current_amount || 0);
                    let target = Number(g.target_amount || g.so_tien_muc_tieu || 0);
                    let pct = target > 0 ? Math.min(Math.round((current / target) * 100), 100) : 0;
                    let alertBadge = "";
                    let isCompleted = current >= target;
                    if(isCompleted) {
                        alertBadge = `<span class="bg-teal-100 text-teal-800 text-[9px] font-bold px-1.5 py-0.5 rounded ml-1">🏆 ĐÃ HOÀN THÀNH (100%)</span>`;
                    } else if(pct >= 90) {
                        alertBadge = `<span class="bg-amber-100 text-amber-800 text-[9px] font-bold px-1.5 py-0.5 rounded ml-1">⚡ SẮP HOÀN THÀNH (${pct}%)</span>`;
                    }

                    // Khi đạt 100% thì chuyển nút trích tiền thành nhãn 'Đã hoàn thành mục tiêu'.
                    // Chỉ khi sửa mục tiêu lên cao hơn thì mới quay về hiển thị nút trích tiền.
                    let actionButtonHtml = isCompleted
                        ? `<span class="px-2.5 py-1 bg-emerald-50 text-emerald-700 font-bold rounded-lg border border-emerald-200 inline-flex items-center gap-1 text-[10px]">🎉 Đã hoàn thành mục tiêu</span>`
                        : `<button onclick="openSavingsDepositModal(${g.id})" class="px-2.5 py-1 bg-teal-50 hover:bg-teal-100 text-teal-700 font-bold rounded-lg transition">Trích tiền vào ví</button>`;

                    const safeTitle = (g.title || '').replace(/'/g, "\\'");
                    const todayStr = getLocalDateString();
                    let deadlineHtml = '';
                    if (g.deadline) {
                        const isOverdue = g.deadline < todayStr;
                        if (isOverdue) {
                            deadlineHtml = `<span class="text-rose-600 font-semibold flex items-center gap-1">🕒 Hạn chót: ${formatVNDate(g.deadline)} <span class="bg-rose-100 text-rose-700 text-[9px] font-bold px-1.5 py-0.5 rounded">ĐÃ QUÁ HẠN</span></span>`;
                        } else {
                            deadlineHtml = `<span class="text-slate-500 font-medium">🕒 Hạn chót: ${formatVNDate(g.deadline)}</span>`;
                        }
                    } else {
                        deadlineHtml = `<span class="text-slate-400">🕒 Hạn chót: Không có</span>`;
                    }

                    container.innerHTML += `
                        <div class="bg-white p-3 rounded-2xl border text-xs space-y-2 shadow-sm">
                            <div class="flex justify-between items-center gap-2">
                                <div class="flex items-center gap-1.5 min-w-0">
                                    <span class="font-bold text-slate-800 text-xs truncate">🎯 ${g.title}</span>
                                    ${alertBadge}
                                </div>
                                <div class="flex items-center gap-1.5 shrink-0">
                                    <button onclick="openEditSavingsModal(${g.id}, '${safeTitle}', ${g.target_amount}, '${g.deadline || ''}', ${g.current_amount})" class="px-2 py-0.5 bg-teal-50 hover:bg-teal-100 text-teal-700 font-bold text-[10px] rounded-lg transition whitespace-nowrap">Sửa</button>
                                    <button onclick="openDeleteSavingsGoalModal(${g.id})" class="px-2 py-0.5 bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold text-[10px] rounded-lg transition whitespace-nowrap">Xóa</button>
                                </div>
                            </div>
                            <div class="flex justify-between items-center text-[11px] whitespace-nowrap">
                                <span class="font-bold text-teal-600">${g.current_amount.toLocaleString()} đ <span class="text-slate-400 font-normal text-[10px]">/ ${g.target_amount.toLocaleString()} đ</span></span>
                                <span class="font-bold text-slate-600 text-[10px]">${pct}%</span>
                            </div>
                            <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                                <div class="bg-teal-500 h-full transition-all duration-300" style="width: ${pct}%"></div>
                            </div>
                            <div class="flex justify-between items-center text-[10px] text-slate-400 gap-2">
                                <div class="min-w-0 truncate">${deadlineHtml}</div>
                                <div class="shrink-0 whitespace-nowrap">${actionButtonHtml}</div>
                            </div>
                        </div>`;
                });
            }


            async function createSavingsGoal() {
                const title = document.getElementById('sg-title').value.trim();
                const target = parseFloat(document.getElementById('sg-target').value);
                const deadline = document.getElementById('sg-deadline').value;
                if(!title || !target || isNaN(target) || target < 1000) return showCustomModal("Thiếu thông tin", "Số tiền mục tiêu tiết kiệm tối thiểu là 1.000 đ!", "⚠️");

                const todayStr = getLocalDateString();
                if(deadline && deadline < todayStr) {
                    return showCustomModal("Hạn chót không hợp lệ", `Hạn chót phải là ngày hôm nay (${formatVNDate(todayStr)}) hoặc thời gian trong tương lai, không được đặt ngày trong quá khứ (${formatVNDate(deadline)})!`, "⚠️");
                }

                const res = await fetch('/tiet-kiem', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({title, target_amount: target, deadline})
                });
                if(res.ok) { 
                    loadSavingsGoals(); 
                    document.getElementById('sg-title').value = "";
                    document.getElementById('sg-target').value = "";
                    clearCreateSavingsDeadline();
                    showCustomModal("Thành công", "Đã tạo mục tiêu tiết kiệm mới!", "✅"); 
                } else {
                    let err = await res.json().catch(() => ({}));
                    showCustomModal("Lỗi", err.detail || "Không thể tạo mục tiêu tiết kiệm!", "❌");
                }
            }

