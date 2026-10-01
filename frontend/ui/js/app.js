// # PENDING-UI patch applied
const API_BASE = '';  // Stays empty to dynamically evaluate your Render URL paths
let authToken = localStorage.getItem('coMpaNeoN_token') || '';
let currentUser = null;
let currentWorkspaceId = null;
let workspaceList = [];

let signupMode = 'solo';

// ========== Auth Layout View Switcher ==========
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

// ========== Global Dynamic HTTP Core Requester ==========
async function api(path, method='GET', body=null, isForm=false) {
    const headers = {};
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    if (!isForm) {
        headers['Content-Type'] = 'application/json';
    }
    
    const options = { method, headers };
    if (body) {
        options.body = isForm ? body : JSON.stringify(body);
    }
    
    const res = await fetch(API_BASE + path, options);
    if (!res.ok) {
        // API-FIX: read the body once, then try to parse as JSON.
        const rawText = await res.text();
        let errorMsg = 'An unexpected server error occurred.';
        if (rawText) {
            try {
                const errData = JSON.parse(rawText);
                errorMsg = errData.detail || errData.message || errData.error || errorMsg;
            } catch (_) {
                errorMsg = rawText;
            }
        }
        throw new Error(`${res.status} ${errorMsg}`);
    }
    // 204 No Content or empty body
    const text = await res.text();
    return text ? JSON.parse(text) : {};
}

// ========== User Registration Logic ==========
async function login() {
    const phone = document.getElementById('loginPhone').value.trim();
    const password = document.getElementById('loginPassword').value;
    if (!phone || !password) {
        alert('Please provide your login credentials.');
        return;
    }
    try {
        const data = await api('/auth/login', 'POST', { phone, password });
        // PENDING-UI: workers awaiting admin approval get no token
        if (data && data.pending) {
            alert(data.message || 'Your signup is awaiting admin approval.');
            return;
        }
        if (typeof handleAuthSuccess === 'function') {
            handleAuthSuccess(data);
            return;
        }
        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('coMpaNeoN_token', authToken);
        localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
        showScreen('mainScreen');
        await loadWorkspaces();
    } catch (e) { 
        alert(`Login Fault: ${e.message}`); 
    }
}

// ========== Auth Views ==========
function showAuthView(viewName) {
    document.querySelectorAll('.auth-view').forEach(v => v.classList.remove('active'));
    const t = document.getElementById(viewName);
    if (t) t.classList.add('active');
}

function authViewFromKey(key) {
    const map = {
        landing: 'authLanding',
        login: 'authLogin',
        signupChoice: 'authSignupChoice',
        signupSolo: 'authSignupSolo',
        signupOrgCreate: 'authSignupOrgCreate',
        signupOrgJoin: 'authSignupOrgJoin',
    };
    return map[key] || 'authLanding';
}

function bindAuthNav() {
    document.querySelectorAll('[data-view]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const key = btn.dataset.view;
            if (key) showAuthView(authViewFromKey(key));
        });
    });
}

function handleAuthSuccess(data) {
    if (!data || !data.access_token) {
        showAuthView('authLanding');
        return;
    }
    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem('coMpaNeoN_token', authToken);
    localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
    showScreen('mainScreen');
    loadWorkspaces();
}

// Signup — Regular User
async function signupSolo() {
    const full_name = document.getElementById('soloFullName').value.trim();
    const phone = document.getElementById('soloPhone').value.trim();
    const password = document.getElementById('soloPassword').value;
    const country = document.getElementById('signupCountry').value;
    const temperament = document.getElementById('signupTemperament').value;
    if (!full_name || !phone || !password) {
        alert('Name, phone, and password are required.');
        return;
    }
    try {
        const data = await api('/auth/signup', 'POST',
            { full_name, phone, password, country, temperament, language: 'en' });
        handleAuthSuccess(data);
    } catch (e) {
        alert(`Registration failed: ${e.message}`);
    }
}

// Signup — Create Organization
async function signupOrgCreate() {
    const full_name = document.getElementById('orgFullName').value.trim();
    const phone = document.getElementById('orgAdminPhone').value.trim();
    const password = document.getElementById('orgPassword').value;
    const org_name = document.getElementById('orgName').value.trim();
    const org_slug = document.getElementById('orgSlug').value.trim();
    const org_email = document.getElementById('orgEmail').value.trim();
    const org_country = document.getElementById('orgCountry').value.trim() || 'Nigeria';
    if (!full_name || !phone || !password || !org_name || !org_slug) {
        alert('All fields except org email are required.');
        return;
    }
    try {
        const data = await api('/auth/org/create', 'POST', {
            full_name, phone, password,
            org_name, org_slug,
            org_email: org_email || null,
            org_country,
            language: 'en',
        });
        if (data && data.worker_credential) {
            alert('Organization created.\n\nWorker credential (share with your team):\n\n'
                + data.worker_credential
                + '\n\nSave this \u2014 you will need it to onboard workers.');
        }
        handleAuthSuccess(data);
    } catch (e) {
        alert(`Org creation failed: ${e.message}`);
    }
}

// Signup — Join Organization as worker
async function signupOrgJoin() {
    const full_name = document.getElementById('joinFullName').value.trim();
    const phone = document.getElementById('joinPhone').value.trim();
    const password = document.getElementById('joinPassword').value;
    const worker_credential = document.getElementById('workerCred').value.trim();
    const department = document.getElementById('joinDept').value.trim();
    const role = document.getElementById('joinRole').value.trim() || 'member';
    const title = document.getElementById('joinTitle').value.trim();
    if (!full_name || !phone || !password || !worker_credential || !department) {
        alert('Name, phone, password, worker credential, and department are required.');
        return;
    }
    try {
        const data = await api('/auth/org/join', 'POST', {
            full_name, phone, password,
            worker_credential, department, role,
            title: title || null,
            language: 'en',
        });
        if (data && data.pending) {
            alert('Signup submitted. An org admin must approve you before you can enter.');
            showAuthView('authLanding');
            return;
        }
        handleAuthSuccess(data);
    } catch (e) {
        alert(`Join failed: ${e.message}`);
    }
}

function bindAuthButtons() {
    const pairs = [
        ['btnLogin', login],
        ['btnSignupSolo', signupSolo],
        ['btnSignupOrgCreate', signupOrgCreate],
        ['btnSignupOrgJoin', signupOrgJoin],
    ];
    pairs.forEach(([id, fn]) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', fn);
    });
}

function logout() {
    authToken = '';
    currentUser = null;
    currentWorkspaceId = null;
    workspaceList = [];
    localStorage.removeItem('coMpaNeoN_token');
    localStorage.removeItem('coMpaNeoN_user');
    document.getElementById('chatBox').innerHTML = '';
    showScreen('authScreen');
}

// ========== Dynamic Workspace Ribbon Controllers ==========
async function loadWorkspaces() {
    try {
        const workspaces = await api('/workspaces');
        workspaceList = workspaces;
        renderWorkspaceTabs();
        
        // Auto-select the first workspace if none is active and items exist
        if (workspaceList.length > 0 && !currentWorkspaceId) {
            currentWorkspaceId = workspaceList[0].id;
            renderWorkspaceTabs();
            await loadWorkspaceMessages(currentWorkspaceId);
        }
    } catch (e) { 
        console.error(`Failed to refresh threads: ${e.message}`); 
    }
}

function renderWorkspaceTabs() {
    const container = document.getElementById('workspaceTabs');
    if (!container) return;
    
    container.innerHTML = workspaceList.map(ws => `
        <div class="workspace-tab ${ws.id === currentWorkspaceId ? 'active' : ''}" data-id="${ws.id}">
            ${ws.project_name}
        </div>
    `).join('');
    
    container.querySelectorAll('.workspace-tab').forEach(tab => {
        tab.addEventListener('click', async () => {
            currentWorkspaceId = tab.dataset.id;
            renderWorkspaceTabs();
            await loadWorkspaceMessages(currentWorkspaceId);
        });
    });
}

async function createWorkspace(firstMessage) {
    try {
        const data = await api('/workspace', 'POST', { first_message: firstMessage });
        currentWorkspaceId = data.workspace_id;
        
        // Clear chat area for the newly initiated thread context
        document.getElementById('chatBox').innerHTML = '';
        appendMessage('user', firstMessage);
        
        await loadWorkspaces();
        // Dispatches directly to the specialized workspace generator context
        await sendMessage(firstMessage, true);
    } catch (e) { 
        alert(`Could not create workspace: ${e.message}`); 
    }
}

async function loadWorkspaceMessages(wsId) {
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = '';
    
    // Fallback indicator while thread aggregates initial assets
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message ai';
    loadingDiv.style.opacity = '0.5';
    loadingDiv.textContent = 'Synchronizing workspace history context...';
    chatBox.appendChild(loadingDiv);

    try {
        // Points natively to your historical message retriever setup
        const messages = await api(`/api/messages/with/${currentUser?.phone || ''}`);
        chatBox.innerHTML = '';
        
        if (messages && messages.length > 0) {
            messages.forEach(msg => {
                appendMessage(msg.sender === currentUser?.phone ? 'user' : 'ai', msg.content);
            });
        } else {
            appendMessage('ai', 'Workspace synchronized. How shall we expand our dataset logic today?');
        }
    } catch (e) {
        chatBox.innerHTML = '';
        appendMessage('ai', 'Workspace activated. Start typing to seed runtime context logs.');
    }
}

// ========== Modern Chat Stream Engine & Bubble Layout Generator ==========
function renderCodeTokens(tokens, lang) {
    const parts = tokens.map(t => {
        const cls = t.kind === 'c' && t.color ? ` code-${t.color.toLowerCase()}` : '';
        const esc = (t.text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        return cls ? `<span class="${cls.trim()}">${esc}</span>` : esc;
    });
    return `<pre class="code-block" data-lang="${lang || ''}"><code>${parts.join('')}</code></pre>`;
}

function renderStatusFrame(container, jsonPayload) {
    let payload;
    try { payload = JSON.parse(jsonPayload); }
    catch (_) { return; }
    const kind = payload.kind || 'status';
    const msg = payload.msg || '';

    // find or create the "thinking" tray at the top of this message body
    let tray = container.querySelector('.status-tray');
    if (!tray) {
        tray = document.createElement('div');
        tray.className = 'status-tray';
        container.appendChild(tray);
    }

    // collapse trailing "thinking/generating" pills when a new status arrives
    if (kind === 'done' || kind === 'error' || kind === 'verify_result' || kind === 'tool_result') {
        tray.querySelectorAll('.status-pill.pending').forEach(el => el.classList.remove('pending'));
    }

    const pill = document.createElement('div');
    pill.className = 'status-pill';

    if (kind === 'thinking' || kind === 'planning' || kind === 'generating' || kind === 'waiting') {
        pill.classList.add('pending');
    }
    if (kind === 'error') pill.classList.add('err');
    if (kind === 'verify_result' || kind === 'tool_result') {
        pill.classList.add(payload.ok ? 'ok' : 'err');
    }
    if (kind === 'done') pill.classList.add('ok');

    const icon = {
        thinking:    '🧠', planning: '📋', generating: '✍️', waiting: '⏳',
        tool_call:   '🔧', tool_result: '✅', verifying: '🔍',
        verify_result: '🛡️', retry: '🔁', error: '⚠️', done: '🎉',
    }[kind] || '•';

    pill.innerHTML = `<span class="status-icon">${icon}</span><span class="status-text">${kind}${msg ? ' · ' + msg : ''}</span>`;
    tray.appendChild(pill);
}

function renderFrames(container, frames) {
    if (!Array.isArray(frames) || frames.length === 0) return false;

    let prose = '';
    let codeTokens = [];
    let codeLang = '';
    let inCode = false;
    let pendingKind = null;
    let pendingColor = null;

    const flushProse = () => {
        if (!prose) return;
        const p = document.createElement('div');
        p.className = 'frame-prose';
        p.textContent = prose;
        container.appendChild(p);
        prose = '';
    };

    for (const frame of frames) {
        if (frame.startsWith('#begin#') || frame.startsWith('#end#') || frame.startsWith('#meta#')) {
            continue;
        }
        if (frame.startsWith('#status#')) {
            flushProse();
            try { renderStatusFrame(container, frame.slice(8)); }
            catch (_) {}
            continue;
        }

        if (frame.startsWith('#prose#')) {
            flushProse();
            prose += frame.slice(7);
            continue;
        }
        if (frame.startsWith('#code-begin#')) {
            flushProse();
            const parts = frame.slice(12).split('#');
            codeLang = parts[0] || '';
            inCode = true;
            codeTokens = [];
            continue;
        }
        if (frame.startsWith('#code-end#')) {
            const div = document.createElement('div');
            div.innerHTML = renderCodeTokens(codeTokens, codeLang);
            container.appendChild(div);
            inCode = false;
            codeTokens = [];
            codeLang = '';
            continue;
        }
        if (frame.startsWith('#code-error#')) {
            flushProse();
            const div = document.createElement('div');
            div.className = 'frame-error';
            div.textContent = '⚠️ Code block rejected by verification: ' + frame.slice(12);
            container.appendChild(div);
            inCode = false;
            continue;
        }
        if (frame.startsWith('#error#')) {
            flushProse();
            const div = document.createElement('div');
            div.className = 'frame-error';
            div.textContent = '⚠️ ' + frame.slice(7);
            container.appendChild(div);
            continue;
        }
        if (frame.startsWith('#kind#')) { pendingKind = frame.slice(6); continue; }
        if (frame.startsWith('#color#')) { pendingColor = frame.slice(7); continue; }
        if (frame.startsWith('#token#')) {
            const text = frame.slice(7);
            if (inCode) {
                codeTokens.push({ kind: pendingKind || 'w', color: pendingColor, text });
            } else {
                prose += text;
            }
            pendingKind = null;
            pendingColor = null;
        }
    }

    flushProse();
    return true;
}

function appendFrameMessage(role, frames, followUps = []) {
    const chatBox = document.getElementById('chatBox');
    if (!chatBox) return;
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const body = document.createElement('div');
    div.appendChild(body);
    renderFrames(body, frames);

    if (followUps && followUps.length > 0) {
        followUps.forEach(followUpText => {
            const card = document.createElement('div');
            card.className = 'reply-card';
            card.innerHTML = `<span class="reply-tag">💡 Suggested Extension</span><p>${followUpText}</p>`;
            card.addEventListener('click', (e) => {
                e.stopPropagation();
                document.getElementById('promptInput').value = followUpText;
                document.getElementById('btnSend').click();
            });
            div.appendChild(card);
        });
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendMessage(role, text, followUps = []) {
    const chatBox = document.getElementById('chatBox');
    if (!chatBox) return;
    
    const div = document.createElement('div');
    div.className = `message ${role}`;
    
    // Render sanitized plain-text message strings cleanly
    div.textContent = text;
    
    // Inject dynamic, interactive follow-up reply cards if supplied by backend endpoints
    if (followUps && followUps.length > 0) {
        followUps.forEach(followUpText => {
            const card = document.createElement('div');
            card.className = 'reply-card';
            card.innerHTML = `<span class="reply-tag">💡 Suggested Extension</span><p>${followUpText}</p>`;
            card.addEventListener('click', (e) => {
                e.stopPropagation();
                document.getElementById('promptInput').value = followUpText;
                document.getElementById('btnSend').click();
            });
            div.appendChild(card);
        });
    }
    
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}


// ========== Research Engine Aggregators ==========
async function openResearch() {
    const panel = document.getElementById('researchPanel');
    if (!panel) return;
    
    panel.style.display = 'block';
    const query = document.getElementById('promptInput').value.trim();
    const container = document.getElementById('researchResults');
    
    if (query) {
        container.innerHTML = '<p style="opacity:0.6;">Querying external index structures (Wikipedia, News, Dictionary)...</p>';
        try {
            const data = await api('/research', 'POST', { query });
            displayResearch(data);
        } catch (e) { 
            container.innerHTML = `<p style="color:#ef4444;">Research Fault: ${e.message}</p>`; 
        }
    } else {
        container.innerHTML = '<p style="opacity:0.5;">Input terms into the prompt bar to crawl cross-domain engines.</p>';
    }
}

function displayResearch(data) {
    const container = document.getElementById('researchResults');
    if (!container) return;
    container.innerHTML = '';

    let fragmentsFound = false;

    if (data.wikipedia && data.wikipedia.extract) {
        fragmentsFound = true;
        container.innerHTML += `
            <div style="margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                <h4 style="color:var(--neon-blue);">📚 Wikipedia Extract</h4>
                <p style="opacity:0.85;">${data.wikipedia.extract}</p>
                ${data.wikipedia.url ? `<a href="${data.wikipedia.url}" target="_blank" style="opacity:0.7; font-size:0.8rem;">source</a>` : ''}
            </div>`;
    }

    if (data.news && Array.isArray(data.news) && data.news.length > 0) {
        fragmentsFound = true;
        container.innerHTML += `<div style="margin-bottom: 1rem;"><h4 style="color:var(--neon-blue);">📰 News</h4>`;
        data.news.slice(0, 8).forEach(item => {
            const title = item.title || item.headline || 'Untitled';
            const url = item.url || item.link || '#';
            container.innerHTML += `
                <div style="margin-bottom:0.5rem;">
                    <a href="${url}" target="_blank" style="opacity:0.9;">${title}</a>
                </div>`;
        });
        container.innerHTML += `</div>`;
    }

    if (data.dictionary && data.dictionary.length > 0) {
        fragmentsFound = true;
        container.innerHTML += `<div style="margin-bottom: 1rem;"><h4 style="color:var(--neon-blue);">📖 Dictionary</h4>`;
        data.dictionary.slice(0, 5).forEach(entry => {
            container.innerHTML += `<p style="opacity:0.85; margin-bottom:0.4rem;">${entry}</p>`;
        });
        container.innerHTML += `</div>`;
    }

    if (data.books && data.books.length > 0) {
        fragmentsFound = true;
        container.innerHTML += `<div><h4 style="color:var(--neon-blue);">📚 Books</h4>`;
        data.books.slice(0, 5).forEach(b => {
            container.innerHTML += `<p style="opacity:0.85; margin-bottom:0.4rem;">${b.title || b}</p>`;
        });
        container.innerHTML += `</div>`;
    }

    if (!fragmentsFound) {
        container.innerHTML = '<p style="opacity:0.6;">No external fragments matched this query.</p>';
    }
}

document.getElementById('btnLogout').addEventListener('click', logout);

document.getElementById('btnSettings').addEventListener('click', () => {
    document.getElementById('settingsModal').style.display = 'flex';
    if (currentUser) {
        if (document.getElementById('settingsLanguage')) {
            document.getElementById('settingsLanguage').value = currentUser.language || 'en';
        }
        if (document.getElementById('settingsTemperament')) {
            document.getElementById('settingsTemperament').value = currentUser.temperament || 'sanguine';
        }
    }
});

document.getElementById('btnCloseSettings').addEventListener('click', () => {
    document.getElementById('settingsModal').style.display = 'none';
});

document.getElementById('btnSaveSettings').addEventListener('click', async () => {
    const language = document.getElementById('settingsLanguage').value;
    const temperament = document.getElementById('settingsTemperament').value;
    if (currentUser) {
        currentUser.language = language;
        currentUser.temperament = temperament;
        localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
    }
    document.getElementById('settingsModal').style.display = 'none';
    alert('Local system preferences applied.');
});

document.getElementById('btnCloseResearch').addEventListener('click', () => {
    document.getElementById('researchPanel').style.display = 'none';
});

// Setup bottom application navigation switches
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        const action = link.dataset.action;
        if (action === 'research') {
            openResearch();
        } else if (action === 'workspace') {
            loadWorkspaces();
        } else if (action === 'train') {
        openTrainingModal();
    }
    });
});

// ========== Training Modal ==========
async function openTrainingModal() {
    const modal = document.getElementById('trainingModal');
    const status = document.getElementById('trainingStatusText');
    if (!modal) return;
    modal.style.display = 'flex';
    status.textContent = 'Checking runtime readiness…';
    document.getElementById('trainingResult').innerHTML = '';
    try {
        const s = await api('/train/status');
        if (s.torch_available) {
            status.innerHTML = '✅ Runtime ready. Torch is installed.';
            document.getElementById('btnStartTraining').disabled = false;
        } else {
            status.innerHTML = '⚠️ Torch is not installed on this runtime. Training will fail until it is.';
            document.getElementById('btnStartTraining').disabled = true;
        }
    } catch (e) {
        status.textContent = `Status check failed: ${e.message}`;
        document.getElementById('btnStartTraining').disabled = true;
    }
}

async function startTraining() {
    const epochs = parseInt(document.getElementById('trainEpochs').value, 10) || 1;
    const batch_size = parseInt(document.getElementById('trainBatch').value, 10) || 8;
    const max_texts = parseInt(document.getElementById('trainMaxTexts').value, 10) || 500;
    const result = document.getElementById('trainingResult');
    const btn = document.getElementById('btnStartTraining');
    btn.disabled = true;
    result.innerHTML = 'Queuing run…';
    try {
        const data = await api('/train', 'POST', {
            epochs, batch_size, max_texts, label: 'manual-ui',
        });
        result.innerHTML = `<pre style="white-space:pre-wrap;">${JSON.stringify(data, null, 2)}</pre>`;
    } catch (e) {
        result.innerHTML = `<span style="color:#ef4444;">Training error: ${e.message}</span>`;
    } finally {
        btn.disabled = false;
    }
}

document.getElementById('btnCloseTraining')?.addEventListener('click', () => {
    document.getElementById('trainingModal').style.display = 'none';
});
document.getElementById('btnStartTraining')?.addEventListener('click', startTraining);

// ========== Initialization Engine Spark ==========
if (authToken) {
    try {
        currentUser = JSON.parse(localStorage.getItem('coMpaNeoN_user') || '{}');
        showScreen('mainScreen');
        loadWorkspaces();
    } catch (_) {
        logout();
    }
} else {
    showScreen('authScreen');
    try { showAuthView('authLanding'); } catch (_) {}
}

// Bind auth navigation + submit buttons
try {
    bindAuthNav();
    bindAuthButtons();
    showAuthView('authLanding');
} catch (_) {}


// ========== Particle Bubble Canvas ==========
function initBubbleCanvas() {
    const canvas = document.getElementById('bubbleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W = 0, H = 0;
    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const COUNT = Math.max(18, Math.min(45, Math.floor(W * H / 42000)));
    const bubbles = Array.from({ length: COUNT }, () => ({
        x: Math.random() * W,
        y: Math.random() * H,
        r: 6 + Math.random() * 34,
        dx: (Math.random() - 0.5) * 0.45,
        dy: -0.15 - Math.random() * 0.55,
        a: 0.035 + Math.random() * 0.09,
        hue: [220, 340, 172][Math.floor(Math.random() * 3)],  // neon blue, burgundy, aqua
    }));

    function frame() {
        ctx.clearRect(0, 0, W, H);
        for (const b of bubbles) {
            ctx.beginPath();
            ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${b.hue}, 80%, 60%, ${b.a})`;
            ctx.fill();
            ctx.strokeStyle = `hsla(${b.hue}, 80%, 75%, ${b.a * 0.7})`;
            ctx.lineWidth = 1;
            ctx.stroke();

            b.x += b.dx;
            b.y += b.dy;
            if (b.y + b.r < -10) {
                b.y = H + b.r;
                b.x = Math.random() * W;
            }
            if (b.x < -b.r) b.x = W + b.r;
            if (b.x > W + b.r) b.x = -b.r;
        }
        requestAnimationFrame(frame);
    }
    frame();
}

// boot the canvas once
try { initBubbleCanvas(); } catch (_) {}


// ============================================================================
// ROOMS (workspace CRUD + room chat)
// ============================================================================

let roomList = [];
let currentRoomId = null;
let currentUserRole = 'owner';
let isAdmin = false;
let hasOrg = false;
let dmPartner = null;

async function loadMe() {
    try {
        const me = await api('/auth/me');
        currentUserRole = me.primary_role || 'owner';
        isAdmin = !!me.is_admin;
        hasOrg = !!me.has_org;
        currentUser = Object.assign({}, currentUser || {}, me.user, {
            role: currentUserRole,
        });
        localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
    } catch (e) {
        console.warn('loadMe failed:', e.message);
    }
}

async function loadRooms() {
    try {
        roomList = await api('/rooms');
    } catch (e) {
        console.warn('loadRooms failed:', e.message);
        roomList = [];
    }
    renderRoomBar();
    if (!currentRoomId && roomList.length > 0) {
        await openRoom(roomList[0].id);
    }
}

function renderRoomBar() {
    // # SIDEBAR-V2
    const bar = document.getElementById('roomList');
    if (!bar) return;

    const groups = [
        { key: 'personal_brainstorm', label: 'Personal',     icon: 'fa-brain',         required: true  },
        { key: 'group',               label: 'Groups',        icon: 'fa-users',         required: true  },
        { key: 'meeting',             label: 'Meetings',      icon: 'fa-handshake',     required: false },
        { key: 'team',                label: 'Teams',         icon: 'fa-people-group',  required: false },
        { key: 'department',          label: 'Departments',   icon: 'fa-building',      required: false },
        { key: 'organization',        label: 'Organization',  icon: 'fa-sitemap',       required: false },
    ];

    // bucket rooms by type
    const buckets = {};
    groups.forEach(g => buckets[g.key] = []);
    roomList.forEach(r => {
        if (!buckets[r.workspace_type]) buckets[r.workspace_type] = [];
        buckets[r.workspace_type].push(r);
    });

    // collapse state from localStorage
    let collapse = {};
    try { collapse = JSON.parse(localStorage.getItem('acd_room_collapse') || '{}'); } catch (_) {}

    bar.innerHTML = groups.map(g => {
        const items = buckets[g.key] || [];
        if (!g.required && items.length === 0 && !hasOrg) return '';
        const collapsed = collapse[g.key] === true;
        const arrow = collapsed ? '\u25B8' : '\u25BE';
        const itemsHtml = items.length
            ? items.map(r => `
                <button class="side-item${r.id === currentRoomId ? ' active' : ''}" data-room="${r.id}">
                    <span class="side-item-name">${escapeHtml(r.project_name || 'Untitled')}</span>
                    ${r.member_count > 1 ? `<span class="side-item-badge">${r.member_count}</span>` : ''}
                </button>
            `).join('')
            : `<div class="side-empty">No ${g.label.toLowerCase()} yet</div>`;
        return `
            <div class="side-section">
                <div class="side-header" data-toggle="${g.key}">
                    <span class="side-arrow">${arrow}</span>
                    <i class="fa-solid ${g.icon}"></i>
                    <span class="side-label">${g.label}</span>
                    <span class="side-count">${items.length}</span>
                    <span class="side-add" data-new="${g.key}" title="New ${g.label}">
                        <i class="fa-solid fa-plus"></i>
                    </span>
                </div>
                <div class="side-items${collapsed ? ' hidden' : ''}">
                    ${itemsHtml}
                </div>
            </div>`;
    }).join('');

    // wire section toggles
    bar.querySelectorAll('[data-toggle]').forEach(el => {
        el.addEventListener('click', (e) => {
            if (e.target.closest('[data-new]')) return;
            const key = el.dataset.toggle;
            collapse[key] = !collapse[key];
            localStorage.setItem('acd_room_collapse', JSON.stringify(collapse));
            renderRoomBar();
        });
    });

    // wire + buttons
    bar.querySelectorAll('[data-new]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            openNewRoomModalFor(el.dataset.new);
        });
    });

    // wire item clicks
    bar.querySelectorAll('.side-item').forEach(el => {
        el.addEventListener('click', () => {
            openRoom(el.dataset.room);
            closeSidebar();
        });
    });
}

function openSidebar() {
    const s = document.getElementById('sidebar');
    const b = document.getElementById('sidebarBackdrop');
    if (s) s.classList.add('open');
    if (b) b.classList.add('open');
}

function closeSidebar() {
    const s = document.getElementById('sidebar');
    const b = document.getElementById('sidebarBackdrop');
    if (s) s.classList.remove('open');
    if (b) b.classList.remove('open');
}

function openNewRoomModalFor(type) {
    const sel = document.getElementById('newRoomType');
    if (sel) {
        // map sidebar key to modal option value (they are the same strings)
        sel.value = type;
    }
    openNewRoomModal();
}

function updateActiveTitle() {
    const t = document.getElementById('activeRoomTitle');
    if (!t) return;
    if (!currentRoomId) { t.textContent = 'CoMpaNeoN AI'; return; }
    const room = roomList.find(r => r.id === currentRoomId);
    t.textContent = room ? room.project_name : 'CoMpaNeoN AI';
}

function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

async function openRoom(id) {
    currentRoomId = id;
    renderRoomBar();
    updateActiveTitle();
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = '';
    try {
        const msgs = await api(`/rooms/${id}/messages`);
        if (!msgs.length) {
            appendMessage('ai', 'Workspace ready. Say something to begin.');
        } else {
            msgs.forEach(m => {
                const mine = m.user_id && currentUser && m.user_id === currentUser.id;
                appendMessage(m.role === 'ai' || m.role === 'assistant' ? 'ai' : (mine ? 'user' : 'ai'), m.content);
            });
        }
    } catch (e) {
        appendMessage('ai', `Could not load room: ${e.message}`);
    }
}

async function createRoom() {
    const type = document.getElementById('newRoomType').value;
    const name = document.getElementById('newRoomName').value.trim();
    if (!name) { alert('Give the workspace a name.'); return; }
    try {
        const room = await api('/rooms', 'POST', {
            workspace_type: type,
            project_name: name,
        });
        document.getElementById('newRoomModal').style.display = 'none';
        document.getElementById('newRoomName').value = '';
        await loadRooms();
        await openRoom(room.id);
    } catch (e) {
        alert(`Could not create workspace: ${e.message}`);
    }
}

function openNewRoomModal() {
    const modal = document.getElementById('newRoomModal');
    if (!modal) return;
    // hide org-only options when user has no org
    modal.querySelectorAll('option[data-org-only]').forEach(opt => {
        opt.style.display = hasOrg ? '' : 'none';
    });
    modal.style.display = 'flex';
}

// ============================================================================
// DIRECT MESSAGES (peer-to-peer)
// ============================================================================

async function openDMPanel() {
    const panel = document.getElementById('dmPanel');
    if (!panel) return;
    panel.style.display = 'block';
    document.getElementById('dmThread').style.display = 'none';
    document.getElementById('dmList').style.display = 'block';
    await loadDMConversations();
}

async function loadDMConversations() {
    const list = document.getElementById('dmList');
    list.innerHTML = '<p style="opacity:.6;">Loading…</p>';
    try {
        const convos = await api('/api/messages/conversations');
        if (!convos.length) {
            list.innerHTML = '<p style="opacity:.6;">No conversations yet. Send a message by phone number.</p>';
            return;
        }
        list.innerHTML = convos.map(c => `
            <button class="dm-item" data-phone="${escapeHtml(c.phone)}">
                <div class="dm-phone">${escapeHtml(c.phone)}</div>
                <div class="dm-last">${escapeHtml((c.last_message || '').slice(0, 60))}</div>
                ${c.unread ? `<span class="dm-unread">${c.unread}</span>` : ''}
            </button>
        `).join('');
        list.querySelectorAll('.dm-item').forEach(el => {
            el.addEventListener('click', () => openDMThread(el.dataset.phone));
        });
    } catch (e) {
        list.innerHTML = `<p style="color:#f3a9c1;">Could not load conversations: ${escapeHtml(e.message)}</p>`;
    }
}

async function openDMThread(phone) {
    dmPartner = phone;
    document.getElementById('dmList').style.display = 'none';
    document.getElementById('dmThread').style.display = 'block';
    const box = document.getElementById('dmMessages');
    box.innerHTML = '<p style="opacity:.6;">Loading…</p>';
    try {
        const msgs = await api(`/api/messages/with/${encodeURIComponent(phone)}`);
        box.innerHTML = '';
        if (!msgs.length) {
            box.innerHTML = '<p style="opacity:.5;padding:.75rem;">No messages yet.</p>';
        } else {
            msgs.forEach(m => {
                const mine = m.sender_phone === (currentUser && currentUser.phone);
                const d = document.createElement('div');
                d.className = `dm-bubble ${mine ? 'dm-mine' : 'dm-theirs'}`;
                d.textContent = m.content;
                box.appendChild(d);
            });
        }
        box.scrollTop = box.scrollHeight;
    } catch (e) {
        box.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

async function sendDM() {
    const input = document.getElementById('dmInput');
    const content = input.value.trim();
    if (!content || !dmPartner) return;
    input.value = '';
    try {
        await api('/api/messages/send', 'POST', {
            recipient_phone: dmPartner,
            content,
        });
        await openDMThread(dmPartner);
    } catch (e) {
        alert(`Could not send: ${e.message}`);
    }
}

// ============================================================================
// ADMIN (pending workers)
// ============================================================================

async function loadAdminPending() {
    if (!isAdmin) return;
    const section = document.getElementById('adminSection');
    const list = document.getElementById('adminPendingList');
    if (!section || !list) return;
    section.style.display = 'block';
    list.innerHTML = '<p style="opacity:.6;">Loading…</p>';
    try {
        const pending = await api('/admin/pending');
        if (!pending.length) {
            list.innerHTML = '<p style="opacity:.5;">No pending signups.</p>';
            return;
        }
        list.innerHTML = pending.map(p => `
            <div class="admin-row">
                <div>
                    <strong>${escapeHtml(p.full_name || '')}</strong>
                    <div style="opacity:.6;font-size:.78rem;">${escapeHtml(p.phone || '')} · ${escapeHtml(p.department || '')}</div>
                </div>
                <div class="admin-actions">
                    <button class="mini-btn ok" data-approve="${p.membership_id}">
                        <i class="fa-solid fa-check"></i>
                    </button>
                    <button class="mini-btn err" data-reject="${p.membership_id}">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>
        `).join('');
        list.querySelectorAll('[data-approve]').forEach(el => {
            el.addEventListener('click', () => adminApprove(el.dataset.approve));
        });
        list.querySelectorAll('[data-reject]').forEach(el => {
            el.addEventListener('click', () => adminReject(el.dataset.reject));
        });
    } catch (e) {
        list.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

async function adminApprove(id) {
    try {
        await api(`/admin/approve/${id}`, 'POST');
        await loadAdminPending();
    } catch (e) { alert(`Approve failed: ${e.message}`); }
}

async function adminReject(id) {
    if (!confirm('Reject this signup?')) return;
    try {
        await api(`/admin/reject/${id}`, 'POST');
        await loadAdminPending();
    } catch (e) { alert(`Reject failed: ${e.message}`); }
}

// ============================================================================
// BOOT WIRING (added to existing init via listeners below)
// ============================================================================

function wireRoomUI() {
    const btnNew = document.getElementById('btnNewRoom');
    if (btnNew) btnNew.addEventListener('click', openNewRoomModal);
    const btnCreate = document.getElementById('btnCreateRoom');
    if (btnCreate) btnCreate.addEventListener('click', createRoom);
    const btnCloseNew = document.getElementById('btnCloseNewRoom');
    if (btnCloseNew) btnCloseNew.addEventListener('click', () => {
        document.getElementById('newRoomModal').style.display = 'none';
    });
    const btnCloseDM = document.getElementById('btnCloseDM');
    if (btnCloseDM) btnCloseDM.addEventListener('click', () => {
        document.getElementById('dmPanel').style.display = 'none';
    });
    const btnDmBack = document.getElementById('btnDmBack');
    if (btnDmBack) btnDmBack.addEventListener('click', () => {
        document.getElementById('dmThread').style.display = 'none';
        document.getElementById('dmList').style.display = 'block';
        loadDMConversations();
    });
    const btnSendDM = document.getElementById('btnSendDM');
    if (btnSendDM) btnSendDM.addEventListener('click', sendDM);
    const dmInput = document.getElementById('dmInput');
    if (dmInput) dmInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') sendDM();
    });
    // hook the bottom nav "messages" icon
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.dataset.action === 'messages') {
            link.addEventListener('click', openDMPanel);
        }
    });
    // hook settings open → admin section
    const btnSettings = document.getElementById('btnSettings');
    if (btnSettings) {
        btnSettings.addEventListener('click', () => {
            if (isAdmin) loadAdminPending();
        });
    }
}

try { wireRoomUI(); } catch (_) {}

// Override sendMessage so room input posts to the room chat endpoint.
async function sendMessage(text, isFirst=false) {
    if (!text.trim()) return;
    if (!isFirst) appendMessage('user', text);
    try {
        let data;
        if (currentRoomId) {
            data = await api(`/rooms/${currentRoomId}/messages`, 'POST', { content: text });
        } else {
            // no active room — fall back to a personal brainstorm
            const room = await api('/rooms', 'POST', {
                workspace_type: 'personal_brainstorm',
                project_name: text.slice(0, 60) || 'Quick chat',
            });
            currentRoomId = room.id;
            await loadRooms();
            data = await api(`/rooms/${currentRoomId}/messages`, 'POST', { content: text });
        }
        if (data && data.frames && data.frames.length > 0) {
            appendFrameMessage('ai', data.frames, []);
        } else if (data && data.content) {
            appendMessage('ai', data.content);
        }
    } catch (e) {
        appendMessage('ai', `System Matrix Sync Failure: ${e.message}`);
    }
}

// Make sure login/signup boot the room pipeline.
const _origHandleAuthSuccess = handleAuthSuccess;
handleAuthSuccess = async function(data) {
    _origHandleAuthSuccess(data);
    try {
        await loadMe();
        await loadRooms();
    } catch (_) {}
};


// ============================================================================
// WORKER CREDENTIAL (admin)
// ============================================================================

async function loadOrgCredential() {
    const box = document.getElementById('adminCredential');
    if (!box) return;
    box.style.display = 'block';
    const code = document.getElementById('credValue');
    code.textContent = 'Loading…';
    try {
        const data = await api('/admin/credential');
        code.textContent = data.worker_credential || '—';
        const when = document.getElementById('credRotatedAt');
        if (when && data.rotated_at) {
            when.textContent = `last rotated ${new Date(data.rotated_at).toLocaleString()}`;
        }
    } catch (e) {
        code.textContent = `error: ${e.message}`;
    }
}

async function rotateOrgCredential() {
    if (!confirm('Rotate the worker credential? The old code will stop working immediately.')) return;
    const code = document.getElementById('credValue');
    code.textContent = 'Rotating…';
    try {
        const data = await api('/admin/credential/rotate', 'POST');
        code.textContent = data.worker_credential || '—';
        const when = document.getElementById('credRotatedAt');
        if (when && data.rotated_at) {
            when.textContent = `last rotated ${new Date(data.rotated_at).toLocaleString()}`;
        }
        alert('Credential rotated. Share the new code with your workers.');
    } catch (e) {
        code.textContent = `error: ${e.message}`;
        alert(`Rotate failed: ${e.message}`);
    }
}

async function copyOrgCredential() {
    const code = document.getElementById('credValue');
    if (!code || !code.textContent) return;
    try {
        await navigator.clipboard.writeText(code.textContent);
        const btn = document.getElementById('btnCopyCred');
        if (btn) {
            const original = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check"></i>';
            setTimeout(() => { btn.innerHTML = original; }, 1400);
        }
    } catch (_) {
        alert('Copy failed — select the text manually.');
    }
}

// extend the settings-open hook to load the credential for admins
(function() {
    const btnSettings = document.getElementById('btnSettings');
    if (!btnSettings) return;
    btnSettings.addEventListener('click', () => {
        if (!isAdmin) return;
        // only CEO / c_suite / HR can view credential; backend enforces anyway
        const role = (currentUser && currentUser.role) || currentUserRole;
        if (role === 'ceo' || role === 'c_suite' || role === 'hr') {
            loadOrgCredential();
        }
        const btnRotate = document.getElementById('btnRotateCred');
        if (btnRotate) btnRotate.addEventListener('click', rotateOrgCredential);
        const btnCopy = document.getElementById('btnCopyCred');
        if (btnCopy) btnCopy.addEventListener('click', copyOrgCredential);
    });
})();


// ============================================================================
// SEND BINDING (btnSend + Enter)
// ============================================================================

(function bindSendButton() {
    // # SEND-BIND
    const btn = document.getElementById('btnSend');
    const input = document.getElementById('promptInput');
    if (!btn) {
        console.warn('[acd] btnSend not found — messages cannot be sent');
        return;
    }
    btn.addEventListener('click', () => {
        const v = (input && input.value) || '';
        if (!v.trim()) return;
        if (input) input.value = '';
        sendMessage(v);
    });
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                btn.click();
            }
        });
    }
    console.log('[acd] send button wired');
})();


// ============================================================================
// SIDEBAR WIRING
// ============================================================================

(function wireSidebar() {
    const openBtn = document.getElementById('btnSidebar');
    const closeBtn = document.getElementById('btnCloseSidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (openBtn) openBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (backdrop) backdrop.addEventListener('click', closeSidebar);
})();
