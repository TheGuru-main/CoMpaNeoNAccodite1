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
    // # ORG-EXTRAS-JS
    const phone = document.getElementById('orgPhone').value.trim();
    const password = document.getElementById('orgPassword').value;
    const org_name = document.getElementById('orgName').value.trim();
    const org_email = (document.getElementById('orgEmail') || {}).value || '';
    const country = (document.getElementById('orgCountry') || {}).value || 'Nigeria';
    const org_type = (document.getElementById('orgType') || {}).value || 'software';
    const goals = (document.getElementById('orgGoals') || {}).value || '';
    const ai_temperament = (document.getElementById('orgTemperament') || {}).value || 'sanguine';

    if (!phone || !password || !org_name) {
        alert('Phone, password, and organization name are required.');
        return;
    }
    try {
        const data = await api('/auth/org/create', 'POST', {
            phone, password,
            org_name,
            org_email: org_email || null,
            country,
            org_type,
            goals,
            ai_temperament,
        });
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
    // # LOADWS-ALIAS
    // Legacy name. The room system replaced /workspaces with /rooms.
    // Keep the call site working by delegating to loadRooms().
    return loadRooms();
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
let activeOrgId = null;
let dmPartner = null;

async function loadMe() {
    try {
        const me = await api('/auth/me');
        currentUserRole = me.primary_role || 'owner';
        isAdmin = !!me.is_admin;
        hasOrg = !!me.has_org;
        currentUser = Object.assign({}, currentUser || {}, me.user, {
            role: currentUserRole,
            orgs: me.orgs || [],
        });
        // ORG-ROOM-CREATE
        const activeOrgs = (me.orgs || []).filter(o => o.credential_active);
        activeOrgId = activeOrgs.length ? activeOrgs[0].org_id : null;
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
    updateInviteButtonVisibility();
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
    // ORG-ROOM-CREATE
    const type = document.getElementById('newRoomType').value;
    const name = document.getElementById('newRoomName').value.trim();
    if (!name) { alert('Give the workspace a name.'); return; }

    const orgTypes = new Set(['department', 'team', 'meeting', 'organization']);
    const isOrgType = orgTypes.has(type);

    try {
        let room;
        if (isOrgType) {
            if (!activeOrgId) {
                alert('You are not in an organization. Departments / teams / meetings / org rooms are org-only.');
                return;
            }
            room = await api(`/orgs/${activeOrgId}/rooms`, 'POST', {
                workspace_type: type,
                name: name,
            });
        } else {
            // personal_brainstorm / group
            room = await api('/rooms', 'POST', {
                workspace_type: type,
                project_name: name,
            });
        }
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
    // ORG-ROOM-CREATE: org-only types are hidden for solo users
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
        // AI-DEDUP-V2: mark ai_msg_id rendered so WS echo is skipped
        if (data && data.ai_msg_id) _renderedIds.add(data.ai_msg_id);
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


// ============================================================================
// INVITE MEMBER
// ============================================================================


async function sendInvite() {
    const room = roomList.find(r => r.id === currentRoomId);
    if (!room) return;
    const phone = document.getElementById('invitePhone').value.trim();
    const out = document.getElementById('inviteResult');
    if (!phone) { out.textContent = 'Enter a phone number.'; return; }
    out.textContent = 'Looking up…';
    try {
        const data = await api(`/rooms/${currentRoomId}/members`, 'POST', { phone });
        if (data.already_member) {
            out.innerHTML = '<span style="color:var(--aqua-bright);">Already a member.</span>';
        } else {
            out.innerHTML = `<span style="color:#86efac;">Added ${escapeHtml(data.invited || phone)}.</span>`;
        }
    } catch (e) {
        out.innerHTML = `<span style="color:#f3a9c1;">${escapeHtml(e.message)}</span>`;
    }
}

function updateInviteButtonVisibility() {
    const btn = document.getElementById('btnInvite');
    if (!btn) return;
    const room = roomList.find(r => r.id === currentRoomId);
    const isPrivate = !room || room.workspace_type === 'personal_brainstorm';
    btn.style.display = isPrivate ? 'none' : '';
}

// hook invite button + modal close + Enter in phone field
(function wireInvite() {
    const btn = document.getElementById('btnInvite');
    if (btn) btn.addEventListener('click', openInviteModal);
    const send = document.getElementById('btnSendInvite');
    if (send) send.addEventListener('click', sendInvite);
    const close = document.getElementById('btnCloseInvite');
    if (close) close.addEventListener('click', () => {
        document.getElementById('inviteModal').style.display = 'none';
    });
    const input = document.getElementById('invitePhone');
    if (input) input.addEventListener('keydown', e => {
        if (e.key === 'Enter') sendInvite();
    });
})();


// ============================================================================
// PROFILE
// ============================================================================

async function openProfile() {
    const modal = document.getElementById('profileModal');
    const body = document.getElementById('profileBody');
    if (!modal || !body) return;
    modal.style.display = 'flex';
    body.innerHTML = '<p style="opacity:.6;">Loading…</p>';
    try {
        const p = await api('/auth/profile');
        // PROFILE-ORG-BRAIN
        const orgs = (p.orgs || []).map(o => {
            const status = o.brain_status || (o.ai_uid ? 'active' : 'pending');
            const brainLine = status === 'active'
                ? `<div class="profile-org-meta" style="opacity:.6; word-break:break-all;">
                       <span class="k" style="font-size:0.68rem; text-transform:uppercase; letter-spacing:0.05em; opacity:.6;">org brain</span>
                       <div style="font-family:var(--font-mono); font-size:0.78rem; margin-top:0.15rem;">${escapeHtml(o.ai_uid || '—')}</div>
                   </div>`
                : `<div class="profile-org-meta" style="opacity:.55; font-style:italic;">
                       org brain: not yet generated — create it in the dashboard
                   </div>`;
            return `
                <div class="profile-org">
                    <div class="profile-org-name">${escapeHtml(o.org_name || '')}</div>
                    <div class="profile-org-meta">${escapeHtml(o.role || '')}${o.department ? ' · ' + escapeHtml(o.department) : ''}${o.title ? ' · ' + escapeHtml(o.title) : ''}</div>
                    <div class="profile-org-meta" style="opacity:.55;">${o.credential_active ? 'member active' : 'membership pending'}</div>
                    ${brainLine}
                </div>`;
        }).join('') || '<p style="opacity:.5; font-size:0.8rem;">No organization memberships</p>';

        body.innerHTML = `
            <div class="profile-header">
                <div class="profile-avatar"><i class="fa-solid fa-user-circle"></i></div>
                <div>
                    <div class="profile-name">${escapeHtml(p.full_name || '')}</div>
                    <div class="profile-phone">${escapeHtml(p.phone || '')}</div>
                </div>
            </div>
            <div class="profile-grid">
                <div class="profile-kv"><span class="k">Country</span><span class="v">${escapeHtml(p.country || '')}</span></div>
                <div class="profile-kv"><span class="k">Language</span><span class="v">${escapeHtml(p.language || '')}</span></div>
                <div class="profile-kv"><span class="k">Temperament</span><span class="v">${escapeHtml(p.temperament || '')}</span></div>
                <div class="profile-kv"><span class="k">Account type</span><span class="v">${escapeHtml(p.account_type || 'regular')}</span></div>
                <div class="profile-kv"><span class="k">Start row</span><span class="v">${escapeHtml(String(p.start_row ?? '—'))}</span></div>
                <div class="profile-kv"><span class="k">Start col</span><span class="v">${escapeHtml(String(p.start_col ?? '—'))}</span></div>
                <div class="profile-kv"><span class="k">Brain UID</span><span class="v">${escapeHtml(p.personal_ai_uid || '—')}</span></div>
                <div class="profile-kv"><span class="k">Joined</span><span class="v">${p.created_at ? new Date(p.created_at).toLocaleString() : '—'}</span></div>
            </div>
            <h4 style="margin-top:1rem;"><i class="fa-solid fa-sitemap"></i> Organizations</h4>
            <div style="margin-top:0.5rem;">${orgs}</div>
        `;
    } catch (e) {
        body.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

// ============================================================================
// DOCUMENTS SPACE
// ============================================================================

async function openDocuments() {
    hideAllPanels();
    const panel = document.getElementById('docsPanel');
    if (!panel) return;
    panel.style.display = 'block';
    const box = document.getElementById('docsResults');
    box.innerHTML = '<p style="opacity:.6;">Loading artifacts…</p>';
    try {
        const data = await api('/documents');
        if (!data || !data.items || !data.items.length) {
            box.innerHTML = `
                <p style="opacity:.55; padding:1rem 0;">
                    No documents yet. Generated PDFs, ZIPs, summaries, and
                    iterations will appear here as your work produces them.
                </p>`;
            return;
        }
        const iconFor = {
            summary:   'fa-file-lines',
            pdf:       'fa-file-pdf',
            archive:   'fa-file-zipper',
            table:     'fa-table',
            image:     'fa-image',
            diagram:   'fa-diagram-project',
            repo:      'fa-code-branch',
            iteration: 'fa-brain',
            note:      'fa-note-sticky',
        };
        box.innerHTML = data.items.map(it => `
            <div class="doc-item">
                <div class="doc-icon"><i class="fa-solid ${iconFor[it.kind] || 'fa-file'}"></i></div>
                <div class="doc-body">
                    <div class="doc-name">${escapeHtml(it.name || 'untitled')}</div>
                    <div class="doc-meta">
                        <span class="doc-kind">${escapeHtml(it.kind)}</span>
                        ${it.size ? `<span>${Math.round(it.size / 1024)} KB</span>` : ''}
                        <span>${it.created_at ? new Date(it.created_at).toLocaleDateString() : ''}</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

// ============================================================================
// SCREEN ISOLATION
// ============================================================================

function hideAllPanels() {
    const ids = ['researchPanel', 'dmPanel', 'docsPanel'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}

function showHome() {
    hideAllPanels();
}

// ============================================================================
// WIRING
// ============================================================================

(function wireProfileAndDocs() {
    const btnProfile = document.getElementById('btnProfile');
    if (btnProfile) btnProfile.addEventListener('click', openProfile);
    const btnCloseProfile = document.getElementById('btnCloseProfile');
    if (btnCloseProfile) btnCloseProfile.addEventListener('click', () => {
        document.getElementById('profileModal').style.display = 'none';
    });
    const btnCloseDocs = document.getElementById('btnCloseDocs');
    if (btnCloseDocs) btnCloseDocs.addEventListener('click', () => {
        document.getElementById('docsPanel').style.display = 'none';
    });

    // Rebind nav so each action isolates the panel
    document.querySelectorAll('.nav-link, .header-nav .nav-link').forEach(link => {
        // remove existing listener is hard; add a capturing one first that
        // wins by stopping propagation on the previous handler is impossible
        // without refactoring. Instead, we add a second listener that runs
        // after and enforces the correct panel state.
        link.addEventListener('click', () => {
            const action = link.dataset.action;
            if (action === 'home') {
                showHome();
            } else if (action === 'research') {
                hideAllPanels();
            } else if (action === 'workspace') {
                // workspace nav now opens the documents space
                setTimeout(openDocuments, 0);
            } else if (action === 'messages') {
                hideAllPanels();
            } else if (action === 'train') {
                hideAllPanels();
            }
        });
    });
})();


// ============================================================================
// INPUT + CHIP VISIBILITY
// ============================================================================

function updateInputVisibility() {
    // # INPUT-VISIBILITY
    const inputArea = document.getElementById('inputArea');
    const chips = document.getElementById('roomChips');
    const room = roomList.find(r => r.id === currentRoomId);

    if (!currentRoomId || !room) {
        if (inputArea) inputArea.style.display = 'none';
        if (chips) chips.style.display = 'none';
        return;
    }

    if (inputArea) inputArea.style.display = '';
    if (chips) {
        const isPrivate = room.workspace_type === 'personal_brainstorm';
        chips.style.display = isPrivate ? 'none' : '';
        const cnt = document.getElementById('chipMemberCount');
        if (cnt) cnt.textContent = String(room.member_count || 1);
    }
}

// ============================================================================
// DM: start conversation from phone
// ============================================================================

function dmNormalizePhone() {
    const cc = document.getElementById('dmCountryCode').value;
    let raw = (document.getElementById('dmNewPhone').value || '').replace(/\D/g, '');
    if (!raw) return '';
    if (raw.startsWith('0')) raw = raw.slice(1);
    return `+${cc}${raw}`;
}

async function dmStartConversation() {
    const phone = dmNormalizePhone();
    if (!phone || phone.length < 8) {
        alert('Enter a valid phone number.');
        return;
    }
    // Verify the user exists by trying to open the thread
    document.getElementById('dmThread').style.display = 'block';
    document.getElementById('dmList').style.display = 'none';
    document.getElementById('dmNewPhone').value = '';
    dmPartner = phone;
    await openDMThread(phone);
}

// ============================================================================
// INLINE INVITE CHIP
// ============================================================================

function wireRoomChips() {
    const inv = document.getElementById('chipInvite');
    if (inv) inv.addEventListener('click', openInviteModal);
    const mem = document.getElementById('chipMembers');
    if (mem) mem.addEventListener('click', listRoomMembers);
}

async function listRoomMembers() {
    if (!currentRoomId) return;
    try {
        const members = await api(`/rooms/${currentRoomId}/members`);
        const list = members.map(m => `  • ${m.full_name} (${m.phone}) — ${m.role}`).join('\n');
        alert(`Room members (${members.length}):\n${list || '  none'}`);
    } catch (e) {
        alert(`Could not load members: ${e.message}`);
    }
}

// ============================================================================
// BOOT WIRING
// ============================================================================

(function wireInputAndChips() {
    wireRoomChips();
    const btnDmStart = document.getElementById('btnDmStart');
    if (btnDmStart) btnDmStart.addEventListener('click', dmStartConversation);
    const inp = document.getElementById('dmNewPhone');
    if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') dmStartConversation(); });

    // Ensure the input is hidden on first paint
    updateInputVisibility();
})();

// Hook into openRoom to update visibility
const _origOpenRoom = openRoom;
openRoom = async function(id) {
    await _origOpenRoom(id);
    updateInputVisibility();
};

// Hide input when logging out
const _origLogout = logout;
logout = function() {
    currentRoomId = null;
    updateInputVisibility();
    _origLogout();
};

// Reload messages for the current room when tabs return (visibilitychange)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && currentRoomId) {
        openRoom(currentRoomId).catch(() => {});
    }
});


// ============================================================================
// NAV UNIFIED (single listener, one panel at a time)
// ============================================================================

function _openPanel(which) {
    // close everything first
    ['researchPanel', 'dmPanel', 'docsPanel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    if (which === 'research') {
        try { openResearch(); } catch (_) {}
    } else if (which === 'dm') {
        const el = document.getElementById('dmPanel');
        if (el) el.style.display = 'block';
        try { loadDMConversations(); } catch (_) {}
    } else if (which === 'docs') {
        try { openDocuments(); } catch (_) {}
    }
    // 'home' → all closed; chat box visible
}

(function bindNavUnified() {
    // # NAV-UNIFIED
    const links = document.querySelectorAll('.header-nav .nav-link, .bottom-nav .nav-link');
    links.forEach(link => {
        // replace by cloning to drop any earlier listeners
        const clone = link.cloneNode(true);
        link.parentNode.replaceChild(clone, link);
    });
    document.querySelectorAll('.header-nav .nav-link, .bottom-nav .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            const action = link.dataset.action;
            if (action === 'home')       _openPanel('home');
            else if (action === 'research') _openPanel('research');
            else if (action === 'workspace') _openPanel('docs');
            else if (action === 'messages') _openPanel('dm');
            else if (action === 'train') {
                _openPanel('home');
                try { openTrainingModal(); } catch (_) {}
            }
        });
    });
})();

// ============================================================================
// INPUT VISIBILITY (JS only — no CSS !important)
// ============================================================================

function updateInputVisibility() {
    const inputArea = document.getElementById('inputArea');
    const chips = document.getElementById('roomChips');
    const onMain = document.getElementById('mainScreen')?.classList.contains('active');
    const room = roomList.find(r => r.id === currentRoomId);

    if (!onMain || !currentRoomId) {
        if (inputArea) inputArea.style.display = 'none';
        if (chips) chips.style.display = 'none';
        return;
    }
    if (inputArea) inputArea.style.display = 'flex';
    if (chips) {
        const isPrivate = room && room.workspace_type === 'personal_brainstorm';
        chips.style.display = isPrivate ? 'none' : 'flex';
        const cnt = document.getElementById('chipMemberCount');
        if (cnt && room) cnt.textContent = String(room.member_count || 1);
    }
}

// show/hide based on screen
const _origShowScreen = showScreen;
showScreen = function(id) {
    _origShowScreen(id);
    document.body.classList.toggle('logged-in', id === 'mainScreen');
    setTimeout(updateInputVisibility, 0);
};

// ============================================================================
// LAST ROOM PERSISTENCE
// ============================================================================

function rememberRoom(id) {
    if (!id) return;
    try { localStorage.setItem('acd_last_room', id); } catch (_) {}
}

function forgetRoom() {
    try { localStorage.removeItem('acd_last_room'); } catch (_) {}
}

function recallRoom() {
    try { return localStorage.getItem('acd_last_room'); } catch (_) { return null; }
}

// wrap openRoom to remember
const _origOpenRoomPersist = openRoom;
openRoom = async function(id) {
    await _origOpenRoomPersist(id);
    rememberRoom(id);
    updateInputVisibility();
};

// wrap loadRooms to restore last room after list arrives
const _origLoadRooms = loadRooms;
loadRooms = async function() {
    await _origLoadRooms();
    // if a room was remembered and still exists, open it
    const last = recallRoom();
    if (last && roomList.find(r => r.id === last) && last !== currentRoomId) {
        await openRoom(last);
        return;
    }
    // else if no active room, open the first
    if (!currentRoomId && roomList.length > 0) {
        await openRoom(roomList[0].id);
    }
    updateInputVisibility();
};

// wrap logout to forget
const _origLogoutPersist = logout;
logout = function() {
    forgetRoom();
    currentRoomId = null;
    updateInputVisibility();
    _origLogoutPersist();
};

// ============================================================================
// DM: hide compose when in thread, show when in list
// ============================================================================

const _origOpenDMThread = openDMThread;
openDMThread = async function(phone) {
    const compose = document.querySelector('.dm-compose');
    if (compose) compose.style.display = 'none';
    await _origOpenDMThread(phone);
};

const _origLoadDMConversations = loadDMConversations;
loadDMConversations = async function() {
    const compose = document.querySelector('.dm-compose');
    if (compose) compose.style.display = '';
    await _origLoadDMConversations();
};

// ============================================================================
// BOOT: ensure no input on auth, main screen state applied
// ============================================================================

(function bootVisibility() {
    document.body.classList.remove('logged-in');
    setTimeout(updateInputVisibility, 0);
})();


// ============================================================================
// ORG DASHBOARD SCREEN
// ============================================================================

let orgActiveTab = 'pending';

async function openOrgScreen() {
    showScreen('orgScreen');
    // refresh identity so we know the role
    try { await loadMe(); } catch (_) {}
    document.getElementById('orgScreenTitle').textContent = 'Organization';
    await renderOrgTab(orgActiveTab);
}

async function renderOrgTab(tab) {
    orgActiveTab = tab;
    document.querySelectorAll('.org-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.otab === tab);
    });
    const body = document.getElementById('orgBody');
    body.innerHTML = '<p style="opacity:.6; padding:1rem;">Loading…</p>';
    try {
        if (tab === 'pending')      return renderOrgPending(body);
        if (tab === 'members')      return renderOrgMembers(body);
        if (tab === 'credential')   return renderOrgCredential(body);
        if (tab === 'details')      return renderOrgDetails(body);
        if (tab === 'departments')  return renderOrgDepartments(body);
        if (tab === 'boards')       return renderOrgBoards(body);
    } catch (e) {
        body.innerHTML = `<p style="color:#f3a9c1; padding:1rem;">${escapeHtml(e.message)}</p>`;
    }
}

async function renderOrgPending(body) {
    const pending = await api('/admin/pending');
    if (!pending.length) {
        body.innerHTML = '<p class="org-empty">No pending signups.</p>';
        return;
    }
    body.innerHTML = pending.map(p => `
        <div class="org-row">
            <div>
                <div class="org-row-title">${escapeHtml(p.full_name || '')}</div>
                <div class="org-row-sub">${escapeHtml(p.phone || '')} · ${escapeHtml(p.department || '—')}</div>
            </div>
            <div class="org-actions">
                <button class="mini-btn ok" data-approve="${p.membership_id}"><i class="fa-solid fa-check"></i></button>
                <button class="mini-btn err" data-reject="${p.membership_id}"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>
    `).join('');
    body.querySelectorAll('[data-approve]').forEach(el => el.addEventListener('click', async () => {
        try { await api(`/admin/approve/${el.dataset.approve}`, 'POST'); renderOrgTab('pending'); }
        catch (e) { alert(e.message); }
    }));
    body.querySelectorAll('[data-reject]').forEach(el => el.addEventListener('click', async () => {
        if (!confirm('Reject this signup?')) return;
        try { await api(`/admin/reject/${el.dataset.reject}`, 'POST'); renderOrgTab('pending'); }
        catch (e) { alert(e.message); }
    }));
}

async function renderOrgMembers(body) {
    const members = await api('/admin/members');
    if (!members.length) {
        body.innerHTML = '<p class="org-empty">No active members yet.</p>';
        return;
    }
    body.innerHTML = members.map(m => `
        <div class="org-row">
            <div>
                <div class="org-row-title">${escapeHtml(m.full_name || '')}</div>
                <div class="org-row-sub">${escapeHtml(m.phone || '')} · ${escapeHtml(m.department || '—')} · ${escapeHtml(m.role || '')}</div>
            </div>
            <div class="org-actions">
                <select class="role-select" data-mid="${m.membership_id}">
                    ${['ceo','c_suite','hr','dept_head','manager','member','reviewer','viewer']
                        .map(r => `<option value="${r}" ${r === m.role ? 'selected' : ''}>${r}</option>`).join('')}
                </select>
            </div>
        </div>
    `).join('');
    body.querySelectorAll('.role-select').forEach(sel => sel.addEventListener('change', async () => {
        try {
            await api('/admin/role', 'POST', { membership_id: sel.dataset.mid, new_role: sel.value });
            sel.style.borderColor = 'var(--aqua)';
            setTimeout(() => { sel.style.borderColor = ''; }, 800);
        } catch (e) { alert(e.message); }
    }));
}

async function renderOrgCredential(body) {
    // # ORG-CRED-GEN
    const data = await api('/admin/credential');
    if (data.needs_generation) {
        body.innerHTML = `
            <p style="font-size:0.85rem; opacity:0.72; padding:0.5rem 0 0.75rem;">
                No worker credential has been created yet. Generate one to
                become the org brain uID and give your workers an entry point.
            </p>
            <button id="btnGenerateOrgCred" class="primary-btn">
                <i class="fa-solid fa-key"></i> Generate worker credential
            </button>
            <div id="orgCredMsg" style="font-size:0.8rem; margin-top:0.5rem;"></div>
        `;
        document.getElementById('btnGenerateOrgCred').addEventListener('click', async () => {
            const msg = document.getElementById('orgCredMsg');
            msg.textContent = 'Generating…';
            try {
                await api('/admin/credential/generate', 'POST');
                renderOrgTab('credential');
            } catch (e) {
                msg.innerHTML = `<span style="color:#f3a9c1;">${escapeHtml(e.message)}</span>`;
            }
        });
        return;
    }

    body.innerHTML = `
        <p style="font-size:0.82rem; opacity:0.72; padding:0.5rem 0 0.75rem;">
            Share this one credential with every worker joining your org.
            Rotating invalidates the old one.
        </p>
        <div class="cred-box">
            <code id="orgCredValue">${escapeHtml(data.worker_credential || '—')}</code>
            <button id="btnCopyOrgCred" class="mini-btn" title="Copy"><i class="fa-solid fa-copy"></i></button>
        </div>
        <button id="btnRotateOrgCred" class="primary-btn secondary-btn" style="margin-top:0.75rem; font-size:0.85rem;">
            <i class="fa-solid fa-arrows-rotate"></i> Rotate credential
        </button>
        <div style="font-size:0.72rem; opacity:0.55; margin-top:0.6rem;">brain uID: ${escapeHtml(data.ai_uid || '—')}</div>
        <div style="font-size:0.72rem; opacity:0.55; margin-top:0.3rem;">
            ${data.rotated_at ? 'last rotated ' + new Date(data.rotated_at).toLocaleString() : ''}
        </div>
    `;
    document.getElementById('btnCopyOrgCred').addEventListener('click', () => {
        navigator.clipboard.writeText(data.worker_credential || '');
    });
    document.getElementById('btnRotateOrgCred').addEventListener('click', async () => {
        if (!confirm('Rotate credential? Old code stops working immediately.')) return;
        try { await api('/admin/credential/rotate', 'POST'); renderOrgTab('credential'); }
        catch (e) { alert(e.message); }
    });
}

async function renderOrgDetails(body) {
    const d = await api('/admin/org-details');
    body.innerHTML = `
        <label class="field-label">Organization name</label>
        <input type="text" id="orgEditName" value="${escapeHtml(d.name || '')}" />
        <label class="field-label">Email</label>
        <input type="text" id="orgEditEmail" value="${escapeHtml(d.email || '')}" />
        <label class="field-label">Country</label>
        <input type="text" id="orgEditCountry" value="${escapeHtml(d.country || '')}" />
        <label class="field-label">Type</label>
        <select id="orgEditType">
            ${['software','healthcare','school','finance','legal','government','ngo','research','retail','other']
              .map(t => `<option value="${t}" ${t === (d.settings?.org_type || 'software') ? 'selected' : ''}>${t}</option>`).join('')}
        </select>
        <label class="field-label">Goals</label>
        <input type="text" id="orgEditGoals" value="${escapeHtml(d.settings?.goals || '')}" />
        <label class="field-label">AI temperament</label>
        <select id="orgEditTemp">
            ${['sanguine','melancholy','phlegmatic','choleric']
              .map(t => `<option value="${t}" ${t === (d.settings?.ai_temperament || 'sanguine') ? 'selected' : ''}>${t}</option>`).join('')}
        </select>
        <button id="btnSaveOrgDetails" class="primary-btn" style="margin-top:1rem;">Save changes</button>
        <div id="orgDetailsMsg" style="font-size:0.8rem; margin-top:0.5rem;"></div>
    `;
    document.getElementById('btnSaveOrgDetails').addEventListener('click', async () => {
        const msg = document.getElementById('orgDetailsMsg');
        msg.textContent = 'Saving…';
        try {
            await api('/admin/org-details', 'PUT', {
                name: document.getElementById('orgEditName').value,
                email: document.getElementById('orgEditEmail').value,
                country: document.getElementById('orgEditCountry').value,
                org_type: document.getElementById('orgEditType').value,
                goals: document.getElementById('orgEditGoals').value,
                ai_temperament: document.getElementById('orgEditTemp').value,
            });
            msg.innerHTML = '<span style="color:#86efac;">Saved.</span>';
        } catch (e) {
            msg.innerHTML = `<span style="color:#f3a9c1;">${escapeHtml(e.message)}</span>`;
        }
    });
}

async function renderOrgDepartments(body) {
    const list = await api('/admin/departments');
    body.innerHTML = `
        <div class="org-add-row">
            <input type="text" id="newDeptName" placeholder="Department name (e.g. Engineering)" />
            <button id="btnAddDept" class="primary-btn" style="width:auto; padding:0 1rem;">
                <i class="fa-solid fa-plus"></i>
            </button>
        </div>
        <div id="orgDeptList">
            ${list.length === 0 ? '<p class="org-empty">No departments yet.</p>' :
              list.map(d => `
                <div class="org-row">
                    <div>
                        <div class="org-row-title">${escapeHtml(d.name)}</div>
                        <div class="org-row-sub">created ${d.created_at ? new Date(d.created_at).toLocaleDateString() : ''}</div>
                    </div>
                </div>
              `).join('')}
        </div>
    `;
    document.getElementById('btnAddDept').addEventListener('click', async () => {
        const name = document.getElementById('newDeptName').value.trim();
        if (!name) return;
        try { await api('/admin/departments', 'POST', { name }); renderOrgTab('departments'); }
        catch (e) { alert(e.message); }
    });
}

async function renderOrgBoards(body) {
    const list = await api('/admin/boards');
    body.innerHTML = `
        <div class="org-add-row">
            <input type="text" id="newBoardName" placeholder="Board name (e.g. security)" />
            <button id="btnAddBoard" class="primary-btn" style="width:auto; padding:0 1rem;">
                <i class="fa-solid fa-plus"></i>
            </button>
        </div>
        <div>
            ${list.length === 0 ? '<p class="org-empty">No boards yet.</p>' :
              list.map(b => `
                <div class="org-row">
                    <div>
                        <div class="org-row-title">${escapeHtml(b.name)}</div>
                        <div class="org-row-sub">min severity: ${escapeHtml(b.min_severity)} · kinds: ${(b.pattern_kinds || []).join(', ') || 'any'}</div>
                    </div>
                    <button class="mini-btn err" data-del-board="${b.id}"><i class="fa-solid fa-trash"></i></button>
                </div>
              `).join('')}
        </div>
    `;
    document.getElementById('btnAddBoard').addEventListener('click', async () => {
        const name = document.getElementById('newBoardName').value.trim();
        if (!name) return;
        try { await api('/admin/boards', 'POST', { name }); renderOrgTab('boards'); }
        catch (e) { alert(e.message); }
    });
    body.querySelectorAll('[data-del-board]').forEach(el => el.addEventListener('click', async () => {
        if (!confirm('Delete this board?')) return;
        try { await api(`/admin/boards/${el.dataset.delBoard}`, 'DELETE'); renderOrgTab('boards'); }
        catch (e) { alert(e.message); }
    }));
}

// ============================================================================
// INVITE MODAL REBUILD (3 tabs: friends / phone / link)
// ============================================================================

let inviteActiveTab = 'search';



async function inviteSearch() {
    const q = document.getElementById('inviteSearchInput').value.trim();
    const box = document.getElementById('inviteSearchResults');
    if (q.length < 2) {
        box.innerHTML = '<p class="org-empty">Type a name or phone to search</p>';
        return;
    }
    box.innerHTML = '<p style="opacity:.6;">Searching…</p>';
    try {
        const data = await api(`/contacts/search?q=${encodeURIComponent(q)}`);
        if (!data.results || !data.results.length) {
            box.innerHTML = '<p class="org-empty">None found</p>';
            return;
        }
        box.innerHTML = data.results.map(r => `
            <div class="invite-result" data-uid="${r.user_id}" data-phone="${escapeHtml(r.phone)}">
                <div>
                    <div class="org-row-title">${escapeHtml(r.full_name || '')}</div>
                    <div class="org-row-sub">${escapeHtml(r.phone || '')}</div>
                </div>
                <button class="mini-btn ok"><i class="fa-solid fa-plus"></i></button>
            </div>
        `).join('');
        box.querySelectorAll('.invite-result').forEach(el => el.addEventListener('click', async () => {
            await inviteByPhone(el.dataset.phone);
        }));
    } catch (e) {
        box.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

async function inviteByPhone(phone) {
    const box = document.getElementById('inviteSearchResults') || document.getElementById('invitePhoneResult');
    try {
        const data = await api(`/rooms/${currentRoomId}/members`, 'POST', { phone });
        const msg = data.already_member ? 'Already a member.' : `Added ${phone}.`;
        const ok = document.createElement('div');
        ok.style.cssText = 'color:#86efac; font-size:0.8rem; padding:0.3rem 0;';
        ok.textContent = msg;
        box.appendChild(ok);
    } catch (e) {
        const err = document.createElement('div');
        err.style.cssText = 'color:#f3a9c1; font-size:0.8rem; padding:0.3rem 0;';
        err.textContent = e.message;
        box.appendChild(err);
    }
}

async function inviteByPhoneInput() {
    const cc = document.getElementById('inviteCountryCode').value;
    let raw = (document.getElementById('invitePhoneInput').value || '').replace(/\D/g, '');
    if (raw.startsWith('0')) raw = raw.slice(1);
    const phone = `+${cc}${raw}`;
    if (phone.length < 8) { alert('Invalid phone'); return; }
    await inviteByPhone(phone);
}

// ============================================================================
// WIRING
// ============================================================================

(function wireOrgAndInvite() {
    const btnOrg = document.getElementById('btnOrg');
    if (btnOrg) btnOrg.addEventListener('click', openOrgScreen);
    const back = document.getElementById('btnBackFromOrg');
    if (back) back.addEventListener('click', () => showScreen('mainScreen'));

    document.querySelectorAll('.org-tab').forEach(t => {
        t.addEventListener('click', () => renderOrgTab(t.dataset.otab));
    });

    document.querySelectorAll('.invite-tab').forEach(t => {
        t.addEventListener('click', () => switchInviteTab(t.dataset.itab));
    });
    const si = document.getElementById('inviteSearchInput');
    if (si) {
        let tmr = null;
        si.addEventListener('input', () => {
            clearTimeout(tmr);
            tmr = setTimeout(inviteSearch, 300);
        });
    }
    const sendPhone = document.getElementById('btnSendInvitePhone');
    if (sendPhone) sendPhone.addEventListener('click', inviteByPhoneInput);
    const closeInv = document.getElementById('btnCloseInvite');
    if (closeInv) closeInv.addEventListener('click', () => {
        document.getElementById('inviteModal').style.display = 'none';
    });
    const copyLink = document.getElementById('btnCopyInviteLink');
    if (copyLink) copyLink.addEventListener('click', () => {
        const v = document.getElementById('inviteLinkValue').textContent;
        navigator.clipboard.writeText(v);
    });

    const chipInvite = document.getElementById('chipInvite');
    if (chipInvite) chipInvite.addEventListener('click', openInviteModal);
    const hdrInvite = document.getElementById('btnInvite');
    if (hdrInvite) hdrInvite.addEventListener('click', openInviteModal);
})();

// show org button on main screen when user has an org
const _origUpdateInputVisibilityForOrg = updateInputVisibility;
updateInputVisibility = function() {
    _origUpdateInputVisibilityForOrg();
    const btn = document.getElementById('btnOrg');
    if (btn) btn.style.display = hasOrg ? '' : 'none';
};


// ORG-BTN-VIS — toggle org button visibility on hasOrg
const _origUpdateInputVisibilityForOrgBtn = updateInputVisibility;
updateInputVisibility = function() {
    _origUpdateInputVisibilityForOrgBtn();
    const btn = document.getElementById('btnOrg');
    if (btn) btn.style.display = hasOrg ? '' : 'none';
};


// ============================================================================
// INVITE MODAL (single source of truth)
// ============================================================================

function openInviteModal() {
    // # INVITE-CLEAN
    const room = roomList.find(r => r.id === currentRoomId);
    if (!room) { alert('Open a room first.'); return; }
    if (room.workspace_type === 'personal_brainstorm') {
        alert('Personal brainstorm is private. Create a Group to invite.');
        return;
    }
    // share link
    const link = `${window.location.origin}/app/#room=${currentRoomId}`;
    const lv = document.getElementById('inviteLinkValue');
    if (lv) lv.textContent = link;

    // reset
    switchInviteTab('org');
    document.getElementById('inviteSearchInput').value = '';
    document.getElementById('inviteSearchResults').innerHTML =
        '<p class="org-empty">Type a name or phone to search</p>';
    document.getElementById('invitePhoneInput').value = '';
    document.getElementById('invitePhoneResult').innerHTML = '';

    document.getElementById('inviteModal').style.display = 'flex';
    loadInviteCandidates();
}

function switchInviteTab(tab) {
    // # INVITE-CLEAN
    document.querySelectorAll('.invite-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.itab === tab);
    });
    const map = {
        org: 'inviteBodyOrg',
        contacts: 'inviteBodyContacts',
        phone: 'inviteBodyPhone',
        link: 'inviteBodyLink',
    };
    Object.entries(map).forEach(([k, id]) => {
        const el = document.getElementById(id);
        if (el) el.style.display = k === tab ? '' : 'none';
    });
    const sendPhone = document.getElementById('btnSendInvitePhone');
    if (sendPhone) sendPhone.style.display = tab === 'phone' ? '' : 'none';
    if (tab === 'contacts') {
        setTimeout(() => document.getElementById('inviteSearchInput')?.focus(), 50);
    }
}

async function loadInviteCandidates() {
    const box = document.getElementById('inviteCandidates');
    if (!box) return;
    box.innerHTML = '<p style="opacity:.6;">Loading candidates…</p>';
    try {
        const data = await api(`/rooms/${currentRoomId}/candidates`);
        const list = data.candidates || [];
        if (!list.length) {
            box.innerHTML = '<p class="org-empty">No one left to add</p>';
            return;
        }
        box.innerHTML = list.map(c => `
            <div class="invite-result" data-phone="${escapeHtml(c.phone)}">
                <div>
                    <div class="org-row-title">${escapeHtml(c.full_name || '')}</div>
                    <div class="org-row-sub">${escapeHtml(c.phone || '')}${c.department ? ' · ' + escapeHtml(c.department) : ''}${c.role ? ' · ' + escapeHtml(c.role) : ''}</div>
                </div>
                <button class="mini-btn ok"><i class="fa-solid fa-plus"></i></button>
            </div>
        `).join('');
        box.querySelectorAll('.invite-result').forEach(el => el.addEventListener('click', async () => {
            await inviteByPhone(el.dataset.phone, box);
        }));
    } catch (e) {
        box.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

async function inviteSearch() {
    const q = document.getElementById('inviteSearchInput').value.trim();
    const box = document.getElementById('inviteSearchResults');
    if (q.length < 2) {
        box.innerHTML = '<p class="org-empty">Type a name or phone to search</p>';
        return;
    }
    box.innerHTML = '<p style="opacity:.6;">Searching…</p>';
    try {
        const data = await api(`/contacts/search?q=${encodeURIComponent(q)}`);
        if (!data.results || !data.results.length) {
            box.innerHTML = '<p class="org-empty">None found</p>';
            return;
        }
        box.innerHTML = data.results.map(r => `
            <div class="invite-result" data-phone="${escapeHtml(r.phone)}">
                <div>
                    <div class="org-row-title">${escapeHtml(r.full_name || '')}</div>
                    <div class="org-row-sub">${escapeHtml(r.phone || '')}</div>
                </div>
                <button class="mini-btn ok"><i class="fa-solid fa-plus"></i></button>
            </div>
        `).join('');
        box.querySelectorAll('.invite-result').forEach(el => el.addEventListener('click', async () => {
            await inviteByPhone(el.dataset.phone, box);
        }));
    } catch (e) {
        box.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
}

async function inviteByPhone(phone, targetBox) {
    const box = targetBox || document.getElementById('inviteSearchResults') || document.getElementById('invitePhoneResult');
    try {
        const data = await api(`/rooms/${currentRoomId}/members`, 'POST', { phone });
        const msg = data.already_member ? 'Already a member.' : `Added ${phone}.`;
        const ok = document.createElement('div');
        ok.style.cssText = 'color:#86efac; font-size:0.8rem; padding:0.3rem 0;';
        ok.textContent = msg;
        box.appendChild(ok);
    } catch (e) {
        const err = document.createElement('div');
        err.style.cssText = 'color:#f3a9c1; font-size:0.8rem; padding:0.3rem 0;';
        err.textContent = e.message;
        box.appendChild(err);
    }
}

async function inviteByPhoneInput() {
    const cc = document.getElementById('inviteCountryCode').value;
    let raw = (document.getElementById('invitePhoneInput').value || '').replace(/\D/g, '');
    if (raw.startsWith('0')) raw = raw.slice(1);
    const phone = `+${cc}${raw}`;
    if (phone.length < 8) { alert('Invalid phone'); return; }
    const box = document.getElementById('invitePhoneResult');
    await inviteByPhone(phone, box);
}

// ============================================================================
// INVITE WIRING (idempotent — safe to re-run)
// ============================================================================

(function wireInviteClean() {
    // bind tabs once
    document.querySelectorAll('.invite-tab').forEach(t => {
        if (t.dataset.bound === '1') return;
        t.dataset.bound = '1';
        t.addEventListener('click', () => switchInviteTab(t.dataset.itab));
    });
    // chipInvite
    const chip = document.getElementById('chipInvite');
    if (chip && chip.dataset.bound !== '1') {
        chip.dataset.bound = '1';
        chip.addEventListener('click', openInviteModal);
    }
    // btnInvite
    const btn = document.getElementById('btnInvite');
    if (btn && btn.dataset.bound !== '1') {
        btn.dataset.bound = '1';
        btn.addEventListener('click', openInviteModal);
    }
    // search input
    const si = document.getElementById('inviteSearchInput');
    if (si && si.dataset.bound !== '1') {
        si.dataset.bound = '1';
        let tmr = null;
        si.addEventListener('input', () => {
            clearTimeout(tmr);
            tmr = setTimeout(inviteSearch, 300);
        });
    }
    // phone add button
    const sp = document.getElementById('btnSendInvitePhone');
    if (sp && sp.dataset.bound !== '1') {
        sp.dataset.bound = '1';
        sp.addEventListener('click', inviteByPhoneInput);
    }
    // close
    const cl = document.getElementById('btnCloseInvite');
    if (cl && cl.dataset.bound !== '1') {
        cl.dataset.bound = '1';
        cl.addEventListener('click', () => {
            document.getElementById('inviteModal').style.display = 'none';
        });
    }
    // copy link
    const cp = document.getElementById('btnCopyInviteLink');
    if (cp && cp.dataset.bound !== '1') {
        cp.dataset.bound = '1';
        cp.addEventListener('click', () => {
            const v = document.getElementById('inviteLinkValue').textContent;
            navigator.clipboard.writeText(v);
        });
    }
})();


// HEADER-INVITE-VIS — show header invite only in non-personal rooms
const _origUpdateInputVisibilityForHeaderInvite = updateInputVisibility;
updateInputVisibility = function() {
    _origUpdateInputVisibilityForHeaderInvite();
    const btn = document.getElementById('btnInvite');
    if (!btn) return;
    const room = roomList.find(r => r.id === currentRoomId);
    const show = room && room.workspace_type !== 'personal_brainstorm';
    btn.style.display = show ? '' : 'none';
};


// ============================================================================
// HOME STATE + GREETING
// ============================================================================

function greetingFor() {
    const h = new Date().getHours();
    if (h < 5)  return 'Working late';
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    if (h < 21) return 'Good evening';
    return 'Working late';
}

function showHomeState() {
    // # HOME-STATE
    currentRoomId = null;
    try { localStorage.removeItem('acd_last_room'); } catch (_) {}
    renderRoomBar();
    const title = document.getElementById('activeRoomTitle');
    if (title) title.textContent = 'Accodite Coding Agent';

    const chatBox = document.getElementById('chatBox');
    if (!chatBox) return;
    const name = (currentUser && (currentUser.full_name || currentUser.phone)) || 'there';
    const g = greetingFor();
    chatBox.innerHTML = `
        <div class="home-welcome">
            <div class="home-welcome-icon"><i class="fa-solid fa-brain"></i></div>
            <h2>${g}, ${escapeHtml(name)}.</h2>
            <p>${lastSessionLine()}</p>
            <div class="home-actions">
                <button class="home-action" data-new-room="personal_brainstorm">
                    <i class="fa-solid fa-brain"></i> New brainstorm
                </button>
                <button class="home-action" data-new-room="group">
                    <i class="fa-solid fa-users"></i> New group
                </button>
            </div>
        </div>
    `;
    chatBox.querySelectorAll('[data-new-room]').forEach(el => {
        el.addEventListener('click', () => {
            document.getElementById('newRoomType').value = el.dataset.newRoom;
            openNewRoomModal();
        });
    });

    updateInputVisibility();
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelector('[data-action="home"]')?.classList.add('active');
}

function lastSessionLine() {
    try {
        const last = localStorage.getItem('acd_last_room');
        if (last && roomList.length) {
            const r = roomList.find(x => x.id === last);
            if (r) return `Last session: ${escapeHtml(r.project_name)}. Pick it from the sidebar, or start something new.`;
        }
    } catch (_) {}
    return 'No workspace is open. Pick one from the sidebar, or start a new one.';
}

// On login, greet instead of auto-opening a room
const _origLoadRoomsHome = loadRooms;
loadRooms = async function() {
    await _origLoadRoomsHome();
    // if nothing was remembered, greet
    const last = recallRoom();
    const hasLast = last && roomList.find(r => r.id === last);
    if (!hasLast && !currentRoomId) {
        showHomeState();
    }
};

// Rebind the nav to route home through showHomeState
(function rebindNavHome() {
    const links = document.querySelectorAll('.bottom-nav .nav-link');
    links.forEach(link => {
        // clone to strip old listeners
        const clone = link.cloneNode(true);
        link.parentNode.replaceChild(clone, link);
    });
    document.querySelectorAll('.bottom-nav .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            const action = link.dataset.action;
            if (action === 'home') {
                showHomeState();
            } else if (action === 'research') {
                hideAllPanels(); openResearch();
            } else if (action === 'workspace') {
                hideAllPanels(); openDocuments();
            } else if (action === 'messages') {
                hideAllPanels(); openDMPanel();
            } else if (action === 'train') {
                hideAllPanels(); openTrainingModal();
            }
        });
    });
})();


// ============================================================================
// ROOM WEBSOCKET — real-time fan-out
// ============================================================================

let _roomSocket = null;
let _roomSocketRoom = null;

function closeRoomSocket() {
    // # ROOM-WS
    if (_roomSocket) {
        try { _roomSocket.close(); } catch (_) {}
        _roomSocket = null;
        _roomSocketRoom = null;
    }
}

function openRoomSocket(roomId) {
    if (!roomId || !authToken) return;
    if (_roomSocketRoom === roomId && _roomSocket && _roomSocket.readyState === 1) return;
    closeRoomSocket();

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/rooms/${roomId}/ws?token=${encodeURIComponent(authToken)}`;
    try {
        const ws = new WebSocket(url);
        _roomSocket = ws;
        _roomSocketRoom = roomId;

        ws.addEventListener('message', (ev) => {
            let payload;
            try { payload = JSON.parse(ev.data); } catch (_) { return; }
            if (payload.room_id !== currentRoomId) return;

            if (payload.type === 'user_message') {
                const m = payload.message;
                if (!m) return;
                // skip our own message — already rendered optimistically
                const mine = currentUser && m.user_id === currentUser.id;
                if (mine) return;
                appendMessage('user', `${m.full_name || m.phone || ''}: ${m.content}`);
            } else if (payload.type === 'ai_message') {
                const frames = payload.frames || [];
                if (frames.length) {
                    appendFrameMessage('ai', frames, []);
                } else if (payload.message && payload.message.content) {
                    appendMessage('ai', payload.message.content);
                }
            }
        });

        ws.addEventListener('close', () => {
            if (_roomSocketRoom === roomId) {
                setTimeout(() => {
                    if (currentRoomId === roomId) openRoomSocket(roomId);
                }, 2000);
            }
        });

        ws.addEventListener('error', () => {});
    } catch (e) {
        console.warn('[ws] connect failed:', e.message);
    }
}

// hook into openRoom to (re)connect the socket
const _origOpenRoomWS = openRoom;
openRoom = async function(id) {
    await _origOpenRoomWS(id);
    openRoomSocket(id);
};

// close socket on logout / home
const _origShowHomeStateWS = showHomeState;
showHomeState = function() {
    closeRoomSocket();
    _origShowHomeStateWS();
};

const _origLogoutWS = logout;
logout = function() {
    closeRoomSocket();
    _origLogoutWS();
};


// ============================================================================
// ATTACHMENTS — image upload
// ============================================================================

function _apiBase() {
    return (typeof API_BASE !== 'undefined' && API_BASE) ? API_BASE : '';
}

async function uploadImage(file) {
    // # ATTACH-UPLOAD
    const fd = new FormData();
    fd.append('file', file, file.name || 'photo.jpg');
    const res = await fetch(_apiBase() + '/uploads/image', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: fd,
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
    return JSON.parse(text);
}

// SAFARI-VOICE: pick the format the browser actually supports.
// Safari (macOS/iOS) -> audio/mp4
// Chrome / Firefox    -> audio/webm;codecs=opus
// Older Firefox        -> audio/ogg;codecs=opus
const VOICE_MIME_CANDIDATES = [
    { mime: 'audio/webm;codecs=opus', ext: 'webm' },
    { mime: 'audio/webm',             ext: 'webm' },
    { mime: 'audio/mp4',              ext: 'm4a'  },
    { mime: 'audio/mp4;codecs=mp4a.40.2', ext: 'm4a' },
    { mime: 'audio/ogg;codecs=opus',  ext: 'ogg'  },
    { mime: 'audio/ogg',              ext: 'ogg'  },
    { mime: 'audio/wav',              ext: 'wav'  },
];

function pickVoiceFormat() {
    try {
        if (typeof MediaRecorder === 'undefined') return null;
        if (typeof MediaRecorder.isTypeSupported !== 'function') {
            // very old Safari — just try mp4
            return { mime: 'audio/mp4', ext: 'm4a' };
        }
        for (const c of VOICE_MIME_CANDIDATES) {
            try {
                if (MediaRecorder.isTypeSupported(c.mime)) return c;
            } catch (_) {}
        }
        // last resort — let the browser decide
        return { mime: '', ext: 'webm' };
    } catch (_) {
        return null;
    }
}

async function uploadVoice(blob, ext = 'webm') {
    const fd = new FormData();
    fd.append('file', blob, `voice.${ext}`);
    const res = await fetch(_apiBase() + '/uploads/voice', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: fd,
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 200)}`);
    return JSON.parse(text);
}

async function postMessageWithAttachment({ text = '', attachmentId = null }) {
    if (!currentRoomId) { alert('Open a room first.'); return; }
    const body = { content: text };
    if (attachmentId) body.attachment_id = attachmentId;

    // optimistic user bubble
    appendAttachmentBubble('user', {
        full_name: (currentUser && currentUser.full_name) || '',
        content: text,
        attachment: attachmentId ? { url: `/uploads/${attachmentId}` } : null,
    });

    try {
        await api(`/rooms/${currentRoomId}/messages`, 'POST', body);
    } catch (e) {
        appendMessage('ai', `Send failed: ${e.message}`);
    }
}

function appendAttachmentBubble(role, payload) {
    const chatBox = document.getElementById('chatBox');
    if (!chatBox) return;
    const div = document.createElement('div');
    div.className = `message ${role}`;

    if (role !== 'ai' && payload.full_name) {
        const who = document.createElement('div');
        who.className = 'msg-author';
        who.textContent = payload.full_name;
        div.appendChild(who);
    }

    if (payload.content && payload.content !== '[attachment]') {
        const p = document.createElement('div');
        p.className = 'frame-prose';
        p.textContent = payload.content;
        div.appendChild(p);
    }

    if (payload.attachment) {
        div.appendChild(renderAttachment(payload.attachment));
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function renderAttachment(att) {
    const url = _apiBase() + (att.url || '');
    const lower = (url.split('?')[0] || '').toLowerCase();
    const isImg = lower.match(/\.(png|jpg|jpeg|gif|webp)$/);
    const isAudio = lower.match(/\.(webm|ogg|mp3|m4a|wav)$/);

    const wrap = document.createElement('div');
    wrap.className = 'attachment';

    if (isImg || (!isAudio && (att.kind || '') === 'image')) {
        const img = document.createElement('img');
        img.src = url;
        img.className = 'attachment-image';
        img.loading = 'lazy';
        img.addEventListener('click', () => window.open(url, '_blank'));
        wrap.appendChild(img);
    } else if (isAudio || (att.kind || '') === 'voice_note') {
        const audio = document.createElement('audio');
        audio.src = url;
        audio.controls = true;
        audio.className = 'attachment-audio';
        wrap.appendChild(audio);
    } else {
        const a = document.createElement('a');
        a.href = url;
        a.target = '_blank';
        a.textContent = att.name || 'attachment';
        wrap.appendChild(a);
    }
    return wrap;
}

// wire attach button
(function wireAttach() {
    const btn = document.getElementById('btnAttachImage');
    const input = document.getElementById('imageInput');
    if (btn && input) {
        btn.addEventListener('click', () => input.click());
        input.addEventListener('change', async () => {
            const f = input.files && input.files[0];
            input.value = '';
            if (!f) return;
            btn.disabled = true;
            const original = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            try {
                const up = await uploadImage(f);
                await postMessageWithAttachment({ text: '', attachmentId: up.id });
            } catch (e) {
                alert(`Image upload failed: ${e.message}`);
            } finally {
                btn.disabled = false;
                btn.innerHTML = original;
            }
        });
    }
})();

// ============================================================================
// VOICE NOTES
// ============================================================================

let _mediaRecorder = null;
let _voiceMime = '';
let _voiceExt = 'webm';
let _mediaChunks = [];
let _mediaStream = null;
let _voiceStart = 0;
let _voiceTimerHandle = null;

function _voiceTimerUpdate() {
    const el = document.getElementById('voiceTimer');
    if (!el) return;
    const s = Math.floor((Date.now() - _voiceStart) / 1000);
    el.textContent = `${Math.floor(s/60)}:${String(s % 60).padStart(2,'0')}`;
}

async function startVoiceRecording() {
    if (!currentRoomId) { alert('Open a room first.'); return; }
    if (_mediaRecorder) return;

    const fmt = pickVoiceFormat();
    if (fmt === null) {
        alert('This browser does not support audio recording.');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        _mediaStream = stream;
        _mediaChunks = [];
        _voiceMime = fmt.mime;
        _voiceExt = fmt.ext;

        let mr;
        try {
            mr = fmt.mime
                ? new MediaRecorder(stream, { mimeType: fmt.mime })
                : new MediaRecorder(stream);
        } catch (e) {
            // fallback: let the browser choose
            mr = new MediaRecorder(stream);
            _voiceMime = mr.mimeType || '';
            _voiceExt = _voiceMime.includes('mp4') ? 'm4a'
                      : _voiceMime.includes('ogg') ? 'ogg'
                      : 'webm';
        }

        mr.addEventListener('dataavailable', (e) => {
            if (e.data && e.data.size > 0) _mediaChunks.push(e.data);
        });
        _mediaRecorder = mr;
        mr.start();

        _voiceStart = Date.now();
        document.getElementById('voiceOverlay').style.display = 'flex';
        _voiceTimerHandle = setInterval(_voiceTimerUpdate, 250);
        _voiceTimerUpdate();
    } catch (e) {
        alert(`Microphone access denied: ${e.message}`);
    }
}

function _stopVoiceTracks() {
    try { _mediaStream && _mediaStream.getTracks().forEach(t => t.stop()); } catch (_) {}
    _mediaStream = null;
    if (_voiceTimerHandle) { clearInterval(_voiceTimerHandle); _voiceTimerHandle = null; }
}

async function stopVoiceRecording(send = true) {
    if (!_mediaRecorder) return;
    const mr = _mediaRecorder;
    _mediaRecorder = null;
    const chunks = _mediaChunks;
    _mediaChunks = [];

    await new Promise((resolve) => {
        mr.addEventListener('stop', resolve, { once: true });
        try { mr.stop(); } catch (_) { resolve(); }
    });
    _stopVoiceTracks();
    document.getElementById('voiceOverlay').style.display = 'none';

    if (!send) return;
    const mime = _voiceMime || 'audio/webm';
    const ext = _voiceExt || 'webm';
    const blob = new Blob(chunks, { type: mime });
    if (blob.size < 512) return;

    const btn = document.getElementById('btnMic');
    const orig = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'; }
    try {
        const up = await uploadVoice(blob, ext);
        await postMessageWithAttachment({ text: '', attachmentId: up.id });
    } catch (e) {
        alert(`Voice upload failed: ${e.message}`);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = orig; }
    }
}

(function wireVoice() {
    const btn = document.getElementById('btnMic');
    if (btn) btn.addEventListener('click', startVoiceRecording);
    const stopBtn = document.getElementById('btnVoiceStop');
    if (stopBtn) stopBtn.addEventListener('click', () => stopVoiceRecording(true));
    const cancelBtn = document.getElementById('btnVoiceCancel');
    if (cancelBtn) cancelBtn.addEventListener('click', () => stopVoiceRecording(false));
})();

// Extend appendMessage so historical messages with attachments render too
const _origAppendMessageForAttach = appendMessage;
appendMessage = function(role, text, followUps = [], attachment = null) {
    if (attachment) {
        appendAttachmentBubble(role, { content: text, attachment });
        return;
    }
    return _origAppendMessageForAttach(role, text, followUps);
};


// ============================================================================
// NOTIFICATIONS — in-app toasts + browser Notification API
// ============================================================================

const _notifySeen = new Set();

async function requestNotificationPermission() {
    // # NOTIFY
    if (!('Notification' in window)) return 'unsupported';
    if (Notification.permission === 'granted') return 'granted';
    if (Notification.permission === 'denied') return 'denied';
    try {
        const p = await Notification.requestPermission();
        return p;
    } catch (_) { return 'denied'; }
}

function toast(title, body, opts = {}) {
    // in-app toast (always shown)
    let tray = document.getElementById('toastTray');
    if (!tray) {
        tray = document.createElement('div');
        tray.id = 'toastTray';
        tray.className = 'toast-tray';
        document.body.appendChild(tray);
    }
    const el = document.createElement('div');
    el.className = 'toast';
    el.innerHTML = `
        <div class="toast-icon"><i class="fa-solid ${opts.icon || 'fa-bell'}"></i></div>
        <div class="toast-body">
            <div class="toast-title">${escapeHtml(title || '')}</div>
            ${body ? `<div class="toast-text">${escapeHtml(body)}</div>` : ''}
        </div>
        <button class="toast-close"><i class="fa-solid fa-xmark"></i></button>
    `;
    tray.appendChild(el);
    const remove = () => { try { el.remove(); } catch (_) {} };
    el.querySelector('.toast-close').addEventListener('click', remove);
    if (opts.onClick) {
        el.addEventListener('click', (ev) => {
            if (ev.target.closest('.toast-close')) return;
            try { opts.onClick(); } catch (_) {}
            remove();
        });
    }
    setTimeout(remove, opts.ttl || 6000);
}

function browserNotify(title, body, opts = {}) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    if (document.visibilityState === 'visible') return;  // only when hidden
    try {
        const n = new Notification(title, {
            body,
            icon: '/app/icons/icon-192.png',
            tag: opts.tag || ('acd-' + Math.random().toString(36).slice(2, 8)),
            silent: false,
        });
        if (opts.onClick) {
            n.addEventListener('click', () => {
                try { window.focus(); } catch (_) {}
                try { opts.onClick(); } catch (_) {}
            });
        }
    } catch (_) {}
}

function notify(title, body, opts = {}) {
    const key = opts.dedupeKey;
    if (key) {
        if (_notifySeen.has(key)) return;
        _notifySeen.add(key);
        if (_notifySeen.size > 200) {
            const iter = _notifySeen.values();
            for (let i = 0; i < 50; i++) { _notifySeen.delete(iter.next().value); }
        }
    }
    toast(title, body, opts);
    browserNotify(title, body, opts);
}

// Wire into the room WebSocket payload — extended handler
const _origOpenRoomSocketForNotify = openRoomSocket;
openRoomSocket = function(roomId) {
    _origOpenRoomSocketForNotify(roomId);

    // attach a second listener that adds notification logic
    if (_roomSocket) {
        _roomSocket.addEventListener('message', (ev) => {
            let payload;
            try { payload = JSON.parse(ev.data); } catch (_) { return; }
            if (payload.room_id !== currentRoomId) {
                // different room — notify
                if (payload.type === 'user_message' && payload.message) {
                    const m = payload.message;
                    if (currentUser && m.user_id === currentUser.id) return;
                    notify(
                        m.full_name || m.phone || 'New message',
                        (m.content || '').slice(0, 90),
                        {
                            icon: 'fa-comment',
                            dedupeKey: 'msg-' + m.id,
                            onClick: () => {
                                const rid = payload.room_id;
                                if (rid) { currentRoomId = rid; openRoom(rid); }
                            },
                        },
                    );
                } else if (payload.type === 'ai_message') {
                    notify(
                        'Accodite',
                        'AI responded in a room you are in',
                        { icon: 'fa-brain', dedupeKey: 'ai-' + (payload.message?.id || Date.now()) },
                    );
                }
                return;
            }
        });
    }
};

// Ask for permission after login (non-blocking)
const _origHandleAuthSuccessForNotify = handleAuthSuccess;
handleAuthSuccess = async function(data) {
    await _origHandleAuthSuccessForNotify(data);
    setTimeout(() => { requestNotificationPermission(); }, 1500);
};

// Also verify permission isn't stale on every app boot
setTimeout(() => { requestNotificationPermission(); }, 2500);


// ============================================================================
// THREAD RENDERING + AUTHOR AVATARS
// ============================================================================

function _avatarHtml(user, size = 28) {
    const url = user && user.avatar_url
        ? (_apiBase() + user.avatar_url)
        : null;
    const name = escapeHtml((user && (user.full_name || user.phone)) || '?');
    const initial = name.trim().charAt(0).toUpperCase() || '?';
    if (url) {
        return `<span class="msg-avatar" style="width:${size}px;height:${size}px;">
                  <img src="${url}" alt="${name}" loading="lazy" />
                </span>`;
    }
    return `<span class="msg-avatar msg-avatar-fallback" style="width:${size}px;height:${size}px;">${initial}</span>`;
}

function renderMessageItem(m, { mine = false } = {}) {
    // # THREAD-RENDER
    const chatBox = document.getElementById('chatBox');
    if (!chatBox) return;
    const div = document.createElement('div');
    div.className = `message ${m.role === 'ai' ? 'ai' : (mine ? 'user' : 'other')}`;
    div.dataset.messageId = m.id;

    // Thread reference
    if (m.replies_to) {
        const ref = document.createElement('div');
        ref.className = 'thread-ref';
        ref.innerHTML = `<i class="fa-solid fa-arrow-turn-up"></i>
            <span>replying to <strong>${escapeHtml(m.replies_to_author || 'message')}</strong>
            <span class="thread-preview">${escapeHtml(m.replies_to_preview || '')}</span></span>`;
        div.appendChild(ref);
    }

    // Author row (name + avatar)
    if (m.role !== 'ai') {
        const head = document.createElement('div');
        head.className = 'msg-head';
        head.innerHTML = `
            ${_avatarHtml({ avatar_url: m.avatar_url, full_name: m.full_name, phone: m.phone })}
            <span class="msg-author">${escapeHtml(m.full_name || m.phone || '')}</span>
        `;
        div.appendChild(head);
    } else {
        const head = document.createElement('div');
        head.className = 'msg-head';
        head.innerHTML = `
            <span class="msg-avatar ai-avatar" style="width:28px;height:28px;"><i class="fa-solid fa-brain"></i></span>
            <span class="msg-author ai-author">Accodite</span>
        `;
        div.appendChild(head);
    }

    // Content
    if (m.content && m.content !== '[attachment]') {
        const p = document.createElement('div');
        p.className = 'frame-prose';
        p.textContent = m.content;
        div.appendChild(p);
    }

    // Attachment
    if (m.attachment) {
        div.appendChild(renderAttachment(m.attachment));
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Hook openRoom to use the new renderer
const _origOpenRoomThread = openRoom;
openRoom = async function(id) {
    // do the fetch + clear ourselves so we can use the new renderer
    currentRoomId = id;
    renderRoomBar();
    updateActiveTitle();
    updateInviteButtonVisibility();
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = '';
    try {
        const msgs = await api(`/rooms/${id}/messages`);
        if (!msgs.length) {
            appendMessage('ai', 'Workspace ready. Say something to begin.');
        } else {
            const meId = currentUser && currentUser.id;
            msgs.forEach(m => renderMessageItem(m, { mine: meId && m.user_id === meId }));
        }
    } catch (e) {
        appendMessage('ai', `Could not load room: ${e.message}`);
    }
    openRoomSocket(id);
    updateInputVisibility();
};

// Hook WS handler to use the new renderer for cross-member messages
const _origOpenRoomSocketThread = openRoomSocket;
openRoomSocket = function(roomId) {
    _origOpenRoomSocketThread(roomId);
    if (!_roomSocket) return;
    _roomSocket.addEventListener('message', (ev) => {
        let payload;
        try { payload = JSON.parse(ev.data); } catch (_) { return; }
        if (payload.room_id !== currentRoomId) return;
        if (payload.type === 'user_message' && payload.message) {
            const m = payload.message;
            const mine = currentUser && m.user_id === currentUser.id;
            if (mine) return;   // already rendered optimistically
            renderMessageItem({
                id: m.id,
                user_id: m.user_id,
                full_name: m.full_name,
                avatar_url: m.avatar_url || null,
                role: 'user',
                content: m.content,
                attachment: m.attachment,
                replies_to: null,
                created_at: m.created_at,
            }, { mine: false });
        }
    });
};


// ============================================================================
// PROFILE AVATAR (upload + display)
// ============================================================================

async function uploadAvatar(file) {
    // # AVATAR-UPLOAD
    const fd = new FormData();
    fd.append('file', file, file.name || 'avatar.png');
    const res = await fetch(_apiBase() + '/uploads/profile/avatar', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: fd,
    });
    const txt = await res.text();
    if (!res.ok) throw new Error(`${res.status} ${txt.slice(0, 200)}`);
    return JSON.parse(txt);
}

function renderProfileAvatar(p) {
    const url = p && p.avatar_url ? (_apiBase() + p.avatar_url) : null;
    if (url) {
        return `<div class="profile-avatar profile-avatar-img">
                  <img src="${url}" alt="" onerror="this.style.display='none'" />
                </div>`;
    }
    return `<div class="profile-avatar"><i class="fa-solid fa-user-circle"></i></div>`;
}

// Patch openProfile to render the avatar + upload button
const _origOpenProfileAvatar = openProfile;
openProfile = async function() {
    const modal = document.getElementById('profileModal');
    const body = document.getElementById('profileBody');
    if (!modal || !body) return;
    modal.style.display = 'flex';
    body.innerHTML = '<p style="opacity:.6;">Loading…</p>';
    try {
        const p = await api('/auth/profile');
        const orgs = (p.orgs || []).map(o => {
            const status = o.brain_status || (o.ai_uid && !String(o.ai_uid).startsWith('org-pending-') ? 'active' : 'pending');
            const brainLine = status === 'active'
                ? `<div class="profile-org-meta" style="opacity:.62; word-break:break-all;">
                       <span style="font-size:0.66rem; text-transform:uppercase; letter-spacing:0.06em; opacity:.6;">org brain</span>
                       <div style="font-family:var(--font-mono); font-size:0.78rem; margin-top:0.15rem;">${escapeHtml(o.ai_uid || '—')}</div>
                   </div>`
                : `<div class="profile-org-meta" style="opacity:.55; font-style:italic;">org brain: not yet generated — create it in the dashboard</div>`;
            return `
                <div class="profile-org">
                    <div class="profile-org-name">${escapeHtml(o.org_name || '')}</div>
                    <div class="profile-org-meta">${escapeHtml(o.role || '')}${o.department ? ' · ' + escapeHtml(o.department) : ''}</div>
                    <div class="profile-org-meta" style="opacity:.55;">${o.credential_active ? 'member active' : 'membership pending'}</div>
                    ${brainLine}
                </div>`;
        }).join('') || '<p style="opacity:.5; font-size:0.8rem;">No organization memberships</p>';

        body.innerHTML = `
            <div class="profile-header">
                ${renderProfileAvatar(p)}
                <div>
                    <div class="profile-name">${escapeHtml(p.full_name || '')}</div>
                    <div class="profile-phone">${escapeHtml(p.phone || '')}</div>
                    <button id="btnChangeAvatar" class="primary-btn secondary-btn" style="font-size:0.72rem; padding:0.35rem 0.75rem; margin-top:0.5rem;">
                        <i class="fa-solid fa-camera"></i> Change avatar
                    </button>
                    <input type="file" id="avatarInput" accept="image/*" style="display:none;" />
                </div>
            </div>
            <div class="profile-grid">
                <div class="profile-kv"><span class="k">Country</span><span class="v">${escapeHtml(p.country || '')}</span></div>
                <div class="profile-kv"><span class="k">Language</span><span class="v">${escapeHtml(p.language || '')}</span></div>
                <div class="profile-kv"><span class="k">Temperament</span><span class="v">${escapeHtml(p.temperament || '')}</span></div>
                <div class="profile-kv"><span class="k">Account type</span><span class="v">${escapeHtml(p.account_type || 'regular')}</span></div>
                <div class="profile-kv"><span class="k">Start row</span><span class="v">${escapeHtml(String(p.start_row ?? '—'))}</span></div>
                <div class="profile-kv"><span class="k">Start col</span><span class="v">${escapeHtml(String(p.start_col ?? '—'))}</span></div>
                <div class="profile-kv"><span class="k">Brain UID</span><span class="v">${escapeHtml(p.personal_ai_uid || '—')}</span></div>
                <div class="profile-kv"><span class="k">Joined</span><span class="v">${p.created_at ? new Date(p.created_at).toLocaleString() : '—'}</span></div>
            </div>
            <h4 style="margin-top:1rem;"><i class="fa-solid fa-sitemap"></i> Organizations</h4>
            <div style="margin-top:0.5rem;">${orgs}</div>
        `;

        // wire the avatar upload
        const btn = document.getElementById('btnChangeAvatar');
        const inp = document.getElementById('avatarInput');
        if (btn && inp) {
            btn.addEventListener('click', () => inp.click());
            inp.addEventListener('change', async () => {
                const f = inp.files && inp.files[0];
                inp.value = '';
                if (!f) return;
                btn.disabled = true;
                const orig = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading…';
                try {
                    const r = await uploadAvatar(f);
                    currentUser = Object.assign({}, currentUser || {}, { avatar_url: r.avatar_url });
                    localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
                    openProfile();
                } catch (e) {
                    alert(`Avatar upload failed: ${e.message}`);
                    btn.disabled = false;
                    btn.innerHTML = orig;
                }
            });
        }
    } catch (e) {
        body.innerHTML = `<p style="color:#f3a9c1;">${escapeHtml(e.message)}</p>`;
    }
};


// ============================================================================
// SEARCH PANEL
// ============================================================================

let _searchTimer = null;

async function runSearch() {
    // # SEARCH-PANEL
    const q = (document.getElementById('searchInput').value || '').trim();
    const scope = document.getElementById('searchScope').value || 'all';
    const box = document.getElementById('searchResults');
    if (q.length < 2) {
        box.innerHTML = '<p style="opacity:.55; padding:0.75rem;">Type at least 2 characters.</p>';
        return;
    }
    box.innerHTML = '<p style="opacity:.6; padding:0.75rem;">Searching…</p>';
    try {
        const data = await api(`/search?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}`);
        const results = data.results || [];
        if (!results.length) {
            box.innerHTML = '<p style="opacity:.5; padding:0.75rem;">No results.</p>';
            return;
        }
        box.innerHTML = results.map(r => `
            <div class="search-item" data-source="${escapeHtml(r.source)}"${r.room_id ? ` data-room="${escapeHtml(r.room_id)}"` : ''}>
                <div class="search-item-head">
                    <span class="search-badge search-badge-${escapeHtml(r.source)}">${escapeHtml(r.source)}</span>
                    <span class="search-title">${escapeHtml(r.title || '')}</span>
                </div>
                <div class="search-snippet">${escapeHtml(r.snippet || '')}</div>
            </div>
        `).join('');
        box.querySelectorAll('.search-item').forEach(el => {
            el.addEventListener('click', () => {
                if (el.dataset.room) {
                    document.getElementById('searchPanel').style.display = 'none';
                    openRoom(el.dataset.room);
                }
            });
        });
    } catch (e) {
        box.innerHTML = `<p style="color:#f3a9c1; padding:0.75rem;">${escapeHtml(e.message)}</p>`;
    }
}

function openSearchPanel() {
    hideAllPanels();
    const panel = document.getElementById('searchPanel');
    if (!panel) return;
    panel.style.display = 'block';
    setTimeout(() => document.getElementById('searchInput')?.focus(), 50);
}

(function wireSearch() {
    const inp = document.getElementById('searchInput');
    if (inp) {
        inp.addEventListener('input', () => {
            clearTimeout(_searchTimer);
            _searchTimer = setTimeout(runSearch, 300);
        });
        inp.addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });
    }
    const scopeSel = document.getElementById('searchScope');
    if (scopeSel) scopeSel.addEventListener('change', runSearch);
    const close = document.getElementById('btnCloseSearch');
    if (close) close.addEventListener('click', () => {
        document.getElementById('searchPanel').style.display = 'none';
    });
})();

// Rebind the nav "research" icon to open the search panel
(function rebindResearchToSearch() {
    const link = document.querySelector('.bottom-nav .nav-link[data-action="research"]');
    if (!link) return;
    const clone = link.cloneNode(true);
    link.parentNode.replaceChild(clone, link);
    clone.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        clone.classList.add('active');
        openSearchPanel();
    });
    // swap icon to a magnifier if the icon was something else
    const i = clone.querySelector('i');
    if (i) i.className = 'fa-solid fa-magnifying-glass';
})();


// ============================================================================
// SIDEBAR-COLLAPSE — hide the drawer the moment the user commits to anything
// ============================================================================

// 1) Any nav-link click closes the sidebar first (capture phase)
document.addEventListener('click', (e) => {
    const link = e.target.closest('.bottom-nav .nav-link');
    if (link) {
        try { closeSidebar(); } catch (_) {}
    }
}, true);

// 2) Opening the new-room modal closes the sidebar
const _origOpenNewRoomModalSidebar = openNewRoomModal;
openNewRoomModal = function() {
    try { closeSidebar(); } catch (_) {}
    return _origOpenNewRoomModalSidebar();
};

// 3) Opening a room closes the sidebar
const _origOpenRoomSidebar = openRoom;
openRoom = async function(id) {
    try { closeSidebar(); } catch (_) {}
    return _origOpenRoomSidebar(id);
};

// 4) Escape also closes it
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        try { closeSidebar(); } catch (_) {}
    }
});


// ============================================================================
// REPLY STATE + DEDUP + STRICT AI ECHO SKIP
// ============================================================================

let _replyTo = null;                 // { id, author, preview }
const _renderedIds = new Set();      // message ids already shown

function setReplyTo(ref) {
    // ref = { id, author, preview } or null
    _replyTo = ref;
    const bar = document.getElementById('replyBar');
    if (!bar) {
        const el = document.createElement('div');
        el.id = 'replyBar';
        el.className = 'reply-bar';
        el.style.display = 'none';
        el.innerHTML = `
            <div class="reply-bar-inner">
                <i class="fa-solid fa-reply"></i>
                <div class="reply-bar-text">
                    <div class="reply-bar-who"></div>
                    <div class="reply-bar-preview"></div>
                </div>
                <button class="reply-bar-cancel" title="Cancel reply"><i class="fa-solid fa-xmark"></i></button>
            </div>`;
        const footer = document.getElementById('inputArea');
        if (footer && footer.parentNode) {
            footer.parentNode.insertBefore(el, footer);
        } else {
            document.body.appendChild(el);
        }
        el.querySelector('.reply-bar-cancel').addEventListener('click', () => setReplyTo(null));
    }
    if (_replyTo) {
        bar.querySelector('.reply-bar-who').textContent = 'Replying to ' + (_replyTo.author || 'message');
        bar.querySelector('.reply-bar-preview').textContent = (_replyTo.preview || '').slice(0, 80);
        bar.style.display = '';
    } else {
        bar.style.display = 'none';
    }
}

// Attach a reply chip to every rendered message
function _attachReplyAffordance(el, m) {
    if (!el || !m || !m.id) return;
    el.dataset.messageId = m.id;
    el.style.cursor = 'pointer';
    el.addEventListener('dblclick', (ev) => {
        ev.preventDefault();
        setReplyTo({
            id: m.id,
            author: m.full_name || m.phone || (m.role === 'ai' ? 'Accodite' : 'user'),
            preview: (m.content || '').slice(0, 100),
        });
    });
    // mobile: tap the small reply icon that appears on hover/focus
    if (!el.querySelector('.msg-reply-btn')) {
        const btn = document.createElement('button');
        btn.className = 'msg-reply-btn';
        btn.title = 'Reply';
        btn.innerHTML = '<i class="fa-solid fa-reply"></i>';
        btn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            setReplyTo({
                id: m.id,
                author: m.full_name || m.phone || (m.role === 'ai' ? 'Accodite' : 'user'),
                preview: (m.content || '').slice(0, 100),
            });
        });
        el.appendChild(btn);
    }
}

// Wrap renderMessageItem to dedup + attach reply chip
const _origRenderMessageItemReply = renderMessageItem;
renderMessageItem = function(m, opts = {}) {
    if (m && m.id) {
        if (_renderedIds.has(m.id)) return;
        _renderedIds.add(m.id);
    }
    _origRenderMessageItemReply(m, opts);
    // attach reply affordance to the last message bubble
    const chatBox = document.getElementById('chatBox');
    const last = chatBox && chatBox.lastElementChild;
    if (last && last.classList.contains('message')) {
        _attachReplyAffordance(last, m);
    }
};

// Wrap appendMessage/appendFrameMessage similarly so AI responses also get reply chips
const _origAppendMessageReply = appendMessage;
appendMessage = function(role, text, followUps = [], attachment = null) {
    return _origAppendMessageReply(role, text, followUps, attachment);
};

// Update sendMessage to include ref_message_id + clear reply bar
const _origSendMessageReply = sendMessage;
sendMessage = async function(text, isFirst = false) {
    const body = { content: text };
    if (_replyTo && _replyTo.id) body.ref_message_id = _replyTo.id;
    if (!currentRoomId) { return _origSendMessageReply(text, isFirst); }
    if (!text.trim() && !_replyTo) return;

    // optimistic user bubble
    const optimistic = {
        id: 'local-' + Date.now(),
        role: 'user',
        content: text,
        full_name: (currentUser && currentUser.full_name) || '',
        avatar_url: (currentUser && currentUser.avatar_url) || null,
        replies_to: _replyTo ? _replyTo.id : null,
        replies_to_author: _replyTo ? _replyTo.author : null,
        replies_to_preview: _replyTo ? _replyTo.preview : null,
    };
    _renderedIds.add(optimistic.id);
    renderMessageItem(optimistic, { mine: true });

    // clear reply state
    setReplyTo(null);

    try {
        const data = await api(`/rooms/${currentRoomId}/messages`, 'POST', body);
        // bind the real id to the optimistic bubble so WS duplicates are skipped
        if (data && data.id) {
            _renderedIds.add(data.id);
            const el = document.querySelector(`.message[data-message-id="${optimistic.id}"]`);
            if (el) el.dataset.messageId = data.id;
        }
        // AI-DEDUP-V2: mark ai_msg_id rendered so WS echo is skipped
        if (data && data.ai_msg_id) _renderedIds.add(data.ai_msg_id);
        if (data && data.frames && data.frames.length > 0) {
            appendFrameMessage('ai', data.frames, []);
        }
    } catch (e) {
        appendMessage('ai', `Send failed: ${e.message}`);
    }
};

// WS handler: skip AI message on invoker + dedup
const _origOpenRoomSocketReply = openRoomSocket;
openRoomSocket = function(roomId) {
    _origOpenRoomSocketReply(roomId);
    if (!_roomSocket) return;
    _roomSocket.addEventListener('message', (ev) => {
        let payload;
        try { payload = JSON.parse(ev.data); } catch (_) { return; }
        if (payload.room_id !== currentRoomId) return;

        if (payload.type === 'ai_message') {
            // STRICT-GATE: skip the echo for the member who triggered it
            if (payload.invoked_by && currentUser && payload.invoked_by === currentUser.id) {
                return;
            }
            const id = payload.message && payload.message.id;
            if (id && _renderedIds.has(id)) return;
            if (id) _renderedIds.add(id);
            const frames = payload.frames || [];
            if (frames.length) {
                appendFrameMessage('ai', frames, []);
            } else if (payload.message && payload.message.content) {
                appendMessage('ai', payload.message.content);
            }
        }
    });
};

// reset dedup on room switch
const _origOpenRoomReset = openRoom;
openRoom = async function(id) {
    _renderedIds.clear();
    setReplyTo(null);
    return _origOpenRoomReset(id);
};


// ============================================================================
// AI-INDENT — visual swipe-reply for threaded AI responses
// ============================================================================

// Extend renderMessageItem so an AI message with replies_to gets a class
// that indents it under the referenced message.
const _origRenderMessageItemIndent = renderMessageItem;
renderMessageItem = function(m, opts = {}) {
    // call the base renderer
    _origRenderMessageItemIndent(m, opts);
    // find the bubble just rendered
    const chatBox = document.getElementById('chatBox');
    const el = chatBox && chatBox.lastElementChild;
    if (!el || !el.classList.contains('message')) return;
    if (m && m.replies_to && m.role === 'ai') {
        el.classList.add('threaded-reply');
        el.dataset.repliesTo = m.replies_to;
        // make sure the thread-ref shows the invoker's name when we have it
        const ref = el.querySelector('.thread-ref');
        if (ref) {
            const nameSpan = ref.querySelector('strong');
            if (nameSpan && m.replies_to_author) {
                nameSpan.textContent = m.replies_to_author;
            }
        }
    }
};

// WS handler: propagate replies_to_author / preview from the payload
const _origOpenRoomSocketIndent = openRoomSocket;
openRoomSocket = function(roomId) {
    _origOpenRoomSocketIndent(roomId);
    if (!_roomSocket) return;
    _roomSocket.addEventListener('message', (ev) => {
        let payload;
        try { payload = JSON.parse(ev.data); } catch (_) { return; }
        if (payload.room_id !== currentRoomId) return;
        if (payload.type === 'ai_message' && payload.message) {
            const m = payload.message;
            const id = m.id;
            if (id && _renderedIds.has(id)) return;
            if (id) _renderedIds.add(id);
            const frames = payload.frames || [];
            const wrapped = {
                id,
                role: 'ai',
                content: m.content,
                full_name: 'Accodite',
                replies_to: m.replies_to,
                replies_to_author: m.replies_to_author,
                replies_to_preview: m.replies_to_preview,
            };
            if (frames.length) {
                // use frame rendering path then attach thread info
                appendFrameMessage('ai', frames, []);
                const chatBox = document.getElementById('chatBox');
                const el = chatBox && chatBox.lastElementChild;
                if (el && el.classList.contains('message') && wrapped.replies_to) {
                    el.classList.add('threaded-reply');
                    const ref = document.createElement('div');
                    ref.className = 'thread-ref';
                    ref.innerHTML = `<i class="fa-solid fa-arrow-turn-up"></i>
                        <span>replying to <strong>${escapeHtml(wrapped.replies_to_author || 'message')}</strong>
                        <span class="thread-preview">${escapeHtml((wrapped.replies_to_preview || '').slice(0,80))}</span></span>`;
                    el.insertBefore(ref, el.firstChild);
                }
            } else if (m.content) {
                renderMessageItem(wrapped, { mine: false });
            }
        }
    });
};


// ============================================================================
// HARD-BOOT — runs LAST, unconditionally fixes state
// Earlier patches (bootVisibility at ~line 1809) remove .logged-in and
// nothing puts it back if showScreen already ran. This restores it.
// ============================================================================

(function hardBootStateFix() {
    // # HARD-BOOT
    const hasToken = (typeof authToken !== 'undefined' && authToken);
    const mainEl = document.getElementById('mainScreen');
    const onMain = mainEl && mainEl.classList.contains('active');

    console.log('[hardboot] token:', !!hasToken, 'mainActive:', !!onMain);

    if (!hasToken) return;

    // 1) force body.logged-in when we're on the main screen
    if (onMain) {
        document.body.classList.add('logged-in');
    } else {
        // if not on main yet, put them there
        try { showScreen('mainScreen'); } catch (_) {}
        document.body.classList.add('logged-in');
    }

    // 2) force the nav visible by inline styles (beats every stylesheet)
    document.querySelectorAll('.bottom-nav, .bottom-nav-fixed').forEach(nav => {
        nav.style.setProperty('display', 'flex', 'important');
        nav.style.setProperty('visibility', 'visible', 'important');
        nav.style.setProperty('opacity', '1', 'important');
        nav.style.setProperty('position', 'fixed', 'important');
        nav.style.setProperty('left', '0', 'important');
        nav.style.setProperty('right', '0', 'important');
        nav.style.setProperty('bottom', '0', 'important');
        nav.style.setProperty('height', '64px', 'important');
        nav.style.setProperty('z-index', '60', 'important');
    });

    // 3) if on main and no room is open, show the home greeting
    if (onMain && (typeof currentRoomId === 'undefined' || !currentRoomId)) {
        try {
            if (typeof showHomeState === 'function') showHomeState();
        } catch (e) {
            console.warn('[hardboot] showHomeState failed:', e);
        }
    }

    // 4) reassert after a tick in case something async strips the class
    setTimeout(() => {
        if (authToken) {
            document.body.classList.add('logged-in');
            document.querySelectorAll('.bottom-nav').forEach(nav => {
                nav.style.setProperty('display', 'flex', 'important');
            });
        }
    }, 300);

    console.log('[hardboot] applied. Navs on page:',
        document.querySelectorAll('.bottom-nav').length);
})();
