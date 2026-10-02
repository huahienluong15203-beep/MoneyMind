/**
 * MoneyMind - Quản Lý Danh Mục Thu & Chi, Hoàn Hạn Mức
 */
            function closeConfirmDeleteCatModal() {
                document.getElementById('confirm-delete-cat-modal').classList.add('hidden');
                selectedCategoryToDelete = null;
            }


            function setCategoryTabType(type) {
                const typeInput = document.getElementById('cat-type-input');
                if (typeInput) typeInput.value = type;
                const bChi = document.getElementById('cat-btn-chi');
                const bThu = document.getElementById('cat-btn-thu');
                const wrapper = document.getElementById('cat-limit-wrapper');
                const label = document.getElementById('cat-limit-label');
                const input = document.getElementById('cat-limit-input');
                const errEl = document.getElementById('cat-limit-error');

                if (errEl) errEl.classList.add('hidden');
                if (input) input.classList.remove('border-rose-400');

                if(type === 'chi') {
                    if (bChi) bChi.className = "flex-1 py-1.5 text-xs font-bold rounded-lg bg-white text-rose-600 shadow-sm transition cursor-pointer";
                    if (bThu) bThu.className = "flex-1 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:text-slate-900 transition cursor-pointer";
                    if (wrapper) wrapper.style.display = 'block';
                    if(label) label.innerText = "Số tiền cấp cho hũ (đ):";
                    if(input) {
                        input.placeholder = "Tối thiểu 1.000 đ (Ví dụ: 2000000)";
                        input.setAttribute('min', '1000');
                    }
                } else {
                    if (bThu) bThu.className = "flex-1 py-1.5 text-xs font-bold rounded-lg bg-white text-emerald-600 shadow-sm transition cursor-pointer";
                    if (bChi) bChi.className = "flex-1 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:text-slate-900 transition cursor-pointer";
                    if (wrapper) wrapper.style.display = 'block';
                    if(label) label.innerText = "Số tiền thu nhập cộng vào ví chính (đ):";
                    if(input) {
                        input.placeholder = "Ví dụ: 10000000 (để trống nếu chưa có)";
                        input.removeAttribute('min');
                    }
                }
                if (typeof handleCatLimitInput === 'function' && input) {
                    handleCatLimitInput(input);
                }
            }


            function setModalEditCategoryType(type) {
                const input = document.getElementById('modal-edit-type');
                if (input) input.value = type;
                const bChi = document.getElementById('modal-edit-btn-chi');
                const bThu = document.getElementById('modal-edit-btn-thu');
                if (bChi && bThu) {
                    if (type === 'chi') {
                        bChi.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-white text-rose-600 shadow-sm transition cursor-pointer";
                        bThu.className = "flex-1 py-2 text-xs font-bold rounded-lg text-slate-600 hover:text-slate-900 transition cursor-pointer";
                    } else {
                        bThu.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-white text-emerald-600 shadow-sm transition cursor-pointer";
                        bChi.className = "flex-1 py-2 text-xs font-bold rounded-lg text-slate-600 hover:text-slate-900 transition cursor-pointer";
                    }
                }
                toggleModalEditLimit();
                const limitInput = document.getElementById('modal-edit-limit');
                handleEditLimitChange(limitInput ? limitInput.value : '');
            }

            function toggleModalEditLimit() {
                const type = document.getElementById('modal-edit-type')?.value;
                const wrapper = document.getElementById('modal-edit-limit-wrapper');
                const hintEl = document.getElementById('modal-edit-spent-hint');
                if(type === 'thu') {
                    if (wrapper) wrapper.classList.add('hidden');
                    if (hintEl) hintEl.classList.add('hidden');
                } else {
                    if (wrapper) wrapper.classList.remove('hidden');
                    if (hintEl) hintEl.classList.remove('hidden');
                }
            }


            function handleEditLimitChange(val) {
                const type = document.getElementById('modal-edit-type')?.value;
                const diffBox = document.getElementById('modal-edit-diff-box');
                const submitBtn = document.getElementById('btn-submit-edit-cat');
                if (!diffBox || type !== 'chi') {
                    if (diffBox) diffBox.classList.add('hidden');
                    return;
                }
                const oldLimit = parseFloat(document.getElementById('modal-edit-old-limit')?.value) || 0;
                const rawVal = String(val || '').replace(/[^0-9]/g, '');
                const newLimit = parseFloat(rawVal) || 0;
                const curBalance = parseFloat((document.getElementById('so-du')?.innerText || '0').replace(/[^\d]/g, '')) || 0;
                const diff = newLimit - oldLimit;

                // Chỉ hiển thị cảnh báo đỏ khi số tiền trích thêm vượt quá số dư ví chính
                if (diff > 0 && diff > curBalance) {
                    diffBox.classList.remove('hidden');
                    diffBox.className = "mt-1.5 p-2 rounded-xl text-[11px] font-medium bg-rose-50 border border-rose-200 text-rose-700 leading-snug";
                    diffBox.innerHTML = `⚠️ <strong>Cần trích thêm: +${diff.toLocaleString()} đ</strong>.<br><span class="text-rose-600 font-bold">Số dư ví (${curBalance.toLocaleString()} đ) không đủ để trích!</span>`;
                    if (submitBtn) submitBtn.disabled = true;
                } else {
                    diffBox.classList.add('hidden');
                    if (submitBtn) submitBtn.disabled = false;
                }
            }

            function openEditCategoryModal(id, name, type, limit) {
                // Tính toán chính xác tổng số tiền đã chi tiêu trong tháng hiện tại của danh mục này
                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                let spent = allTransactions
                    .filter(t => {
                        const tDate = t.date || t.ngay_gd || '';
                        return (t.category_id == id || t.ma_dm == id || t.cat_id == id) && 
                               (t.type === 'chi' || t.loai_gd === 'chi') &&
                               tDate.startsWith(currentYM);
                    })
                    .reduce((s, t) => s + (t.amount !== undefined ? t.amount : (t.so_tien || 0)), 0);

                document.getElementById('modal-edit-cat-id').value = id;
                document.getElementById('modal-edit-name').value = name;
                setModalEditCategoryType(type || 'chi');
                const oldLimitVal = (limit && limit > 0) ? limit : 0;
                const oldLimitInput = document.getElementById('modal-edit-old-limit');
                if (oldLimitInput) oldLimitInput.value = oldLimitVal;

                const curLimitValEl = document.getElementById('modal-edit-current-limit-val');
                if (curLimitValEl) curLimitValEl.innerText = oldLimitVal > 0 ? `${oldLimitVal.toLocaleString()} đ` : 'Chưa đặt';

                const limitInput = document.getElementById('modal-edit-limit');
                if (limitInput) {
                    limitInput.value = (limit && limit > 0) ? limit : '';
                }
                document.getElementById('modal-edit-spent').value = spent;

                const hintEl = document.getElementById('modal-edit-spent-hint');
                if (hintEl) {
                    if (type === 'chi') {
                        hintEl.innerHTML = `Đã chi tháng này: <strong class="text-rose-600">${spent.toLocaleString()} đ</strong> (Hạn mức mới phải ≥ ${spent.toLocaleString()} đ)`;
                        hintEl.classList.remove('hidden');
                    } else {
                        hintEl.classList.add('hidden');
                    }
                }

                toggleModalEditLimit();
                handleEditLimitChange(limitInput ? limitInput.value : '');
                document.getElementById('edit-category-modal').classList.remove('hidden');
                setTimeout(() => {
                    if (limitInput && type === 'chi') {
                        limitInput.focus();
                        limitInput.select();
                    }
                }, 100);
            }

            function closeEditCategoryModal() {
                document.getElementById('edit-category-modal').classList.add('hidden');
            }

            async function submitEditCategory() {
                const id = document.getElementById('modal-edit-cat-id').value;
                const name = document.getElementById('modal-edit-name').value.trim();
                const type = document.getElementById('modal-edit-type').value;
                const spent = parseFloat(document.getElementById('modal-edit-spent').value) || 0;
                const limit = type === 'chi' ? (parseFloat(document.getElementById('modal-edit-limit').value) || 0) : 0;

                if(!name) return showCustomModal("Thiếu tên", "Vui lòng nhập tên danh mục!", "⚠️");
                if(type === 'chi' && limit < 1000) return showCustomModal("Hạn mức không hợp lệ", "Hạn mức ngân sách tối thiểu là 1.000 đ!", "⚠️");

                // Quy tắc: Không được sửa hạn mức nhỏ hơn số tiền đã chi trong danh mục đó
                if(type === 'chi' && limit < spent) {
                    return showCustomModal(
                        "Hạn mức không hợp lệ",
                        `Hạn mức mới (${limit.toLocaleString()} đ) không được nhỏ hơn số tiền đã chi (${spent.toLocaleString()} đ) trong danh mục này! Bạn chỉ có thể nâng hạn mức chứ không được giảm nhỏ hơn số tiền đã chi.`,
                        "⚠️"
                    );
                }

                const res = await fetch(`/danh-muc/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({name, type, budget_limit: limit})
                });

                if(res.ok) {
                    const data = await res.json().catch(() => ({}));
                    closeEditCategoryModal();
                    await loadCategories();
                    await loadSummary();
                    if (typeof updateReportSummary === 'function') {
                        updateReportSummary();
                    }
                    if (typeof loadNotifications === 'function') {
                        loadNotifications();
                    }
                    if (data && data.diff > 0) {
                        const oldLimit = data.old_limit || 0;
                        if (data.is_new_allocation || oldLimit === 0) {
                            showCustomModal("Cấp hạn mức thành công", `Đã cấp hạn mức cho hũ "${name}": ${limit.toLocaleString()} đ (đã trích ${data.diff.toLocaleString()} đ từ ví chính vào hũ)!`, "✨");
                        } else {
                            showCustomModal(
                                "Tăng hạn mức thành công",
                                `Hũ "${name}":\n• Hạn mức cũ: ${oldLimit.toLocaleString()} đ\n• Hạn mức mới: ${limit.toLocaleString()} đ\n➔ Đã trích thêm ${data.diff.toLocaleString()} đ từ ví chính vào hũ!`,
                                "📤"
                            );
                        }
                    } else if (data && data.diff < 0) {
                        const refund = Math.abs(data.diff);
                        const oldLimit = data.old_limit || 0;
                        showCustomModal(
                            "Hoàn tiền thành công",
                            `Hũ "${name}":\n• Hạn mức cũ: ${oldLimit.toLocaleString()} đ\n• Hạn mức mới: ${limit.toLocaleString()} đ\n➔ Đã hoàn trả ${refund.toLocaleString()} đ về ví chính!`,
                            "💰"
                        );
                    } else {
                        showCustomModal("Thành công", `Đã cập nhật danh mục "${name}"!`, "✅");
                    }
                } else {
                    let err = await res.json().catch(() => ({}));
                    showCustomModal("Lỗi cập nhật", err.detail || "Không thể cập nhật danh mục!", "❌");
                }
            }


            async function loadCategories() {
                if (!token) return;
                let res = await fetch('/api/danh-muc', {headers: {'Authorization': 'Bearer ' + token}});
                if(!res.ok) {
                    res = await fetch('/danh-muc', {headers: {'Authorization': 'Bearer ' + token}});
                }
                if(res.ok) {
                    const data = await res.json();
                    if (Array.isArray(data)) {
                        allCategories = data.map(c => ({
                            ...c,
                            id: c.id || c.ma_dm,
                            ma_dm: c.ma_dm || c.id,
                            name: c.name || c.ten_dm,
                            ten_dm: c.ten_dm || c.name,
                            type: c.type || c.loai_dm,
                            loai_dm: c.loai_dm || c.type,
                            budget_limit: (c.budget_limit !== undefined) ? Number(c.budget_limit) : Number(c.han_muc || 0),
                            han_muc: (c.han_muc !== undefined) ? Number(c.han_muc) : Number(c.budget_limit || 0)
                        }));

                        if(allCategories.length === 0) {
                            const defaultCats = [
                                {name: "Ăn uống", type: "chi", budget_limit: 0},
                                {name: "Đi lại", type: "chi", budget_limit: 0},
                                {name: "Mua sắm", type: "chi", budget_limit: 0},
                                {name: "Sinh hoạt", type: "chi", budget_limit: 0},
                                {name: "Học tập & Phát triển", type: "chi", budget_limit: 0},
                                {name: "Tiền lương", type: "thu", budget_limit: 0}
                            ];
                            for (const dc of defaultCats) {
                                await fetch('/danh-muc', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                                    body: JSON.stringify(dc)
                                }).catch(() => {});
                            }
                            await loadCategories();
                            return;
                        }

                        renderJarsProgressList();
                        renderCategoriesCrudList();
                        if (typeof updateTongTrongHu === 'function') updateTongTrongHu();
                    }
                }
            }


            function renderCategoriesCrudList() {
                const container = document.getElementById('categories-crud-list');
                container.innerHTML = "";
                allCategories.forEach(c => {
                    // Danh mục Tiết kiệm đã quản lý riêng ở tab Tiết Kiệm nên không hiển thị ở Quản lý Danh Mục (Ảnh 4)
                    if (c.name === 'Tiết kiệm' || c.ten_dm === 'Tiết kiệm') return;
                    container.innerHTML += `
                        <div class="flex justify-between items-center bg-white p-3 rounded-2xl border text-xs shadow-sm gap-2">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <span class="font-bold text-slate-800 truncate">${c.name}</span>
                                <span class="text-[9px] px-1.5 py-0.5 rounded font-bold shrink-0 whitespace-nowrap ${c.type === 'thu' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}">${c.type.toUpperCase()}</span>
                            </div>
                            <div class="flex gap-1.5 shrink-0 whitespace-nowrap">
                                <button onclick="openEditCategoryModal(${c.id}, '${c.name}', '${c.type}', ${c.budget_limit})" class="px-2.5 py-1 bg-teal-50 hover:bg-teal-100 text-teal-700 font-bold text-[10px] rounded-lg transition">Sửa</button>
                                <button onclick="deleteCategory(${c.id})" class="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold text-[10px] rounded-lg transition">Xóa</button>
                            </div>
                        </div>`;
                });
            }


            function toggleAddCategoryForm(show) {
                const box = document.getElementById('box-add-category-form');
                const btnText = document.getElementById('btn-toggle-add-cat-text');
                if (!box) return;
                const isCurrentlyHidden = box.classList.contains('hidden');
                const shouldOpen = typeof show === 'boolean' ? show : isCurrentlyHidden;

                if (shouldOpen) {
                    box.classList.remove('hidden');
                    if (btnText) btnText.innerText = "✕ Đóng";
                    const nameInput = document.getElementById('cat-name-input');
                    if (nameInput) {
                        nameInput.value = '';
                        setTimeout(() => nameInput.focus(), 100);
                    }
                    const limitInput = document.getElementById('cat-limit-input');
                    if (limitInput) limitInput.value = '';
                    setCategoryTabType('chi');
                } else {
                    box.classList.add('hidden');
                    if (btnText) btnText.innerText = "+ Thêm danh mục";
                }
            }
            window.toggleAddCategoryForm = toggleAddCategoryForm;
            window.openAddCategoryModal = openAddCategoryModal;

            function openAddCategoryModal() {
                toggleAddCategoryForm(true);
            }

            function closeAddCategoryModal() {
                toggleAddCategoryForm(false);
                const modal = document.getElementById('add-category-modal');
                if (modal) modal.classList.add('hidden');
            }


            function handleCatLimitInput(input) {
                if (!input) return;
                const type = document.getElementById('cat-type-input')?.value || 'chi';
                const raw = input.value.replace(/[^0-9]/g, '').replace(/^0+/, '');
                input.value = raw;
                const num = parseFloat(raw) || 0;
                const errEl = document.getElementById('cat-limit-error');

                if (type === 'chi') {
                    if (raw && num < 1000) {
                        if (errEl) {
                            errEl.innerText = "⚠️ Số tiền tối thiểu là 1.000 đ!";
                            errEl.classList.remove('hidden');
                        }
                        input.classList.add('border-rose-400');
                    } else {
                        if (errEl) errEl.classList.add('hidden');
                        input.classList.remove('border-rose-400');
                    }
                } else {
                    if (raw && num > 0 && num < 1000) {
                        if (errEl) {
                            errEl.innerText = "⚠️ Số tiền thu nhập tối thiểu là 1.000 đ!";
                            errEl.classList.remove('hidden');
                        }
                        input.classList.add('border-rose-400');
                    } else {
                        if (errEl) errEl.classList.add('hidden');
                        input.classList.remove('border-rose-400');
                    }
                }
            }
            window.handleCatLimitInput = handleCatLimitInput;

            async function saveCategoryCrud() {
                const nameInput = document.getElementById('cat-name-input');
                const name = (nameInput ? nameInput.value : '').trim();
                const typeInput = document.getElementById('cat-type-input');
                const type = (typeInput ? typeInput.value : 'chi');
                const limitInput = document.getElementById('cat-limit-input');
                const rawAmount = (limitInput ? limitInput.value : '').replace(/[^0-9]/g, '');
                const amount = parseFloat(rawAmount) || 0;

                if(!name) {
                    if (nameInput) nameInput.focus();
                    return showCustomModal("Thiếu tên", "Vui lòng nhập tên danh mục!", "⚠️");
                }

                if(name.toLowerCase() === 'tiết kiệm' || name.toLowerCase() === 'tiet kiem') {
                    return showCustomModal("Thông báo", "Quỹ Tiết kiệm đã được quản lý chuyên biệt tại mục Tiết Kiệm!", "ℹ️");
                }

                // Ràng buộc số tiền cấp cho hũ tối thiểu là 1.000 đ
                if(type === 'chi' && (!rawAmount || amount < 1000)) {
                    const errEl = document.getElementById('cat-limit-error');
                    if (errEl) {
                        errEl.innerText = "⚠️ Số tiền tối thiểu là 1.000 đ!";
                        errEl.classList.remove('hidden');
                    }
                    if (limitInput) {
                        limitInput.classList.add('border-rose-400');
                        limitInput.focus();
                    }
                    return showCustomModal("Số tiền không hợp lệ", "Số tiền cấp cho hũ tối thiểu là 1.000 đ!", "⚠️");
                }

                if(type === 'thu' && amount > 0 && amount < 1000) {
                    const errEl = document.getElementById('cat-limit-error');
                    if (errEl) {
                        errEl.innerText = "⚠️ Số tiền thu nhập tối thiểu là 1.000 đ!";
                        errEl.classList.remove('hidden');
                    }
                    if (limitInput) {
                        limitInput.classList.add('border-rose-400');
                        limitInput.focus();
                    }
                    return showCustomModal("Số tiền không hợp lệ", "Số tiền thu nhập cộng vào ví tối thiểu là 1.000 đ!", "⚠️");
                }

                const res = await fetch('/danh-muc', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({name, type, budget_limit: amount, amount: amount})
                });

                if(res.ok) {
                    closeAddCategoryModal();
                    if (nameInput) nameInput.value = "";
                    if (limitInput) {
                        limitInput.value = "";
                        limitInput.classList.remove('border-rose-400');
                    }
                    const errEl = document.getElementById('cat-limit-error');
                    if (errEl) errEl.classList.add('hidden');
                    const hintEl = document.getElementById('cat-limit-hint');
                    if (hintEl) hintEl.classList.remove('hidden');
                    setCategoryTabType(type);
                    await loadCategories();
                    await loadSummary();
                    await loadTransactions();
                    if(type === 'thu') {
                        showCustomModal("Thành công", `Đã lưu danh mục thu "${name}" và cộng ${amount > 0 ? amount.toLocaleString() + ' đ' : ''} vào ví chính!`, "💰");
                    } else {
                        showCustomModal("Thành công", `Đã tạo hũ chi tiêu "${name}" và trích ${amount > 0 ? amount.toLocaleString() + ' đ' : ''} từ ví chính vào hũ!`, "✅");
                    }
                } else {
                    let errData = await res.json().catch(() => ({}));
                    showCustomModal("Không thể tạo danh mục", errData.detail || "Số dư ví chính không đủ để cấp cho hũ này!", "❌");
                }
            }


            function deleteCategory(id) {
                const c = allCategories.find(item => item.id == id);
                if(!c) return;

                selectedCategoryToDelete = c;

                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                let spent = allTransactions.filter(t => {
                    const tDate = t.date || t.ngay_gd || '';
                    return (t.category_id == id || t.ma_dm == id) && 
                           (t.type === 'chi' || t.loai_gd === 'chi') &&
                           tDate.startsWith(currentYM);
                }).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
                let remaining = (c.type === 'chi' && c.budget_limit > 0) ? Math.max(0, c.budget_limit - spent) : 0;

                const refundBox = document.getElementById('confirm-del-cat-refund-box');
                const msgEl = document.getElementById('confirm-del-cat-msg');
                const refundAmtEl = document.getElementById('confirm-del-cat-refund-amount');
                const confirmBtn = document.getElementById('btn-confirm-delete-cat');
                const titleEl = document.getElementById('confirm-del-cat-title');
                const iconEl = document.getElementById('confirm-del-cat-icon');

                if(c.type === 'chi' && remaining > 0) {
                    if(iconEl) iconEl.innerText = "💰";
                    if(titleEl) titleEl.innerText = "Xác Nhận Xóa Hũ & Hoàn Tiền";
                    if(refundBox) refundBox.classList.remove('hidden');
                    if(refundAmtEl) refundAmtEl.innerText = remaining.toLocaleString() + " đ";
                    if(msgEl) msgEl.innerHTML = `Hũ chi tiêu <strong>"${c.name}"</strong> chưa sử dụng hết hạn mức. Sau khi xóa, số tiền hạn mức khả dụng còn lại <strong class="text-teal-700">${remaining.toLocaleString()} đ</strong> sẽ được <strong>hoàn về ví chính</strong> để bạn sử dụng cho các mục tiêu chi tiêu tiếp theo.`;
                    if(confirmBtn) {
                        confirmBtn.innerText = "Xác nhận xóa & Hoàn tiền";
                        confirmBtn.className = "flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition shadow-sm";
                    }
                } else {
                    if(iconEl) iconEl.innerText = "🗑️";
                    if(titleEl) titleEl.innerText = "Xác Nhận Xóa Danh Mục";
                    if(refundBox) refundBox.classList.add('hidden');
                    if(msgEl) msgEl.innerHTML = `Bạn có chắc chắn muốn xóa danh mục <strong>"${c.name}"</strong> không? Thao tác này sẽ xóa danh mục và các dữ liệu liên quan.`;
                    if(confirmBtn) {
                        confirmBtn.innerText = "Xác nhận xóa";
                        confirmBtn.className = "flex-1 py-2.5 bg-rose-500 hover:bg-rose-600 text-white text-xs font-bold rounded-xl transition shadow-sm";
                    }
                }

                document.getElementById('confirm-delete-cat-modal').classList.remove('hidden');
            }

            async function executeDeleteCategory() {
                if(!selectedCategoryToDelete) return;
                const c = selectedCategoryToDelete;
                const id = c.id;
                closeConfirmDeleteCatModal();

                const now = new Date();
                const currentYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                let spent = allTransactions.filter(t => {
                    const tDate = t.date || t.ngay_gd || '';
                    return (t.category_id == id || t.ma_dm == id) && 
                           (t.type === 'chi' || t.loai_gd === 'chi') &&
                           tDate.startsWith(currentYM);
                }).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
                let remaining = (c.type === 'chi' && c.budget_limit > 0) ? Math.max(0, c.budget_limit - spent) : 0;

                const res = await fetch(`/danh-muc/${id}`, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    await loadCategories();
                    await loadTransactions();
                    await loadSummary();
                    await loadNotifications();
                    if(c.type === 'chi' && remaining > 0) {
                        showCustomModal("Hoàn tiền thành công", `Đã xóa danh mục "${c.name}". Số tiền hạn mức khả dụng còn lại ${remaining.toLocaleString()} đ đã được hoàn về ví chính để bạn sử dụng cho các mục tiêu chi tiêu tiếp theo!`, "💰");
                    } else {
                        showCustomModal("Thành công", `Đã xóa danh mục "${c.name}" thành công!`, "🗑️");
                    }
                } else {
                    showCustomModal("Lỗi", "Không thể xóa danh mục!", "❌");
                }
            }

