/**
 * MoneyMind - Thống Kê & Báo Cáo Tài Chính Toàn Diện
 * Hỗ trợ lọc theo khoảng thời gian (Tháng, Quý, Năm, Tất cả)
 * Biểu đồ xu hướng tài chính (Trend Chart)
 * Tổng hợp & xem chi tiết từng danh mục đã có và đã chi tiêu
 */

var reportFilterMode = 'month'; // 'week' | 'month' | 'year'
var selectedReportYear = new Date().getFullYear();
var selectedReportMonth = new Date().getMonth() + 1; // 1-12
var selectedReportWeekDate = new Date(); // Ngày mốc để xác định tuần
var reportCategoryFilter = 'all'; // 'all' | 'spent_only'
var expandedReportCats = new Set();
var reportChartInstance = null;

// Chuyển đổi chế độ lọc khoảng thời gian (Tuần / Tháng / Năm)
function setReportFilterMode(mode) {
    reportFilterMode = mode;

    const modes = ['week', 'month', 'year'];
    modes.forEach(m => {
        const btn = document.getElementById(`rf-mode-${m}`);
        if (!btn) return;
        if (m === mode) {
            btn.className = "flex-1 py-1.5 rounded-lg bg-teal-600 text-white shadow-xs transition";
        } else {
            btn.className = "flex-1 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 transition";
        }
    });

    updateReportSummary();
}

// Điều hướng lùi/tiến khoảng thời gian (Tuần / Tháng / Năm)
function navigateReportPeriod(direction) {
    if (reportFilterMode === 'week') {
        selectedReportWeekDate.setDate(selectedReportWeekDate.getDate() + direction * 7);
    } else if (reportFilterMode === 'month') {
        selectedReportMonth += direction;
        if (selectedReportMonth > 12) {
            selectedReportMonth = 1;
            selectedReportYear += 1;
        } else if (selectedReportMonth < 1) {
            selectedReportMonth = 12;
            selectedReportYear -= 1;
        }
    } else if (reportFilterMode === 'year') {
        selectedReportYear += direction;
    }

    updateReportSummary();
}

// Reset về thời gian hiện tại
function resetReportPeriodToCurrent() {
    const now = new Date();
    selectedReportYear = now.getFullYear();
    selectedReportMonth = now.getMonth() + 1;
    selectedReportWeekDate = new Date();
    updateReportSummary();
}

// Lọc danh mục: Tất cả vs Chỉ danh mục có phát sinh chi tiêu
function setReportCatFilter(filter) {
    reportCategoryFilter = filter;
    const btnAll = document.getElementById('rcat-filter-all');
    const btnSpent = document.getElementById('rcat-filter-spent');

    if (btnAll && btnSpent) {
        if (filter === 'all') {
            btnAll.className = "px-2 py-1 rounded-md bg-white text-teal-700 shadow-2xs transition";
            btnSpent.className = "px-2 py-1 rounded-md text-slate-600 transition";
        } else {
            btnAll.className = "px-2 py-1 rounded-md text-slate-600 transition";
            btnSpent.className = "px-2 py-1 rounded-md bg-white text-teal-700 shadow-2xs transition";
        }
    }

    renderReportCategoryBreakdown();
}

// Mở/đóng chi tiết giao dịch của 1 danh mục
function toggleReportCatDetail(catId) {
    const idStr = String(catId);
    if (expandedReportCats.has(idStr)) {
        expandedReportCats.delete(idStr);
    } else {
        expandedReportCats.add(idStr);
    }
    renderReportCategoryBreakdown();
}

// Tính khoảng thời gian bắt đầu và kết thúc (Tuần, Tháng, Năm)
function getReportPeriodRange() {
    let startDate = null;
    let endDate = null;
    let label = "";
    let sublabel = "";
    let badgeText = "";

    const pad = (n) => String(n).padStart(2, '0');

    if (reportFilterMode === 'week') {
        const d = new Date(selectedReportWeekDate);
        const day = d.getDay(); // 0: CN, 1: T2...
        const diffToMonday = (day === 0 ? -6 : 1 - day);

        startDate = new Date(d);
        startDate.setDate(d.getDate() + diffToMonday);
        startDate.setHours(0, 0, 0, 0);

        endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + 6);
        endDate.setHours(23, 59, 59, 999);

        // Kiểm tra xem có trùng tuần hiện tại không
        const now = new Date();
        const nowDay = now.getDay();
        const nowDiff = (nowDay === 0 ? -6 : 1 - nowDay);
        const curMonday = new Date(now);
        curMonday.setDate(now.getDate() + nowDiff);
        curMonday.setHours(0, 0, 0, 0);

        const isCurrentWeek = (startDate.getTime() === curMonday.getTime());
        label = isCurrentWeek
            ? `Tuần Này (${pad(startDate.getDate())}/${pad(startDate.getMonth() + 1)} - ${pad(endDate.getDate())}/${pad(endDate.getMonth() + 1)})`
            : `Tuần ${pad(startDate.getDate())}/${pad(startDate.getMonth() + 1)} - ${pad(endDate.getDate())}/${pad(endDate.getMonth() + 1)}`;
        sublabel = `${pad(startDate.getDate())}/${pad(startDate.getMonth() + 1)}/${startDate.getFullYear()} - ${pad(endDate.getDate())}/${pad(endDate.getMonth() + 1)}/${endDate.getFullYear()}`;
        badgeText = isCurrentWeek ? "Tuần này" : `Tuần ${pad(startDate.getDate())}/${pad(startDate.getMonth() + 1)}`;
    } else if (reportFilterMode === 'month') {
        startDate = new Date(selectedReportYear, selectedReportMonth - 1, 1, 0, 0, 0, 0);
        endDate = new Date(selectedReportYear, selectedReportMonth, 0, 23, 59, 59, 999);
        label = `Tháng ${pad(selectedReportMonth)}/${selectedReportYear}`;
        sublabel = `01/${pad(selectedReportMonth)}/${selectedReportYear} - ${endDate.getDate()}/${pad(selectedReportMonth)}/${selectedReportYear}`;
        badgeText = `Tháng ${pad(selectedReportMonth)}/${selectedReportYear}`;
    } else if (reportFilterMode === 'year') {
        startDate = new Date(selectedReportYear, 0, 1, 0, 0, 0, 0);
        endDate = new Date(selectedReportYear, 11, 31, 23, 59, 59, 999);
        label = `Năm ${selectedReportYear}`;
        sublabel = `01/01/${selectedReportYear} - 31/12/${selectedReportYear}`;
        badgeText = `Năm ${selectedReportYear}`;
    }

    return { startDate, endDate, label, sublabel, badgeText };
}

// Kiểm tra loại trừ giao dịch hoàn tiền nội bộ hoặc mục tiêu đã xóa
function isExcludedTx(t) {
    const note = (t.note || t.ghi_chu || '').toLowerCase();
    return note.includes('(đã xoá)') || note.includes('(đã xóa)') ||
        note.includes('hoàn tiền từ hũ tiết kiệm') || note.includes('hoàn trả hạn mức');
}

// Phân loại chính xác loại giao dịch: Giao dịch tiết kiệm luôn là CHI
function getTxType(t) {
    const note = (t.note || t.ghi_chu || '').toLowerCase();
    if (note.includes('tiết kiệm') || note.includes('trích quỹ') || note.includes('mục tiêu')) {
        return 'chi';
    }
    if (t.type === 'thu' || t.loai_gd === 'thu') {
        return 'thu';
    }
    return 'chi';
}

// Parse Date của giao dịch an toàn
function parseTxDateTime(t) {
    const raw = t.date || t.ngay_gd;
    if (!raw) return null;
    const d = new Date(String(raw).replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
}

// Hàm chính cập nhật thống kê báo cáo
function updateReportSummary() {
    const range = getReportPeriodRange();

    // 1. Cập nhật nhãn khoảng thời gian
    const labelEl = document.getElementById('report-period-label');
    const sublabelEl = document.getElementById('report-period-sublabel');
    const badgeEl = document.getElementById('rp-summary-badge');
    if (labelEl) labelEl.innerText = range.label;
    if (sublabelEl) sublabelEl.innerText = range.sublabel;
    if (badgeEl) badgeEl.innerText = range.badgeText;

    // 2. Lọc các giao dịch trong khoảng thời gian đã chọn & loại trừ giao dịch không hợp lệ
    const filteredTxs = allTransactions.filter(t => {
        const d = parseTxDateTime(t);
        if (!d) return false;
        if (range.startDate && d < range.startDate) return false;
        if (range.endDate && d > range.endDate) return false;
        return true;
    });

    const validTxs = filteredTxs.filter(t => !isExcludedTx(t));

    // 3. Tính Tổng Thu và Tổng Chi chuẩn xác tuyệt đối
    let tThu = validTxs.filter(t => getTxType(t) === 'thu')
        .reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);

    let validChiTxs = validTxs.filter(t => getTxType(t) === 'chi');
    let tChi = validChiTxs.reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);

    // Tiết kiệm ròng và Tỷ lệ tiết kiệm
    let netSavings = tThu - tChi;
    let savingsRate = tThu > 0 ? Math.round((netSavings / tThu) * 100) : 0;

    const thuEl = document.getElementById('rp-thu');
    const chiEl = document.getElementById('rp-chi');
    const netSavingsEl = document.getElementById('rp-net-savings');
    const savingsRateEl = document.getElementById('rp-savings-rate');

    if (thuEl) thuEl.innerText = tThu.toLocaleString() + " đ";
    if (chiEl) chiEl.innerText = tChi.toLocaleString() + " đ";
    if (netSavingsEl) {
        netSavingsEl.innerText = (netSavings >= 0 ? "+" : "") + netSavings.toLocaleString() + " đ";
        netSavingsEl.className = netSavings >= 0 ? "font-bold text-teal-300 text-xs" : "font-bold text-rose-300 text-xs";
    }
    if (savingsRateEl) {
        savingsRateEl.innerText = `(${savingsRate}%)`;
    }

    // 4. Vẽ biểu đồ xu hướng chuẩn xác theo dữ liệu hệ thống
    renderReportTrendChart(validTxs, range);

    // 5. Tổng hợp & phân bổ chi tiết danh mục
    renderReportCategoryBreakdown(validChiTxs, tChi, range);
}

// Vẽ biểu đồ xu hướng thu - chi (Trend Chart với Chart.js chuẩn dữ liệu hệ thống)
function renderReportTrendChart(validTxs, range) {
    const canvas = document.getElementById('report-trend-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    let labels = [];
    let thuData = [];
    let chiData = [];
    const pad = (n) => String(n).padStart(2, '0');

    if (reportFilterMode === 'week') {
        // 7 ngày trong tuần từ Thứ Hai đến Chủ Nhật
        const dNames = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
        labels = [];
        for (let i = 0; i < 7; i++) {
            const dayDate = new Date(range.startDate);
            dayDate.setDate(range.startDate.getDate() + i);
            labels.push(`${dNames[i]} (${pad(dayDate.getDate())})`);
        }
        thuData = new Array(7).fill(0);
        chiData = new Array(7).fill(0);

        validTxs.forEach(t => {
            const d = parseTxDateTime(t);
            if (!d) return;
            const dayDiff = Math.floor((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - new Date(range.startDate.getFullYear(), range.startDate.getMonth(), range.startDate.getDate())) / (1000 * 60 * 60 * 24));
            if (dayDiff >= 0 && dayDiff < 7) {
                const amt = t.amount || t.so_tien || 0;
                const type = getTxType(t);
                if (type === 'thu') {
                    thuData[dayDiff] += amt;
                } else if (type === 'chi') {
                    chiData[dayDiff] += amt;
                }
            }
        });
    } else if (reportFilterMode === 'month') {
        // Chia tháng thành 5 chặng ngày chuẩn xác theo số ngày thực tế trong tháng
        const lastDay = new Date(selectedReportYear, selectedReportMonth, 0).getDate();
        labels = ['01-06', '07-12', '13-18', '19-24', `25-${lastDay}`];
        thuData = [0, 0, 0, 0, 0];
        chiData = [0, 0, 0, 0, 0];

        validTxs.forEach(t => {
            const d = parseTxDateTime(t);
            if (!d) return;
            const day = d.getDate();
            let idx = 0;
            if (day <= 6) idx = 0;
            else if (day <= 12) idx = 1;
            else if (day <= 18) idx = 2;
            else if (day <= 24) idx = 3;
            else idx = 4;

            const amt = t.amount || t.so_tien || 0;
            const type = getTxType(t);
            if (type === 'thu') {
                thuData[idx] += amt;
            } else if (type === 'chi') {
                chiData[idx] += amt;
            }
        });
    } else if (reportFilterMode === 'year') {
        // 12 tháng trong năm
        labels = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'];
        thuData = new Array(12).fill(0);
        chiData = new Array(12).fill(0);

        validTxs.forEach(t => {
            const d = parseTxDateTime(t);
            if (!d) return;
            const idx = d.getMonth();
            if (idx >= 0 && idx < 12) {
                const amt = t.amount || t.so_tien || 0;
                const type = getTxType(t);
                if (type === 'thu') {
                    thuData[idx] += amt;
                } else if (type === 'chi') {
                    chiData[idx] += amt;
                }
            }
        });
    }

    if (reportChartInstance) {
        reportChartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');
    reportChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Thu nhập',
                    data: thuData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    fill: true,
                    tension: 0.1, // Chuẩn xác qua các đỉnh điểm dữ liệu, không làm vồng méo số liệu
                    borderWidth: 2.2,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1.5,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Chi tiêu',
                    data: chiData,
                    borderColor: '#f43f5e',
                    backgroundColor: 'rgba(244, 63, 94, 0.12)',
                    fill: true,
                    tension: 0.1, // Chuẩn xác qua các đỉnh điểm dữ liệu
                    borderWidth: 2.2,
                    pointBackgroundColor: '#f43f5e',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1.5,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.94)',
                    titleFont: { size: 11, weight: 'bold' },
                    bodyFont: { size: 10.5 },
                    padding: 9,
                    cornerRadius: 10,
                    callbacks: {
                        title: function (context) {
                            if (!context || !context[0]) return '';
                            const idx = context[0].dataIndex;
                            const lbl = labels[idx];
                            if (reportFilterMode === 'week') {
                                const dayDate = new Date(range.startDate);
                                dayDate.setDate(range.startDate.getDate() + idx);
                                return `${lbl} - Ngày ${pad(dayDate.getDate())}/${pad(dayDate.getMonth() + 1)}/${dayDate.getFullYear()}`;
                            } else if (reportFilterMode === 'month') {
                                return `Giai đoạn: ${lbl}/${String(selectedReportMonth).padStart(2, '0')}/${selectedReportYear}`;
                            } else if (reportFilterMode === 'year') {
                                return `Tháng ${idx + 1}/${selectedReportYear}`;
                            }
                            return `Thời gian: ${lbl}`;
                        },
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            const val = context.parsed.y !== null ? context.parsed.y : 0;
                            return `  ${label}${val.toLocaleString()} đ`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: { size: 9.5, weight: '600' },
                        color: '#64748b'
                    }
                },
                y: {
                    beginAtZero: true,
                    grace: '8%',
                    grid: {
                        color: 'rgba(226, 232, 240, 0.6)',
                        strokeDash: [3, 3]
                    },
                    ticks: {
                        font: { size: 9 },
                        color: '#94a3b8',
                        maxTicksLimit: 5,
                        callback: function (value) {
                            if (value >= 1000000) return (value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 1) + 'M';
                            if (value >= 1000) return (value / 1000).toFixed(0) + 'k';
                            return value;
                        }
                    }
                }
            }
        }
    });
}

// Tổng hợp phân bổ theo danh mục & xem chi tiết các giao dịch trong danh mục
function renderReportCategoryBreakdown(validChiTxs, tChi, range) {
    if (!validChiTxs || tChi === undefined || !range) {
        range = getReportPeriodRange();
        const filteredTxs = allTransactions.filter(t => {
            const d = parseTxDateTime(t);
            if (!d) return false;
            if (range.startDate && d < range.startDate) return false;
            if (range.endDate && d > range.endDate) return false;
            return true;
        });
        validChiTxs = filteredTxs.filter(t => (t.type === 'chi' || t.loai_gd === 'chi') && !isExcludedTx(t));
        tChi = validChiTxs.reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
    }

    const container = document.getElementById('category-pie-chart');
    if (!container) return;

    // Gom giao dịch theo ID danh mục
    const catMap = {};
    const catTxsMap = {};

    allCategories.forEach(c => {
        const cId = String(c.id || c.ma_dm);
        catMap[cId] = c;
        catTxsMap[cId] = [];
    });

    // Thêm danh mục ảo "Khác" nếu có giao dịch không rõ
    catTxsMap['other'] = [];

    validChiTxs.forEach(t => {
        let cId = String(t.category_id || t.ma_dm || 'other');
        const note = (t.note || t.ghi_chu || '').toLowerCase();

        // Kiểm tra chuyển vào hũ tiết kiệm
        if (note.includes('tiết kiệm') || note.includes('mục tiêu')) {
            const tkCat = allCategories.find(c => (c.name || c.ten_dm || '').toLowerCase().includes('tiết kiệm'));
            if (tkCat) cId = String(tkCat.id || tkCat.ma_dm);
        }

        if (!catTxsMap[cId]) {
            catTxsMap[cId] = [];
        }
        catTxsMap[cId].push(t);
    });

    // Danh sách các danh mục chi tiêu cần hiển thị
    let displayCats = allCategories.filter(c => c.type === 'chi' || c.loai_dm === 'chi');
    if (displayCats.length === 0) {
        displayCats = allCategories;
    }

    // Nếu chọn bộ lọc "Chỉ có chi tiêu"
    if (reportCategoryFilter === 'spent_only') {
        displayCats = displayCats.filter(c => {
            const cId = String(c.id || c.ma_dm);
            const txs = catTxsMap[cId] || [];
            return txs.length > 0;
        });
    }

    if (displayCats.length === 0) {
        container.innerHTML = `
            <div class="text-center py-6 text-slate-400 text-xs">
                <span class="text-2xl block mb-1">📭</span>
                Chưa có dữ liệu chi tiêu trong khoảng thời gian này.
            </div>`;
        return;
    }

    // Sắp xếp danh mục theo số tiền đã chi giảm dần
    displayCats.sort((a, b) => {
        const idA = String(a.id || a.ma_dm);
        const idB = String(b.id || b.ma_dm);
        const spentA = (catTxsMap[idA] || []).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
        const spentB = (catTxsMap[idB] || []).reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
        return spentB - spentA;
    });

    const colors = [
        { bg: 'bg-teal-500', bar: 'bg-teal-500', text: 'text-teal-700', badge: 'bg-teal-50 text-teal-700' },
        { bg: 'bg-sky-500', bar: 'bg-sky-500', text: 'text-sky-700', badge: 'bg-sky-50 text-sky-700' },
        { bg: 'bg-indigo-500', bar: 'bg-indigo-500', text: 'text-indigo-700', badge: 'bg-indigo-50 text-indigo-700' },
        { bg: 'bg-amber-500', bar: 'bg-amber-500', text: 'text-amber-700', badge: 'bg-amber-50 text-amber-700' },
        { bg: 'bg-rose-500', bar: 'bg-rose-500', text: 'text-rose-700', badge: 'bg-rose-50 text-rose-700' },
        { bg: 'bg-purple-500', bar: 'bg-purple-500', text: 'text-purple-700', badge: 'bg-purple-50 text-purple-700' }
    ];

    let html = '';

    displayCats.forEach((c, idx) => {
        const cId = String(c.id || c.ma_dm);
        const cName = c.name || c.ten_dm || 'Danh mục';
        const isSavingsCat = (cName || '').toLowerCase().includes('tiết kiệm') || (cName || '').toLowerCase().includes('tiet kiem');
        const txs = catTxsMap[cId] || [];
        const spentAmount = txs.reduce((s, t) => s + (t.amount || t.so_tien || 0), 0);
        const txCount = txs.length;

        // Tính các chỉ số cho danh mục Tiết Kiệm (tổng mục tiêu, số tiền cần để đạt)
        let totalSavingsTarget = 0;
        let totalSavingsCurrent = 0;
        let totalSavingsNeeded = 0;
        if (isSavingsCat) {
            const goals = Array.isArray(window.allSavingsGoals) ? window.allSavingsGoals : [];
            goals.forEach(g => {
                const tgt = parseFloat(g.target_amount || g.so_tien_muc_tieu || 0) || 0;
                const cur = parseFloat(g.current_amount || g.so_tien_hien_tai || 0) || 0;
                totalSavingsTarget += tgt;
                totalSavingsCurrent += cur;
                totalSavingsNeeded += Math.max(0, tgt - cur);
            });
        }

        // Tỷ lệ % so với tổng chi kỳ này
        const pctOfTotal = tChi > 0 ? Math.round((spentAmount / tChi) * 100) : 0;

        // Hạn mức quy đổi theo khoảng thời gian
        let baseLimit = parseFloat(c.limit || c.han_muc || 0);
        let periodLimit = baseLimit;
        if (reportFilterMode === 'quarter') periodLimit = baseLimit * 3;
        else if (reportFilterMode === 'year') periodLimit = baseLimit * 12;

        let pctOfLimit = periodLimit > 0 ? Math.round((spentAmount / periodLimit) * 100) : null;
        let remaining = periodLimit > 0 ? Math.max(0, periodLimit - spentAmount) : null;

        const theme = colors[idx % colors.length];

        // Màu thanh tiến độ ngân sách thông minh
        let progressBarClass = theme.bar;
        let limitBadgeClass = "bg-slate-100 text-slate-600";
        if (pctOfLimit !== null) {
            if (pctOfLimit >= 100) {
                progressBarClass = "bg-rose-500";
                limitBadgeClass = "bg-rose-100 text-rose-700 font-bold";
            } else if (pctOfLimit >= 90) {
                progressBarClass = "bg-amber-500";
                limitBadgeClass = "bg-amber-100 text-amber-800 font-bold";
            } else if (pctOfLimit >= 70) {
                progressBarClass = "bg-yellow-500";
                limitBadgeClass = "bg-yellow-100 text-yellow-800";
            } else {
                progressBarClass = "bg-teal-500";
                limitBadgeClass = "bg-teal-100 text-teal-800";
            }
        }

        // Cấu hình hiển thị thanh tiến độ: nếu là Tiết kiệm thì hiển thị tiến độ đạt tổng mục tiêu
        let headerLimitText = periodLimit > 0 ? `Hạn mức: ${periodLimit.toLocaleString()} đ` : 'Chưa đặt hạn mức';
        let headerBadgeHtml = pctOfLimit !== null ? `<span class="px-1.5 py-0.2 rounded-full ${limitBadgeClass}">Đã dùng ${pctOfLimit}%</span>` : '';
        let headerBarWidth = pctOfLimit !== null ? Math.min(100, pctOfLimit) : pctOfTotal;
        let headerBarClass = progressBarClass;

        if (isSavingsCat) {
            if (totalSavingsTarget > 0) {
                const savingsPct = Math.min(100, Math.round((totalSavingsCurrent / totalSavingsTarget) * 100));
                headerLimitText = `Tổng mục tiêu: ${totalSavingsTarget.toLocaleString('vi-VN')} đ`;
                headerBadgeHtml = `<span class="px-1.5 py-0.2 rounded-full bg-teal-100 text-teal-800 font-bold">Đã đạt ${savingsPct}%</span>`;
                headerBarWidth = savingsPct;
                headerBarClass = "bg-teal-500";
            } else {
                headerLimitText = "Chưa có mục tiêu";
                headerBadgeHtml = "";
                headerBarWidth = 0;
            }
        }

        const isExpanded = expandedReportCats.has(cId);

        // Danh sách giao dịch chi tiết trong danh mục
        let txsListHtml = '';
        if (txCount === 0) {
            txsListHtml = `
                <div class="py-2.5 text-center text-[11px] text-slate-400 italic">
                    Chưa có giao dịch chi tiêu trong kỳ này.
                </div>`;
        } else {
            // Sắp xếp giao dịch mới nhất lên đầu
            const sortedTxs = [...txs].sort((a, b) => {
                const da = parseTxDateTime(a) || 0;
                const db = parseTxDateTime(b) || 0;
                return db - da;
            });

            txsListHtml = sortedTxs.map(t => {
                const d = parseTxDateTime(t);
                const dateStr = d ? `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}` : '---';
                const timeStr = d ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : '';
                const amt = Math.abs(t.amount || t.so_tien || 0);
                const amountFormatted = amt.toLocaleString('vi-VN') + ' đ';
                const rawNote = t.note || t.ghi_chu || 'Chi tiêu hũ';
                // Bỏ chữ "tiết kiệm", chỉ để "Mục tiêu" (Ví dụ: "Mục tiêu: Du lịch")
                const noteStr = rawNote.replace(/mục tiêu tiết kiệm\s*:/gi, 'Mục tiêu:').replace(/mục tiêu tiết kiệm/gi, 'Mục tiêu');

                const sign = isSavingsCat ? '+' : '-';
                const amountColor = isSavingsCat ? 'text-teal-600' : 'text-rose-600';

                return `
                    <div class="flex items-center justify-between py-2 border-b border-slate-100 last:border-b-0 text-xs">
                        <div class="min-w-0 pr-2">
                            <div class="font-medium text-slate-700 truncate">${noteStr}</div>
                            <div class="text-[10px] text-slate-400 flex items-center gap-1">
                                <span>🗓️ ${dateStr}</span>
                                ${timeStr ? `<span>• ${timeStr}</span>` : ''}
                            </div>
                        </div>
                        <div class="font-bold ${amountColor} shrink-0 whitespace-nowrap text-right">
                            ${sign}${amountFormatted}
                        </div>
                    </div>`;
            }).join('');
        }

        html += `
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-hidden transition-all duration-200">
                <!-- Header danh mục: bấm để mở rộng/thu gọn -->
                <div onclick="toggleReportCatDetail('${cId}')" class="p-3.5 cursor-pointer hover:bg-slate-50/80 transition flex flex-col gap-2">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <span class="w-8 h-8 rounded-xl ${theme.badge} font-bold flex items-center justify-center text-xs shrink-0 shadow-2xs">
                                📁
                            </span>
                            <div class="min-w-0">
                                <h4 class="text-xs font-bold text-slate-800 truncate">${cName}</h4>
                                <span class="text-[10px] text-slate-400 font-medium">${txCount} giao dịch</span>
                            </div>
                        </div>

                        <div class="text-right shrink-0">
                            <div class="text-xs font-bold text-slate-800">${spentAmount.toLocaleString()} đ</div>
                            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-full ${theme.badge}">
                                ${pctOfTotal}% tổng chi
                            </span>
                        </div>
                    </div>

                    <!-- Thanh tiến độ ngân sách hoặc tỷ lệ chi -->
                    <div class="space-y-1 pt-1">
                        <div class="flex justify-between items-center text-[10px]">
                            <span class="text-slate-500 font-medium">
                                ${headerLimitText}
                            </span>
                            ${headerBadgeHtml}
                        </div>
                        <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div class="${headerBarClass} h-full transition-all duration-300 rounded-full" style="width: ${headerBarWidth}%"></div>
                        </div>
                    </div>

                    <!-- Nút xem chi tiết có mũi tên xoay -->
                    <div class="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px] text-teal-700 font-bold">
                        <span>${isExpanded ? 'Ẩn chi tiết danh mục' : 'Xem chi tiết các giao dịch'}</span>
                        <span class="transition-transform duration-200 text-xs ${isExpanded ? 'rotate-180 text-teal-800' : 'text-slate-400'}">▼</span>
                    </div>
                </div>

                <!-- Khung Accordion mở rộng chi tiết giao dịch -->
                <div class="${isExpanded ? 'block' : 'hidden'} bg-slate-50/70 border-t border-slate-200/80 p-3 space-y-2.5 animate-in fade-in duration-200">
                    <!-- Thẻ tóm tắt thông số của riêng danh mục này -->
                    <div class="grid grid-cols-3 gap-1.5 text-center text-[10px] bg-white p-2 rounded-xl border border-slate-200/70 shadow-2xs">
                        <div class="p-1">
                            <div class="text-slate-400 font-medium">${isSavingsCat ? 'Tổng mục tiêu' : 'Hạn mức'}</div>
                            <div class="font-bold text-slate-700 mt-0.5 truncate" title="${isSavingsCat ? (totalSavingsTarget > 0 ? totalSavingsTarget.toLocaleString('vi-VN') + ' đ' : '0 đ') : (periodLimit > 0 ? periodLimit.toLocaleString() + 'đ' : '---')}">
                                ${isSavingsCat ? (totalSavingsTarget > 0 ? totalSavingsTarget.toLocaleString('vi-VN') + ' đ' : '0 đ') : (periodLimit > 0 ? periodLimit.toLocaleString() + 'đ' : '---')}
                            </div>
                        </div>
                        <div class="p-1 border-x border-slate-100">
                            <div class="text-slate-400 font-medium">${isSavingsCat ? 'Đã tiết kiệm được' : 'Đã chi kỳ này'}</div>
                            <div class="font-bold ${isSavingsCat ? 'text-teal-700' : 'text-rose-600'} mt-0.5 truncate" title="${spentAmount.toLocaleString('vi-VN')} đ">${spentAmount.toLocaleString()}đ</div>
                        </div>
                        <div class="p-1">
                            <div class="text-slate-400 font-medium" title="${isSavingsCat ? 'Cần thêm' : 'Ngân sách còn lại'}">${isSavingsCat ? 'Số tiền cần' : 'Còn lại'}</div>
                            <div class="font-bold text-teal-700 mt-0.5 truncate" title="${isSavingsCat ? (totalSavingsNeeded.toLocaleString('vi-VN') + ' đ') : (remaining !== null ? remaining.toLocaleString() + 'đ' : '---')}">
                                ${isSavingsCat ? (totalSavingsNeeded.toLocaleString('vi-VN') + ' đ') : (remaining !== null ? remaining.toLocaleString() + 'đ' : '---')}
                            </div>
                        </div>
                    </div>

                    <!-- Danh sách các giao dịch cụ thể -->
                    <div class="space-y-1">
                        <div class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">
                            Giao dịch trong kỳ (${txCount})
                        </div>
                        <div class="bg-white rounded-xl border border-slate-200/70 px-3 py-1 shadow-2xs divide-y divide-slate-100 max-h-48 overflow-y-auto pr-1">
                            ${txsListHtml}
                        </div>
                    </div>
                </div>
            </div>`;
    });

    container.innerHTML = html;
}
