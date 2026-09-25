/**
 * MoneyMind - Quản Lý Danh Mục Thu & Chi, Hoàn Hạn Mức
 */
            function closeConfirmDeleteCatModal() {
                document.getElementById('confirm-delete-cat-modal').classList.add('hidden');
                selectedCategoryToDelete = null;
            }


            function setCategoryTabType(type) {
                document.getElementById('cat-type-input').value = type;
                const bChi = document.getElementById('cat-btn-chi');
                const bThu = document.getElementById('cat-btn-thu');
                const wrapper = document.getElementById('cat-limit-wrapper');
                const label = document.getElementById('cat-limit-label');
                const input = document.getElementById('cat-limit-input');

                if(type === 'chi') {
                    bChi.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-white text-rose-600 shadow-sm transition";
                    bThu.className = "flex-1 py-2 text-xs font-bold rounded-lg text-slate-600 transition";
                    wrapper.style.display = 'block';
                    if(label) label.innerText = "Số tiền cấp cho hũ (đ):";
                    if(input) input.placeholder = "Ví dụ: 2000000";
                } else {
                    bThu.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-white text-emerald-600 shadow-sm transition";
                    bChi.className = "flex-1 py-2 text-xs font-bold rounded-lg text-slate-600 transition";
                    wrapper.style.display = 'block';
                    if(label) label.innerText = "Số tiền thu nhập cộng vào ví chính (đ):";
                    if(input) input.placeholder = "Ví dụ: 10000000";
                }
            }


            function toggleModalEditLimit() {
                const type = document.getElementById('modal-edit-type').value;
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


            function openEditCategoryModal(id, name, type, limit) {
                // Tính toán chính xác tổng số tiền đã chi tiêu trong danh mục này
                let spent = allTransactions
                    .filter(t => (t.category_id == id || t.ma_dm == id || t.cat_id == id) && (t.type === 'chi' || t.loai_gd === 'chi'))
                    .reduce((s, t) => s + (t.amount !== undefined ? t.amount : (t.so_tien || 0)), 0);

                document.getElementById('modal-edit-cat-id').value = id;
                document.getElementById('modal-edit-name').value = name;
                document.getElementById('modal-edit-type').value = type;
                document.getElementById('modal-edit-limit').value = limit;
                document.getElementById('modal-edit-spent').value = spent;

                const hintEl = document.getElementById('modal-edit-spent-hint');
                if (hintEl) {
                    if (type === 'chi') {
                        hintEl.innerHTML = `Đã chi: <strong class="text-rose-600">${spent.toLocaleString()} đ</strong> (Hạn mức mới phải ≥ ${spent.toLocaleString()} đ)`;
                        hintEl.classList.remove('hidden');
                    } else {
                        hintEl.classList.add('hidden');
                    }
                }

                toggleModalEditLimit();
                document.getElementById('edit-category-modal').classList.remove('hidden');
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
                if(type === 'chi' && limit > 0 && limit < 1000) return showCustomModal("Hạn mức không hợp lệ", "Hạn mức ngân sách tối thiểu là 1.000 đ!", "⚠️");

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
                    closeEditCategoryModal();
                    await loadCategories();
                    await loadSummary();
                    showCustomModal("Thành công", "Đã cập nhật danh mục!", "✅");
                } else {
                    let err = await res.json().catch(() => ({}));
                    showCustomModal("Lỗi cập nhật", err.detail || "Không thể cập nhật danh mục!", "❌");
                }
            }


            async function loadCategories() {
                const res = await fetch('/danh-muc', {headers: {'Authorization': 'Bearer ' + token}});
                if(res.ok) {
                    allCategories = await res.json();
                    if(allCategories.length === 0) {
                        await fetch('/danh-muc', {method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({name: "Ăn uống", type: "chi", budget_limit: 0})});
                        await fetch('/danh-muc', {method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({name: "Tiền lương", type: "thu", budget_limit: 0})});
                        await loadCategories();
                        return;
                    }
                    renderJarsProgressList();
                    renderCategoriesCrudList();
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


            async function saveCategoryCrud() {
                const name = document.getElementById('cat-name-input').value.trim();
                const type = document.getElementById('cat-type-input').value;
                const amount = parseFloat(document.getElementById('cat-limit-input').value) || 0;

                if(!name) return showCustomModal("Thiếu tên", "Vui lòng nhập tên danh mục!", "⚠️");
                if(amount > 0 && amount < 1000) return showCustomModal("Hạn mức không hợp lệ", "Số tiền cấp cho hũ tối thiểu là 1.000 đ!", "⚠️");
                if(name.toLowerCase() === 'tiết kiệm' || name.toLowerCase() === 'tiet kiem') {
                    return showCustomModal("Thông báo", "Quỹ Tiết kiệm đã được quản lý chuyên biệt tại mục Tiết Kiệm!", "ℹ️");
                }

                const res = await fetch('/danh-muc', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                    body: JSON.stringify({name, type, budget_limit: amount, amount: amount})
                });

                if(res.ok) {
                    document.getElementById('cat-name-input').value = "";
                    document.getElementById('cat-limit-input').value = "";
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

                let spent = allTransactions.filter(t => (t.category_id == id || t.ma_dm == id) && (t.type === 'chi' || t.loai_gd === 'chi')).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
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

                let spent = allTransactions.filter(t => (t.category_id == id || t.ma_dm == id) && (t.type === 'chi' || t.loai_gd === 'chi')).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
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

