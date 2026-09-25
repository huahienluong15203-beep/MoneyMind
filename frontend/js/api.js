/**
 * MoneyMind - Core API, Shared State, and Helper Utilities
 */
var token = localStorage.getItem('moneymind_token') || localStorage.getItem('access_token') || '';

function setStoredToken(t) {
    token = t;
    localStorage.setItem('moneymind_token', t);
    localStorage.setItem('access_token', t);
}

function clearStoredToken() {
    token = '';
    localStorage.removeItem('moneymind_token');
    localStorage.removeItem('access_token');
}

var allTransactions = [];
var allCategories = [];
var allSavingsGoals = [];
var allNotifications = [];
var notifDisplayLimit = 15;
var selectedCategoryToDelete = null;
var selectedCategoryId = null;
var customModalCallback = null;

            function showCustomModal(title, message, icon = "✨", onConfirm = null) {
                document.getElementById('modal-title').innerText = title;
                document.getElementById('modal-message').innerText = message;
                document.getElementById('modal-icon').innerText = icon;
                customModalCallback = onConfirm;
                document.getElementById('custom-modal').classList.remove('hidden');
            }
            function closeCustomModal() {
                document.getElementById('custom-modal').classList.add('hidden');
                if (typeof customModalCallback === 'function') {
                    const cb = customModalCallback;
                    customModalCallback = null;
                    cb();
                }
            }


            async function recordNotification(title, message) {
                if(!token) return;
                try {
                    await fetch('/api/notifications', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                        body: JSON.stringify({title, message})
                    });
                } catch(e) {
                    console.error("Lỗi lưu thông báo:", e);
                }
            }


            function getLocalDateString(d = new Date()) {
                const y = d.getFullYear();
                const m = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                return `${y}-${m}-${day}`;
            }

            function formatVNDate(dateStr) {
                if (!dateStr) return 'Không có';
                const clean = String(dateStr).split('T')[0];
                const parts = clean.split('-');
                if (parts.length === 3) {
                    return `${parts[2]}/${parts[1]}/${parts[0]}`;
                }
                return dateStr;
            }

            function formatVNDateFullText(dateStr) {
                if (!dateStr) return '';
                const clean = String(dateStr).split('T')[0];
                const parts = clean.split('-');
                if (parts.length === 3) {
                    const y = parseInt(parts[0], 10);
                    const m = parseInt(parts[1], 10);
                    const d = parseInt(parts[2], 10);
                    return `Ngày ${d < 10 ? '0' + d : d} tháng ${m < 10 ? '0' + m : m} năm ${y}`;
                }
                return '';
            }

            let editSavingsPicker = null;
            let createSavingsPicker = null;


            function getTxTimestamp(t) {
                const raw = t.date || t.ngay_gd;
                if (!raw) return 0;
                if (typeof raw === 'number') return raw;
                const iso = String(raw).replace(' ', 'T');
                const time = new Date(iso).getTime();
                return isNaN(time) ? 0 : time;
            }

