/**
 * MoneyMind - Lịch Sử & Tra Cứu Giao Dịch, Bộ Lọc
 */
            function setLookupType(type) {
                document.getElementById('lookup-type').value = type;
                const bAll = document.getElementById('lookup-btn-all');
                const bThu = document.getElementById('lookup-btn-thu');
                const bChi = document.getElementById('lookup-btn-chi');

                bAll.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg text-slate-600 transition";
                bThu.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg text-slate-600 transition";
                bChi.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg text-slate-600 transition";

                if(type === 'all') bAll.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg bg-white text-teal-600 shadow-sm transition";
                else if(type === 'thu') bThu.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg bg-white text-emerald-600 shadow-sm transition";
                else bChi.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg bg-white text-rose-600 shadow-sm transition";

                applyLookupFilter();
            }


            function removeVietnameseTones(str) {
                if (!str) return '';
                return str
                    .normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '')
                    .replace(/đ/g, 'd').replace(/Đ/g, 'D')
                    .toLowerCase();
            }

            function clearLookupKeyword() {
                const keywordEl = document.getElementById('lookup-keyword');
                if (keywordEl) {
                    keywordEl.value = '';
                    keywordEl.focus();
                }
                const clearBtn = document.getElementById('lookup-clear-btn');
                if (clearBtn) clearBtn.classList.add('hidden');
                applyLookupFilter();
            }

            function openCategoryPickerModal() {}
            function closeCategoryPickerModal() {}
            function selectLookupCategory() {}

            function applyLookupFilter() {
                const type = document.getElementById('lookup-type').value;
                const date = document.getElementById('lookup-date').value;
                const keywordEl = document.getElementById('lookup-keyword');
                const rawKeyword = keywordEl ? keywordEl.value.trim() : '';
                const keyword = rawKeyword.toLowerCase();
                const keywordNoTone = removeVietnameseTones(rawKeyword);

                const clearBtn = document.getElementById('lookup-clear-btn');
                if (clearBtn) {
                    if (rawKeyword) clearBtn.classList.remove('hidden');
                    else clearBtn.classList.add('hidden');
                }

                let catMap = {}; 
                allCategories.forEach(c => { 
                    catMap[c.id] = c.name; 
                    if(c.ma_dm) catMap[c.ma_dm] = c.name;
                });

                let filtered = allTransactions.filter(t => {
                    const tDate = t.date || t.ngay_gd || '';
                    const tCatId = t.category_id || t.ma_dm;
                    const cName = (catMap[tCatId] || t.category_name || '').toLowerCase();
                    const note = (t.note || t.ghi_chu || '').toLowerCase();
                    const isSavings = (note.includes('tiết kiệm') || note.includes('trích quỹ') || note.includes('mục tiêu') || cName.includes('tiết kiệm'));

                    // Tiết kiệm luôn luôn là khoản CHI, tuyệt đối KHÔNG ĐƯỢC coi là khoản THU
                    const effectiveType = isSavings ? 'chi' : (t.type || t.loai_gd);

                    // Khi người dùng bấm lọc "Thu", loại trừ hoàn toàn các giao dịch tiết kiệm
                    if (type === 'thu' && isSavings) {
                        return false;
                    }

                    let matchType = (type === 'all' || effectiveType === type);
                    let matchDate = (!date || tDate.startsWith(date));

                    // Lọc theo từ khóa tìm kiếm (tìm theo mô tả, danh mục hoặc mục tiêu tiết kiệm)
                    let matchKeyword = true;
                    if (keyword) {
                        let goalName = '';
                        if (isSavings) {
                            let clean = note.replace(/\s*\((đã xóa|đã xoá)\)/gi, '').trim();
                            if (clean.includes(':')) {
                                goalName = clean.split(':')[1].trim().toLowerCase();
                            } else {
                                goalName = clean.toLowerCase();
                            }
                        }

                        const noteNoTone = removeVietnameseTones(note);
                        const cNameNoTone = removeVietnameseTones(cName);
                        const goalNameNoTone = removeVietnameseTones(goalName);

                        const matchNote = note.includes(keyword) || noteNoTone.includes(keywordNoTone);
                        const matchCatName = cName.includes(keyword) || cNameNoTone.includes(keywordNoTone);
                        const matchGoal = goalName ? (goalName.includes(keyword) || goalNameNoTone.includes(keywordNoTone)) : false;

                        matchKeyword = matchNote || matchCatName || matchGoal;
                    }

                    return matchType && matchDate && matchKeyword;
                });

                renderLookupTransactions(filtered);
            }


            function formatCompactTxDate(rawDate) {
                if(!rawDate) return 'Vừa xong';
                try {
                    const d = new Date(rawDate.replace(' ', 'T'));
                    if(isNaN(d.getTime())) return rawDate.replace('T', ' ').substring(0, 16);
                    const hh = String(d.getHours()).padStart(2, '0');
                    const mm = String(d.getMinutes()).padStart(2, '0');
                    const dd = String(d.getDate()).padStart(2, '0');
                    const mo = String(d.getMonth() + 1).padStart(2, '0');
                    const yy = String(d.getFullYear()).slice(-2);
                    return `${hh}:${mm} • ${dd}/${mo}/${yy}`;
                } catch(e) {
                    return rawDate.replace('T', ' ').substring(0, 16);
                }
            }

            function renderLookupTransactions(txs) {
                const list = document.getElementById('tx-list');
                list.innerHTML = "";
                if(!txs || txs.length === 0) { 
                    list.innerHTML = `<p class="text-xs text-slate-400 text-center py-4">Không tìm thấy giao dịch phù hợp.</p>`; 
                    return; 
                }

                const keywordEl = document.getElementById('lookup-keyword');
                const rawKeyword = keywordEl ? keywordEl.value.trim() : '';
                const keyword = rawKeyword.toLowerCase();
                const keywordNoTone = removeVietnameseTones(rawKeyword);

                let catMap = {}; 
                allCategories.forEach(c => { 
                    catMap[c.id] = c.name; 
                    if(c.ma_dm) catMap[c.ma_dm] = c.name;
                });

                // Sắp xếp các giao dịch mới nhất ở trên cùng giống như ngăn xếp (LIFO / Stack)
                const sortedTxs = [...txs].sort((a, b) => {
                    const timeA = getTxTimestamp(a);
                    const timeB = getTxTimestamp(b);
                    if (timeB !== timeA) return timeB - timeA;
                    const idA = Number(a.id || a.ma_gd || 0);
                    const idB = Number(b.id || b.ma_gd || 0);
                    return idB - idA;
                });

                sortedTxs.forEach((t, index) => {
                    const txId = t.id || t.ma_gd;
                    const rawNote = t.note || t.ghi_chu || '';
                    let cName = catMap[t.category_id || t.ma_dm] || t.category_name || '';
                    const isSavings = (rawNote.toLowerCase().includes('tiết kiệm') || rawNote.toLowerCase().includes('trích quỹ') || rawNote.toLowerCase().includes('mục tiêu') || cName.toLowerCase().includes('tiết kiệm'));
                    
                    // Tiết kiệm luôn là khoản chi (không phải thu)
                    const isChi = isSavings ? true : (t.type === 'chi' || t.loai_gd === 'chi');
                    const amt = t.amount !== undefined ? t.amount : (t.so_tien || 0);
                    const rawDate = t.date || t.ngay_gd || '';
                    const dateStr = formatCompactTxDate(rawDate);

                    // Kiểm tra mục tiêu đã bị xoá hay chưa
                    const isDeletedGoal = isSavings && (rawNote.includes('(đã xóa)') || rawNote.includes('(đã xoá)'));

                    // Trích xuất tên mục tiêu tiết kiệm và chuẩn hóa mô tả
                    let goalName = '';
                    let displayNote = rawNote;
                    if (isSavings) {
                        cName = '🎯 Tiết kiệm';
                        let clean = rawNote.replace(/\s*\((đã xóa|đã xoá)\)/gi, '').trim();
                        if (clean.includes(':')) {
                            goalName = clean.split(':')[1].trim();
                        } else {
                            goalName = clean;
                        }
                        displayNote = `Mục tiêu: ${goalName}${isDeletedGoal ? ' (đã xoá)' : ''}`;
                    } else if (!cName) {
                        cName = isChi ? 'Khoản chi' : 'Khoản thu';
                        displayNote = rawNote || 'Không có mô tả chi tiết';
                    } else if (!displayNote) {
                        displayNote = 'Không có mô tả chi tiết';
                    }

                    // Tự động mở sẵn phần mô tả chi tiết nếu từ khóa tìm kiếm khớp với mô tả chi tiết (Ảnh 2)
                    let isNoteMatch = false;
                    if (keyword) {
                        const rawNoteLower = rawNote.toLowerCase();
                        const noteNoTone = removeVietnameseTones(rawNote);
                        const goalNameLower = goalName ? goalName.toLowerCase() : '';
                        const goalNameNoTone = removeVietnameseTones(goalName);

                        if (rawNoteLower.includes(keyword) || noteNoTone.includes(keywordNoTone)) {
                            isNoteMatch = true;
                        } else if (goalName && (goalNameLower.includes(keyword) || goalNameNoTone.includes(keywordNoTone))) {
                            isNoteMatch = true;
                        }
                    }

                    const detailClass = isNoteMatch ? "pt-2 border-t border-slate-100 text-slate-600 text-[11px] bg-slate-50 p-2.5 rounded-xl space-y-1" : "hidden pt-2 border-t border-slate-100 text-slate-600 text-[11px] bg-slate-50 p-2.5 rounded-xl space-y-1";
                    const arrowChar = isNoteMatch ? '▴' : '▾';
                    const btnClass = isNoteMatch 
                        ? "shrink-0 whitespace-nowrap px-2 py-0.5 bg-teal-50 hover:bg-teal-100 text-teal-700 rounded-md text-[10px] font-semibold transition flex items-center gap-0.5" 
                        : "shrink-0 whitespace-nowrap px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-md text-[10px] font-semibold transition flex items-center gap-0.5";

                    list.innerHTML += `
                        <div class="p-3 rounded-2xl bg-white border border-slate-200/90 text-xs shadow-xs space-y-2 relative">
                            <!-- Hàng 1: Tên danh mục bên trái, Số tiền (dịch sang trái) và Nút 3 chấm bên phải -->
                            <div class="flex items-center justify-between gap-2">
                                <div class="flex items-center gap-1.5 min-w-0 flex-1">
                                    <span class="font-bold text-slate-800 text-[13px] truncate">${cName}</span>
                                    ${isDeletedGoal ? '<span class="shrink-0 text-[9px] bg-rose-100 text-rose-600 px-1.5 py-0.2 rounded font-bold whitespace-nowrap">Đã xoá</span>' : ''}
                                </div>
                                <div class="flex items-center gap-1.5 shrink-0">
                                    <!-- Số tiền được dịch sang trái một chút để chừa khoảng cách cho nút 3 chấm -->
                                    <div class="font-extrabold text-sm whitespace-nowrap text-right ${isChi ? 'text-rose-600' : 'text-emerald-600'}">
                                        ${isChi ? '-' : '+'}${amt.toLocaleString()} đ
                                    </div>
                                    <!-- Nút 3 chấm mở menu Sửa / Xóa giao dịch -->
                                    <div class="relative">
                                        <button onclick="toggleTxDropdown(event, ${txId})" id="tx-btn-${txId}" class="w-6 h-6 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition" title="Tùy chọn">
                                            <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
                                                <circle cx="12" cy="5" r="1.8"></circle>
                                                <circle cx="12" cy="12" r="1.8"></circle>
                                                <circle cx="12" cy="19" r="1.8"></circle>
                                            </svg>
                                        </button>
                                        <!-- Dropdown Menu -->
                                        <div id="tx-dropdown-${txId}" class="tx-action-dropdown hidden absolute right-0 top-7 z-40 w-36 bg-white rounded-xl shadow-xl border border-slate-100 py-1 text-xs animate-in fade-in duration-150">
                                            <button onclick="openEditTxModal(${txId})" class="w-full text-left px-3 py-2 hover:bg-teal-50 flex items-center gap-2 text-slate-700 font-medium transition">
                                                <svg class="w-3.5 h-3.5 text-teal-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                                                <span>Sửa giao dịch</span>
                                            </button>
                                            <button onclick="openDeleteTxModal(${txId})" class="w-full text-left px-3 py-2 hover:bg-rose-50 flex items-center gap-2 text-rose-600 font-medium border-t border-slate-100 transition">
                                                <svg class="w-3.5 h-3.5 text-rose-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                                <span>Xóa giao dịch</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Hàng 2: Thời gian giao dịch bên trái, Nút chi tiết bên phải -->
                            <div class="flex items-center justify-between gap-2 text-[10px] text-slate-400 pt-1.5 border-t border-slate-100/90">
                                <span class="whitespace-nowrap flex items-center gap-1 font-medium text-slate-500">🕒 ${dateStr}</span>
                                <button onclick="toggleDetail(${index})" id="detail-btn-${index}" class="${btnClass}">
                                    <span>Chi tiết</span>
                                    <span id="detail-arrow-${index}" class="text-[9px]">${arrowChar}</span>
                                </button>
                            </div>

                            <!-- Khung chi tiết mở rộng -->
                            <div id="detail-${index}" class="${detailClass}">
                                <div class="break-words"><span class="font-semibold text-slate-700">Mô tả chi tiết:</span> <span class="font-medium text-slate-800">${displayNote}</span></div>
                                ${isSavings && goalName ? `<div class="break-words"><span class="font-semibold text-slate-700">Mục tiêu:</span> <span class="font-bold text-teal-700">${goalName}</span> ${isDeletedGoal ? '<span class="text-[9px] bg-rose-100 text-rose-600 px-1.5 py-0.5 rounded font-bold ml-1 whitespace-nowrap">Đã xoá</span>' : ''}</div>` : ''}
                            </div>
                        </div>`;
                });
            }


            function toggleDetail(index) {
                const detailBox = document.getElementById(`detail-${index}`);
                const arrow = document.getElementById(`detail-arrow-${index}`);
                if (!detailBox) return;
                detailBox.classList.toggle('hidden');
                if (arrow) {
                    arrow.innerText = detailBox.classList.contains('hidden') ? '▾' : '▴';
                }
            }

            // ==========================================
            // XỬ LÝ MENU 3 CHẤM, SỬA & XÓA GIAO DỊCH
            // ==========================================

            function toggleTxDropdown(event, txId) {
                if (event) event.stopPropagation();
                const dropdown = document.getElementById(`tx-dropdown-${txId}`);
                if (!dropdown) return;
                const isHidden = dropdown.classList.contains('hidden');
                document.querySelectorAll('.tx-action-dropdown').forEach(d => d.classList.add('hidden'));
                if (isHidden) {
                    dropdown.classList.remove('hidden');
                }
            }

            // Tự động đóng dropdown khi nhấp ra ngoài
            document.addEventListener('click', function(e) {
                if (!e.target.closest('.tx-action-dropdown') && !e.target.closest('[id^="tx-btn-"]')) {
                    document.querySelectorAll('.tx-action-dropdown').forEach(d => d.classList.add('hidden'));
                }
            });

            function openEditTxModal(txId) {
                document.querySelectorAll('.tx-action-dropdown').forEach(d => d.classList.add('hidden'));

                const tx = allTransactions.find(t => (t.id == txId || t.ma_gd == txId));
                if (!tx) {
                    if (typeof showCustomModal === 'function') showCustomModal("Lỗi", "Không tìm thấy thông tin giao dịch!", "⚠️");
                    return;
                }

                const editModal = document.getElementById('edit-tx-modal');
                if (!editModal) return;

                document.getElementById('edit-tx-id').value = txId;

                const rawNote = tx.note || tx.ghi_chu || '';
                const catId = tx.category_id || tx.ma_dm;
                let cat = allCategories.find(c => (c.id == catId || c.ma_dm == catId));
                const isSavings = rawNote.toLowerCase().includes('tiết kiệm') || rawNote.toLowerCase().includes('trích quỹ') || (cat && cat.name && cat.name.toLowerCase().includes('tiết kiệm'));
                const txType = isSavings ? 'chi' : (tx.type || tx.loai_gd || 'chi');

                setEditModalTxType(txType, catId);

                const amt = tx.amount !== undefined ? tx.amount : (tx.so_tien || 0);
                document.getElementById('edit-tx-amount').value = amt;

                const rawDate = tx.date || tx.ngay_gd || '';
                if (rawDate) {
                    document.getElementById('edit-tx-date').value = rawDate.substring(0, 10);
                } else {
                    document.getElementById('edit-tx-date').value = new Date().toISOString().substring(0, 10);
                }

                document.getElementById('edit-tx-note').value = rawNote;

                editModal.classList.remove('hidden');
            }

            function closeEditTransactionModal() {
                const editModal = document.getElementById('edit-tx-modal');
                if (editModal) editModal.classList.add('hidden');
            }

            function setEditModalTxType(type, selectedCatId) {
                document.getElementById('edit-tx-type').value = type;
                const btnChi = document.getElementById('btn-edit-tx-chi');
                const btnThu = document.getElementById('btn-edit-tx-thu');

                if (btnChi && btnThu) {
                    if (type === 'chi') {
                        btnChi.className = "py-2 rounded-lg bg-rose-500 text-white shadow-sm transition flex items-center justify-center gap-1";
                        btnThu.className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";
                    } else {
                        btnThu.className = "py-2 rounded-lg bg-emerald-500 text-white shadow-sm transition flex items-center justify-center gap-1";
                        btnChi.className = "py-2 rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";
                    }
                }

                renderEditCategoryChips(type, selectedCatId);
            }

            function renderEditCategoryChips(type, selectedCatId) {
                const chipsContainer = document.getElementById('edit-tx-category-chips');
                if (!chipsContainer) return;
                chipsContainer.innerHTML = '';

                let cats = allCategories.filter(c => (c.type === type || c.loai_dm === type));
                if (cats.length === 0 && selectedCatId) {
                    const found = allCategories.find(c => (c.id == selectedCatId || c.ma_dm == selectedCatId));
                    if (found) cats.push(found);
                }

                let currentSelected = selectedCatId;
                if (!currentSelected && cats.length > 0) {
                    currentSelected = cats[0].id || cats[0].ma_dm;
                }
                document.getElementById('edit-tx-category').value = currentSelected || '';

                cats.forEach(c => {
                    const cId = c.id || c.ma_dm;
                    const cName = c.name || c.ten_dm || 'Danh mục';
                    const isSelected = (cId == currentSelected);
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.id = `edit-chip-cat-${cId}`;
                    btn.className = isSelected 
                        ? "p-2 rounded-xl border text-xs font-bold text-center transition truncate bg-teal-50 border-teal-500 text-teal-700 shadow-xs"
                        : "p-2 rounded-xl border text-xs font-bold text-center transition truncate bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100";
                    btn.innerText = cName;
                    btn.onclick = () => selectEditTxCategory(cId);
                    chipsContainer.appendChild(btn);
                });
            }

            function selectEditTxCategory(catId) {
                document.getElementById('edit-tx-category').value = catId;
                const chipsContainer = document.getElementById('edit-tx-category-chips');
                if (!chipsContainer) return;
                const buttons = chipsContainer.querySelectorAll('button');
                buttons.forEach(btn => {
                    if (btn.id === `edit-chip-cat-${catId}`) {
                        btn.className = "p-2 rounded-xl border text-xs font-bold text-center transition truncate bg-teal-50 border-teal-500 text-teal-700 shadow-xs";
                    } else {
                        btn.className = "p-2 rounded-xl border text-xs font-bold text-center transition truncate bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100";
                    }
                });
            }

            async function submitEditTransaction() {
                const txId = document.getElementById('edit-tx-id').value;
                const type = document.getElementById('edit-tx-type').value;
                const amount = parseFloat(document.getElementById('edit-tx-amount').value);
                const category_id = parseInt(document.getElementById('edit-tx-category').value);
                const note = document.getElementById('edit-tx-note').value.trim();
                const txDate = document.getElementById('edit-tx-date').value;

                if (!category_id || isNaN(category_id)) return showCustomModal("Thiếu danh mục", "Vui lòng chọn danh mục phù hợp!", "⚠️");
                if (!amount || isNaN(amount) || amount < 1000) return showCustomModal("Số tiền không hợp lệ", "Số tiền giao dịch tối thiểu là 1.000 đ!", "⚠️");

                try {
                    const res = await fetch(`/giao-dich/${txId}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                        body: JSON.stringify({
                            amount,
                            so_tien: amount,
                            type,
                            loai_gd: type,
                            category_id,
                            ma_dm: category_id,
                            note,
                            ghi_chu: note,
                            date: txDate ? txDate + 'T12:00:00' : new Date().toISOString(),
                            ngay_gd: txDate ? txDate + 'T12:00:00' : new Date().toISOString()
                        })
                    });

                    if (res.ok) {
                        const data = await res.json();
                        closeEditTransactionModal();

                        // Cập nhật lại đối tượng trong allTransactions
                        const idx = allTransactions.findIndex(t => (t.id == txId || t.ma_gd == txId));
                        if (idx !== -1) {
                            allTransactions[idx] = {
                                ...allTransactions[idx],
                                ...data,
                                amount: data.amount !== undefined ? data.amount : amount,
                                so_tien: data.so_tien !== undefined ? data.so_tien : amount,
                                type: data.type || type,
                                loai_gd: data.loai_gd || type,
                                category_id: data.category_id || category_id,
                                ma_dm: data.ma_dm || category_id,
                                note: data.note !== undefined ? data.note : note,
                                ghi_chu: data.ghi_chu !== undefined ? data.ghi_chu : note,
                                date: data.date || (txDate ? txDate + 'T12:00:00' : new Date().toISOString()),
                                ngay_gd: data.ngay_gd || (txDate ? txDate + 'T12:00:00' : new Date().toISOString())
                            };
                        }

                        // Làm mới danh sách và thống kê
                        applyLookupFilter();
                        if (typeof renderJarsProgressList === 'function') renderJarsProgressList();
                        if (typeof loadSummary === 'function') loadSummary();
                        if (typeof updateReportSummary === 'function') updateReportSummary();

                        if (data.canh_bao && data.canh_bao.co_canh_bao && typeof showBudgetWarningModal === 'function') {
                            showBudgetWarningModal(data.canh_bao);
                        } else {
                            showCustomModal("Thành công", "Đã cập nhật thông tin giao dịch thành công!", "✏️");
                        }
                    } else {
                        const err = await res.json();
                        showCustomModal("Lỗi", err.detail || "Không thể cập nhật giao dịch!", "❌");
                    }
                } catch (e) {
                    showCustomModal("Lỗi kết nối", "Không thể kết nối đến máy chủ. Vui lòng thử lại!", "❌");
                }
            }

            function openDeleteTxModal(txId) {
                document.querySelectorAll('.tx-action-dropdown').forEach(d => d.classList.add('hidden'));
                const tx = allTransactions.find(t => (t.id == txId || t.ma_gd == txId));
                if (!tx) {
                    if (typeof showCustomModal === 'function') showCustomModal("Lỗi", "Không tìm thấy thông tin giao dịch!", "⚠️");
                    return;
                }

                document.getElementById('delete-tx-id').value = txId;

                const amt = tx.amount !== undefined ? tx.amount : (tx.so_tien || 0);
                const catId = tx.category_id || tx.ma_dm;
                let cat = allCategories.find(c => (c.id == catId || c.ma_dm == catId));
                let cName = cat ? (cat.name || cat.ten_dm) : 'Giao dịch';
                const note = tx.note || tx.ghi_chu || '';

                const descEl = document.getElementById('delete-tx-desc');
                if (descEl) {
                    descEl.innerHTML = `Bạn có chắc chắn muốn xóa giao dịch <strong>${cName}</strong> (${amt.toLocaleString()} đ)${note ? ` <em>"${note}"</em>` : ''}?`;
                }

                const modal = document.getElementById('delete-tx-modal');
                if (modal) modal.classList.remove('hidden');
            }

            function closeDeleteTransactionModal() {
                const modal = document.getElementById('delete-tx-modal');
                if (modal) modal.classList.add('hidden');
            }

            async function confirmDeleteTransactionAction() {
                const txId = document.getElementById('delete-tx-id').value;
                if (!txId) return;

                try {
                    const res = await fetch(`/giao-dich/${txId}`, {
                        method: 'DELETE',
                        headers: {'Authorization': 'Bearer ' + token}
                    });

                    if (res.ok) {
                        closeDeleteTransactionModal();
                        // Xóa khỏi danh sách allTransactions trên frontend (tiền không hề back về đâu)
                        allTransactions = allTransactions.filter(t => (t.id != txId && t.ma_gd != txId));

                        // Cập nhật lại giao diện
                        applyLookupFilter();
                        if (typeof renderJarsProgressList === 'function') renderJarsProgressList();
                        if (typeof loadSummary === 'function') loadSummary();
                        if (typeof updateReportSummary === 'function') updateReportSummary();

                        showCustomModal(
                            "Đã xóa giao dịch", 
                            "Giao dịch đã được xóa thành công.\n(Khoản tiền đã chi không hoàn lại vì đã tiêu dùng thực tế)", 
                            "🗑️"
                        );
                    } else {
                        const err = await res.json();
                        showCustomModal("Lỗi", err.detail || "Không thể xóa giao dịch!", "❌");
                    }
                } catch (e) {
                    showCustomModal("Lỗi kết nối", "Không thể kết nối đến máy chủ. Vui lòng thử lại!", "❌");
                }
            }
