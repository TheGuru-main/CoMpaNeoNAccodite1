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

async function sendMessage(text, isFirst=false) {
    if (!text.trim()) return;
    if (!isFirst) appendMessage('user', text);
    
    try {
        let data;
        const payload = {
            prompt: text,
            temperament: currentUser?.temperament || 'sanguine',
            workspace_name: '',
            conversation_history: ''
        };

        if (currentWorkspaceId) {
            // Hit the workspace-scoped context endpoint as defined in backend/main.py
            data = await api(`/workspace/${currentWorkspaceId}/generate`, 'POST', payload);
        } else {
            // Fallback generation path if a root state collision occurs
            data = await api('/generate', 'POST', payload);
        }
        
        if (data.frames && data.frames.length > 0) {
            appendFrameMessage('ai', data.frames, data.follow_ups || []);
        } else {
            appendMessage('ai', data.generated, data.follow_ups || []);
        }
    } catch (e) {
        appendMessage('ai', `System Matrix Sync Failure: ${e.message}`);
    }
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
