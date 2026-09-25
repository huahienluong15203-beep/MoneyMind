/**
 * MoneyMind - Trung Tâm Thông Báo & Cảnh Báo
 */
            function closeNotificationDetailModal() {
                document.getElementById('notification-detail-modal').classList.add('hidden');
            }


            function handleTopNotifClick() {
                if (currentSection === 'thong-bao') {
                    switchSection('quan-ly');
                } else {
                    switchSection('thong-bao');
                }
            }


            async function loadNotifications() {
                if(!token) return;
                try {
                    const res = await fetch('/api/notifications', {headers: {'Authorization': 'Bearer ' + token}});
                    if(res.ok) {
                        allNotifications = await res.json();
                        renderNotificationsList();
                    }
                } catch(e) {
                    console.error("Lỗi tải thông báo:", e);
                }
            }


            async function markAllNotificationsAsRead() {
                if(!token) return;
                const hasUnread = allNotifications.some(n => !n.da_xem && !n.is_read);
                if(!hasUnread) {
                    if(allNotifications.length === 0) return;
                    showCustomModal("Thông báo", "Tất cả thông báo đã ở trạng thái đã xem rồi!", "ℹ️");
                    return;
                }
                allNotifications.forEach(n => {
                    n.da_xem = true;
                    n.is_read = true;
                });
                renderNotificationsList();

                try {
                    await fetch('/api/notifications/read-all', {
                        method: 'PUT',
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                } catch(e) {
                    console.error("Lỗi đánh dấu tất cả đã đọc:", e);
                }
            }


            function renderNotificationsList() {
                const container = document.getElementById('notifications-list');
                const loadMoreWrapper = document.getElementById('notifs-load-more-wrapper');
                const countBadge = document.getElementById('notif-count-badge');
                if(!container) return;

                if(!allNotifications || allNotifications.length === 0) {
                    container.innerHTML = `
                        <div class="text-center py-10 space-y-2">
                            <span class="text-3xl">📭</span>
                            <p class="text-xs font-bold text-slate-500">Chưa có thông báo hoặc cảnh báo nào</p>
                            <p class="text-[11px] text-slate-400">Các cảnh báo chi tiêu, trích ví và biến động tài chính sẽ được ghi nhận tại đây.</p>
                        </div>
                    `;
                    if(loadMoreWrapper) loadMoreWrapper.classList.add('hidden');
                    if(countBadge) countBadge.innerText = "0 thông báo";
                    const topBadge = document.getElementById('top-notif-badge');
                    if(topBadge) topBadge.classList.add('hidden');
                    return;
                }

                const total = allNotifications.length;
                const unreadCount = allNotifications.filter(n => !n.da_xem && !n.is_read).length;
                const visibleCount = Math.min(notifDisplayLimit, total);

                if(countBadge) {
                    countBadge.innerText = `${total} thông báo`;
                }

                const topBadge = document.getElementById('top-notif-badge');
                if(topBadge) {
                    if(unreadCount > 0) {
                        topBadge.innerText = unreadCount > 99 ? '99+' : unreadCount;
                        topBadge.classList.remove('hidden');
                    } else {
                        topBadge.classList.add('hidden');
                    }
                }

                const visibleItems = allNotifications.slice(0, visibleCount);
                container.innerHTML = "";

                visibleItems.forEach((n, idx) => {
                    let title = n.title || n.tieu_de || "Thông báo";
                    let rawMessage = n.message || n.noi_dung || "";
                    let message = rawMessage.replace(/\\n/g, '\n');
                    let timeStr = n.created_at || n.ngay_tao || "";
                    let compactTime = "Vừa xong";
                    if(timeStr) {
                        try {
                            const d = new Date(timeStr.replace(' ', 'T'));
                            if(!isNaN(d.getTime())) {
                                const hh = String(d.getHours()).padStart(2, '0');
                                const mm = String(d.getMinutes()).padStart(2, '0');
                                const dd = String(d.getDate()).padStart(2, '0');
                                const mo = String(d.getMonth() + 1).padStart(2, '0');
                                compactTime = `${hh}:${mm} • ${dd}/${mo}`;
                            } else {
                                compactTime = timeStr.replace('T', ' ').substring(0, 16);
                            }
                        } catch(e) {
                            compactTime = timeStr.replace('T', ' ').substring(0, 16);
                        }
                    }
                    let isRead = Boolean(n.da_xem || n.is_read);

                    // Trích xuất % thực tế từ nội dung chi tiết hoặc tiêu đề (bỏ qua mẫu cố định "từ 90% trở lên")
                    const cleanTitleForMatch = title.replace(/từ\s*90%\s*trở\s*lên/gi, '').replace(/\(từ\s*90%\s*trở\s*lên\)/gi, '');
                    const messageMatch = message.match(/(\d+)\s*%/);
                    const titleMatch = cleanTitleForMatch.match(/(\d+)\s*%/);
                    const actualPct = messageMatch ? messageMatch[1] : (titleMatch ? titleMatch[1] : null);

                    let icon = "📢";
                    let bgTagClass = "bg-slate-100 text-slate-700";
                    let typeLabel = "Thông tin";

                    if(title.includes("Vượt") || title.includes("🚨") || message.includes("vượt quá")) {
                        icon = "🚨";
                        bgTagClass = "bg-rose-100 text-rose-700";
                        typeLabel = actualPct ? `Vượt hạn mức (${actualPct}%)` : "Vượt hạn mức";
                    } else if(title.includes("Sắp") || title.includes("⚠️") || message.includes("sắp chạm") || message.includes("hạn mức") || message.includes("ngân sách")) {
                        icon = "⚠️";
                        bgTagClass = "bg-amber-100 text-amber-800";
                        typeLabel = actualPct ? `Cảnh báo (${actualPct}%)` : "Cảnh báo";
                    } else if(title.includes("Chúc Mừng") || title.includes("🎉") || title.includes("🏆")) {
                        icon = "🏆";
                        bgTagClass = "bg-emerald-100 text-emerald-800";
                        typeLabel = actualPct ? `Đạt mục tiêu (${actualPct}%)` : "Đạt mục tiêu";
                    } else if(title.includes("Động Viên") || title.includes("🌟") || title.includes("Sắp Đạt")) {
                        icon = "🌟";
                        bgTagClass = "bg-teal-100 text-teal-800";
                        typeLabel = actualPct ? `Động viên (${actualPct}%)` : "Động viên";
                    } else if(title.includes("Hoàn Trả") || title.includes("💰")) {
                        icon = "💰";
                        bgTagClass = "bg-teal-100 text-teal-800";
                        typeLabel = "Hoàn tiền ví";
                    }

                    // Hiển thị % theo thực tế danh mục đó trên tiêu đề thay vì thông điệp chung chung
                    let displayTitle = title;
                    if (actualPct) {
                        displayTitle = displayTitle
                            .replace(/TỪ 90% HẠN MỨC TRỞ LÊN!?/gi, `ĐẠT ${actualPct}% HẠN MỨC!`)
                            .replace(/\(Từ 90% Trở Lên\)!?/gi, `(${actualPct}%)!`);
                    }

                    // Quy tắc: Đã xem thì nền trắng, chưa xem thì nền xanh da trời
                    const cardBgClass = isRead 
                        ? "bg-white border-slate-200/90 hover:border-teal-400 shadow-2xs" 
                        : "bg-sky-100 border-sky-300 hover:border-sky-400 shadow-xs ring-1 ring-sky-200/60";

                    const titleColorClass = isRead ? "text-slate-800 font-semibold" : "text-sky-950 font-bold";
                    const messageColorClass = isRead ? "text-slate-500" : "text-slate-700";

                    container.innerHTML += `
                        <div onclick="openNotificationDetailModal(${idx})" class="p-3.5 rounded-2xl border ${cardBgClass} hover:shadow-md transition cursor-pointer space-y-1.5 group">
                            <!-- Hàng 1: Icon + Loại thông báo kèm % thực tế bên trái, Thời gian bên phải -->
                            <div class="flex items-center justify-between gap-2">
                                <div class="flex items-center gap-1.5 min-w-0">
                                    <span class="text-sm shrink-0">${icon}</span>
                                    <span class="text-[9px] ${bgTagClass} px-2 py-0.5 rounded-full font-bold shrink-0 whitespace-nowrap">${typeLabel}</span>
                                </div>
                                <span class="text-[10px] text-slate-400 whitespace-nowrap shrink-0">🕒 ${compactTime}</span>
                            </div>

                            <!-- Hàng 2: Tiêu đề toàn bộ chiều ngang hiển thị % thực tế -->
                            <h4 class="${titleColorClass} text-xs group-hover:text-teal-700 transition leading-snug break-words">
                                ${displayTitle}
                            </h4>

                            <!-- Hàng 3: Nội dung tóm tắt tối đa 2 dòng -->
                            <p class="text-[11px] ${messageColorClass} leading-relaxed line-clamp-2">${message}</p>

                            <!-- Hàng 4: Nút chi tiết góc phải -->
                            <div class="flex justify-end pt-0.5">
                                <span class="text-[10px] font-bold text-teal-600 group-hover:underline flex items-center gap-0.5 whitespace-nowrap">
                                    <span>Xem chi tiết</span>
                                    <span>➔</span>
                                </span>
                            </div>
                        </div>
                    `;
                });

                if(loadMoreWrapper) {
                    if(total > visibleCount) {
                        loadMoreWrapper.classList.remove('hidden');
                        const remaining = total - visibleCount;
                        const btnText = document.getElementById('load-more-count-text');
                        if(btnText) btnText.innerText = `(còn ${remaining} thông báo)`;
                    } else {
                        loadMoreWrapper.classList.add('hidden');
                    }
                }
            }


            function loadMoreNotifications() {
                notifDisplayLimit += 15;
                renderNotificationsList();
            }


            function openNotificationDetailModal(idx) {
                const n = allNotifications[idx];
                if(!n) return;
                let title = n.title || n.tieu_de || "Thông báo";
                const rawMessage = n.message || n.noi_dung || "";
                const message = rawMessage.replace(/\\n/g, '\n');
                const timeStr = n.created_at || n.ngay_tao || "";
                const formattedTime = timeStr ? timeStr.replace('T', ' ').substring(0, 19) : "";

                // Trích xuất % thực tế từ nội dung chi tiết hoặc tiêu đề (bỏ qua mẫu cố định "từ 90% trở lên")
                const cleanTitleForMatch = title.replace(/từ\s*90%\s*trở\s*lên/gi, '').replace(/\(từ\s*90%\s*trở\s*lên\)/gi, '');
                const messageMatch = message.match(/(\d+)\s*%/);
                const titleMatch = cleanTitleForMatch.match(/(\d+)\s*%/);
                const actualPct = messageMatch ? messageMatch[1] : (titleMatch ? titleMatch[1] : null);

                if (actualPct) {
                    title = title
                        .replace(/TỪ 90% HẠN MỨC TRỞ LÊN!?/gi, `ĐẠT ${actualPct}% HẠN MỨC!`)
                        .replace(/\(Từ 90% Trở Lên\)!?/gi, `(${actualPct}%)!`);
                }

                let icon = "📢";
                let badge = "THÔNG BÁO";
                let badgeClass = "bg-slate-100 text-slate-700";

                if(title.includes("Vượt") || title.includes("🚨") || message.includes("vượt quá")) {
                    icon = "🚨";
                    badge = actualPct ? `CẢNH BÁO VƯỢT HẠN MỨC (${actualPct}%)` : "CẢNH BÁO VƯỢT HẠN MỨC";
                    badgeClass = "bg-rose-100 text-rose-700";
                } else if(title.includes("Sắp") || title.includes("⚠️") || message.includes("sắp chạm") || message.includes("hạn mức") || message.includes("ngân sách")) {
                    icon = "⚠️";
                    badge = actualPct ? `CẢNH BÁO SẮP CHẠM HẠN MỨC (${actualPct}%)` : "CẢNH BÁO SẮP CHẠM HẠN MỨC";
                    badgeClass = "bg-amber-100 text-amber-800";
                } else if(title.includes("Chúc Mừng") || title.includes("🎉") || title.includes("🏆")) {
                    icon = "🏆";
                    badge = actualPct ? `CHÚC MỪNG HOÀN THÀNH MỤC TIÊU (${actualPct}%)` : "CHÚC MỪNG HOÀN THÀNH MỤC TIÊU";
                    badgeClass = "bg-emerald-100 text-emerald-800";
                } else if(title.includes("Động Viên") || title.includes("🌟") || title.includes("Sắp Đạt")) {
                    icon = "🌟";
                    badge = actualPct ? `ĐỘNG VIÊN: SẮP ĐẠT MỤC TIÊU TIẾT KIỆM (${actualPct}%)` : "ĐỘNG VIÊN: SẮP ĐẠT MỤC TIÊU TIẾT KIỆM";
                    badgeClass = "bg-teal-100 text-teal-800";
                } else if(title.includes("Hoàn Trả") || title.includes("💰")) {
                    icon = "💰";
                    badge = "HOÀN TIỀN VỀ VÍ CHÍNH";
                    badgeClass = "bg-teal-100 text-teal-800";
                }

                document.getElementById('notif-detail-icon').innerText = icon;
                const badgeEl = document.getElementById('notif-detail-badge');
                badgeEl.innerText = badge;
                badgeEl.className = `inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold ${badgeClass}`;

                document.getElementById('notif-detail-title').innerText = title;
                document.getElementById('notif-detail-time').innerText = "🕒 " + formattedTime;
                document.getElementById('notif-detail-message').innerText = message;
                document.getElementById('notification-detail-modal').classList.remove('hidden');

                // Nếu thông báo đang ở trạng thái chưa xem, chuyển sang đã xem ngay
                if(!n.da_xem && !n.is_read) {
                    n.da_xem = true;
                    n.is_read = true;
                    renderNotificationsList();
                    if(n.id && token) {
                        fetch(`/api/notifications/${n.id}/read`, {
                            method: 'PUT',
                            headers: {'Authorization': 'Bearer ' + token}
                        }).catch(e => console.error("Lỗi cập nhật đã xem:", e));
                    }
                }
            }

