// ========== 工具函数 ==========

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

async function apiRequest(url, method = 'GET', body = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
        window.location.href = '/login';
        return;
    }
    return res.json();
}

// ========== 导航 ==========

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function(e) {
        e.preventDefault();
        const tab = this.dataset.tab;
        switchTab(tab);
    });
});

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tab}`);
    });

    // 切换时加载对应数据
    if (tab === 'friends') loadFriends();
    if (tab === 'cookie') loadCookieConfig();
    if (tab === 'message') loadMessageConfig();
    if (tab === 'email') loadEmailConfig();
    if (tab === 'logs') loadLogs();
    if (tab === 'dashboard') loadStats();
}

// ========== 登出 ==========

async function logout() {
    await apiRequest('/api/logout', 'POST');
    window.location.href = '/login';
}

// ========== 仪表盘 ==========

async function loadStats() {
    const data = await apiRequest('/api/stats');
    if (!data) return;

    document.getElementById('stat-friends').textContent = data.total_friends;
    document.getElementById('stat-cookie').textContent = data.cookie_valid ? '正常' : '异常';
    document.getElementById('stat-today').textContent = data.today_runs;
    document.getElementById('stat-email').textContent = data.email_enabled ? '已开启' : '未开启';
}

// ========== 好友管理 ==========

let editingFriendIndex = -1;

async function loadFriends() {
    const data = await apiRequest('/api/friends');
    if (!data) return;

    const tbody = document.getElementById('friends-tbody');
    const friends = data.friends || [];

    if (friends.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty-state">暂无好友，点击右上角添加</td></tr>`;
        return;
    }

    tbody.innerHTML = friends.map((f, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${escapeHtml(f.nickname || '-')}</td>
            <td><code style="font-size:12px;color:#666;">${escapeHtml(f.sec_uid ? f.sec_uid.substring(0, 20) + '...' : '-')}</code></td>
            <td>${escapeHtml(f.user_id || '-')}</td>
            <td>${escapeHtml(f.remark || '-')}</td>
            <td>
                <div class="table-actions">
                    <button class="btn btn-secondary btn-sm" onclick="editFriend(${i})">编辑</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteFriend(${i})">删除</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function showAddFriendModal() {
    editingFriendIndex = -1;
    document.getElementById('modal-title').textContent = '添加好友';
    document.getElementById('friend-nickname').value = '';
    document.getElementById('friend-secuid').value = '';
    document.getElementById('friend-userid').value = '';
    document.getElementById('friend-remark').value = '';
    document.getElementById('friend-modal').classList.add('show');
}

function editFriend(index) {
    editingFriendIndex = index;
    apiRequest('/api/friends').then(data => {
        const friend = data.friends[index];
        document.getElementById('modal-title').textContent = '编辑好友';
        document.getElementById('friend-nickname').value = friend.nickname || '';
        document.getElementById('friend-secuid').value = friend.sec_uid || '';
        document.getElementById('friend-userid').value = friend.user_id || '';
        document.getElementById('friend-remark').value = friend.remark || '';
        document.getElementById('friend-modal').classList.add('show');
    });
}

function closeFriendModal() {
    document.getElementById('friend-modal').classList.remove('show');
}

async function saveFriend() {
    const friendData = {
        nickname: document.getElementById('friend-nickname').value.trim(),
        sec_uid: document.getElementById('friend-secuid').value.trim(),
        user_id: document.getElementById('friend-userid').value.trim(),
        remark: document.getElementById('friend-remark').value.trim(),
    };

    if (!friendData.nickname && !friendData.sec_uid && !friendData.user_id) {
        showToast('昵称、sec_uid、user_id至少填一个', 'warning');
        return;
    }

    let result;
    if (editingFriendIndex === -1) {
        result = await apiRequest('/api/friends', 'POST', friendData);
    } else {
        result = await apiRequest(`/api/friends/${editingFriendIndex}`, 'PUT', friendData);
    }

    if (result && result.success) {
        showToast(result.message);
        closeFriendModal();
        loadFriends();
        loadStats();
    } else {
        showToast(result?.message || '保存失败', 'error');
    }
}

async function deleteFriend(index) {
    if (!confirm('确定要删除这个好友吗？')) return;

    const result = await apiRequest(`/api/friends/${index}`, 'DELETE');
    if (result && result.success) {
        showToast('删除成功');
        loadFriends();
        loadStats();
    } else {
        showToast(result?.message || '删除失败', 'error');
    }
}

// ========== Cookie设置 ==========

async function loadCookieConfig() {
    const data = await apiRequest('/api/config');
    if (!data) return;

    const douyin = data.douyin || {};
    const statusDot = document.querySelector('#cookie-status .status-dot');
    const statusText = document.getElementById('cookie-status-text');

    if (douyin.cookie_length && douyin.cookie_length > 100) {
        statusDot.classList.add('valid');
        statusText.textContent = `Cookie有效（${douyin.cookie_length}个字符）`;
    } else {
        statusDot.classList.add('invalid');
        statusText.textContent = 'Cookie未设置或过短';
    }

    document.getElementById('headless-checkbox').checked = douyin.headless !== false;
}

async function saveCookieConfig() {
    const cookie = document.getElementById('cookie-input').value.trim();
    const headless = document.getElementById('headless-checkbox').checked;

    const body = { headless };
    if (cookie) body.cookie = cookie;

    const result = await apiRequest('/api/config/douyin', 'POST', body);
    if (result && result.success) {
        showToast('保存成功');
        document.getElementById('cookie-input').value = '';
        loadCookieConfig();
        loadStats();
    } else {
        showToast(result?.message || '保存失败', 'error');
    }
}

// ========== 消息设置 ==========

async function loadMessageConfig() {
    const data = await apiRequest('/api/config');
    if (!data) return;

    const msgApi = data.message_api || {};
    const mode = msgApi.mode || 'mock';

    document.querySelector(`input[name="msg-mode"][value="${mode}"]`).checked = true;
    switchMsgMode(mode);

    if (msgApi.mock && msgApi.mock.messages) {
        document.getElementById('mock-messages').value = msgApi.mock.messages.join('\n');
    }

    if (msgApi.real) {
        document.getElementById('api-url').value = msgApi.real.url || '';
        document.getElementById('api-method').value = msgApi.real.method || 'GET';
        document.getElementById('api-message-path').value = msgApi.real.message_path || '';
        document.getElementById('api-headers').value = JSON.stringify(msgApi.real.headers || {}, null, 2);
    }

    if (msgApi.sticker) {
        document.getElementById('sticker-url').value = msgApi.sticker.url || '';
        document.getElementById('sticker-local').value = msgApi.sticker.local || '';
        document.getElementById('sticker-n').value = msgApi.sticker.n || 1;
        document.getElementById('sticker-list-path').value = msgApi.sticker.image_list_path || 'data.list';
        document.getElementById('sticker-url-path').value = msgApi.sticker.image_url_path || 'url';
    }
}

function switchMsgMode(mode) {
    document.getElementById('mock-section').style.display = mode === 'mock' ? 'block' : 'none';
    document.getElementById('real-section').style.display = mode === 'real' ? 'block' : 'none';
    document.getElementById('sticker-section').style.display = mode === 'sticker' ? 'block' : 'none';
}

async function saveMessageConfig() {
    const mode = document.querySelector('input[name="msg-mode"]:checked').value;

    const body = { mode };

    if (mode === 'mock') {
        const messages = document.getElementById('mock-messages').value
            .split('\n')
            .map(m => m.trim())
            .filter(m => m);
        body.mock = { messages };
    } else if (mode === 'real') {
        let headers = {};
        try {
            headers = JSON.parse(document.getElementById('api-headers').value || '{}');
        } catch (e) {
            showToast('请求头格式不正确，请输入有效JSON', 'error');
            return;
        }
        body.real = {
            url: document.getElementById('api-url').value,
            method: document.getElementById('api-method').value,
            message_path: document.getElementById('api-message-path').value,
            headers,
        };
    } else if (mode === 'sticker') {
        body.sticker = {
            url: document.getElementById('sticker-url').value,
            local: document.getElementById('sticker-local').value,
            n: parseInt(document.getElementById('sticker-n').value) || 1,
            image_list_path: document.getElementById('sticker-list-path').value,
            image_url_path: document.getElementById('sticker-url-path').value,
        };
    }

    const result = await apiRequest('/api/config/message-api', 'POST', body);
    if (result && result.success) {
        showToast('保存成功');
        loadStats();
    } else {
        showToast(result?.message || '保存失败', 'error');
    }
}

// ========== 邮箱设置 ==========

async function loadEmailConfig() {
    const data = await apiRequest('/api/config');
    if (!data) return;

    const email = data.email || {};
    document.getElementById('email-enabled').checked = email.enabled || false;
    document.getElementById('smtp-server').value = email.smtp_server || '';
    document.getElementById('smtp-port').value = email.smtp_port || 465;
    document.getElementById('smtp-ssl').checked = email.use_ssl !== false;
    document.getElementById('email-sender').value = email.sender || '';
    document.getElementById('email-password').value = email.password || '';
    document.getElementById('email-receivers').value = (email.receivers || []).join(', ');

    const notifyOn = email.notify_on || {};
    document.getElementById('notify-all-failed').checked = notifyOn.all_failed !== false;
    document.getElementById('notify-cookie-expired').checked = notifyOn.cookie_expired !== false;
    document.getElementById('notify-daily-summary').checked = notifyOn.daily_summary || false;
}

async function saveEmailConfig() {
    const receivers = document.getElementById('email-receivers').value
        .split(',')
        .map(r => r.trim())
        .filter(r => r);

    const body = {
        enabled: document.getElementById('email-enabled').checked,
        smtp_server: document.getElementById('smtp-server').value,
        smtp_port: parseInt(document.getElementById('smtp-port').value) || 465,
        use_ssl: document.getElementById('smtp-ssl').checked,
        sender: document.getElementById('email-sender').value,
        password: document.getElementById('email-password').value,
        receivers,
        notify_on: {
            all_failed: document.getElementById('notify-all-failed').checked,
            cookie_expired: document.getElementById('notify-cookie-expired').checked,
            daily_summary: document.getElementById('notify-daily-summary').checked,
        },
    };

    const result = await apiRequest('/api/config/email', 'POST', body);
    if (result && result.success) {
        showToast('保存成功');
        loadStats();
    } else {
        showToast(result?.message || '保存失败', 'error');
    }
}

// ========== 测试功能 ==========

async function testMessage() {
    const result = await apiRequest('/api/test/message');
    if (result && result.success) {
        if (result.mode === 'sticker' && result.image_url) {
            // 表情包模式：显示图片预览
            const preview = window.open('', '_blank', 'width=400,height=400');
            if (preview) {
                preview.document.write(`
                    <html><body style="margin:0;display:flex;align-items:center;justify-content:center;background:#f5f5f5;">
                    <img src="${result.image_url}" style="max-width:100%;max-height:100%;object-fit:contain;">
                    </body></html>
                `);
                preview.document.close();
            }
            showToast('获取表情包成功，已打开预览');
        } else {
            showToast(`获取成功: ${result.message.substring(0, 30)}...`);
        }
    } else {
        showToast(result?.message || '获取失败', 'error');
    }
}

async function testEmail() {
    if (!confirm('确认发送测试邮件？')) return;
    const result = await apiRequest('/api/test/email', 'POST');
    if (result && result.success) {
        showToast(result.message);
    } else {
        showToast(result?.message || '发送失败', 'error');
    }
}

// ========== 发送任务 ==========

let sendStatusTimer = null;

async function startSend() {
    if (!confirm('确认立即给所有好友发送消息？')) return;

    const result = await apiRequest('/api/send/start', 'POST');
    if (result && result.success) {
        showToast('任务已启动');
        document.getElementById('send-status-card').style.display = 'block';
        pollSendStatus();
    } else {
        showToast(result?.message || '启动失败', 'error');
    }
}

function pollSendStatus() {
    if (sendStatusTimer) clearInterval(sendStatusTimer);

    sendStatusTimer = setInterval(async () => {
        const data = await apiRequest('/api/send/status');
        if (!data) return;

        updateSendStatusUI(data);

        if (!data.running) {
            clearInterval(sendStatusTimer);
            showToast('发送任务完成');
            loadStats();
        }
    }, 2000);
}

function updateSendStatusUI(data) {
    const badge = document.getElementById('send-status-badge');
    badge.textContent = data.running ? '运行中' : '已完成';
    badge.className = 'status-badge' + (data.running ? ' running' : '');

    const total = data.total || 0;
    const progress = data.progress || 0;
    const percent = total > 0 ? (progress / total * 100) : 0;

    document.getElementById('progress-fill').style.width = percent + '%';
    document.getElementById('progress-text').textContent = `${progress} / ${total}`;

    const resultsDiv = document.getElementById('send-results');
    if (data.results && data.results.length > 0) {
        resultsDiv.innerHTML = data.results.map(r => {
            if (r.error && !r.remark) {
                return `<div class="send-result-item failed">❌ ${escapeHtml(r.error)}</div>`;
            }
            const cls = r.success ? 'success' : 'failed';
            const icon = r.success ? '✅' : '❌';
            return `<div class="send-result-item ${cls}">${icon} ${escapeHtml(r.remark || r.nickname)}: ${escapeHtml(r.message?.substring(0, 30) || '')}${r.error ? ' - ' + escapeHtml(r.error) : ''}</div>`;
        }).join('');
    }
}

// ========== 日志 ==========

async function loadLogs() {
    const data = await apiRequest('/api/logs?lines=200');
    const viewer = document.getElementById('log-viewer');

    if (!data || data.error) {
        viewer.textContent = data?.error || '加载失败';
        return;
    }

    const logs = data.logs || [];
    if (logs.length === 0) {
        viewer.textContent = '暂无日志';
        return;
    }

    viewer.innerHTML = logs.map(line => {
        let cls = '';
        if (line.includes('ERROR') || line.includes('错误') || line.includes('失败')) cls = 'log-error';
        else if (line.includes('WARN') || line.includes('警告')) cls = 'log-warn';
        else if (line.includes('成功') || line.includes('✅')) cls = 'log-success';
        else if (line.includes('INFO')) cls = 'log-info';
        return `<div class="${cls}">${escapeHtml(line)}</div>`;
    }).join('');

    viewer.scrollTop = viewer.scrollHeight;
}

// ========== 工具函数 ==========

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// ========== 初始化 ==========

document.addEventListener('DOMContentLoaded', function() {
    loadStats();

    // 检查是否有正在运行的发送任务
    apiRequest('/api/send/status').then(data => {
        if (data && data.running) {
            document.getElementById('send-status-card').style.display = 'block';
            updateSendStatusUI(data);
            pollSendStatus();
        }
    });
});

// 点击弹窗外部关闭
document.getElementById('friend-modal').addEventListener('click', function(e) {
    if (e.target === this) closeFriendModal();
});
