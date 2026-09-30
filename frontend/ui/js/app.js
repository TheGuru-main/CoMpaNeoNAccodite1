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
        let errorMsg = 'An unexpected server error occurred.';
        try {
            const errData = await res.json();
            errorMsg = errData.detail || errorMsg;
        } catch (_) {
            errorMsg = await res.text();
        }
        throw new Error(errorMsg);
    }
    return res.json();
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

async function signup() {
    const full_name = document.getElementById('signupFullName').value.trim();
    const phone     = document.getElementById('signupPhone').value.trim();
    const password  = document.getElementById('signupPassword').value;
    if (!full_name || !phone || !password) {
        alert('Please fill in name, phone, and password.');
        return;
    }

    try {
        let data;
        if (signupMode === 'solo') {
            const country = document.getElementById('signupCountry').value;
            const temperament = document.getElementById('signupTemperament').value;
            data = await api('/auth/signup', 'POST',
                { full_name, phone, password, country, temperament, language: 'en' });

        } else if (signupMode === 'org-create') {
            const org_name  = document.getElementById('orgName').value.trim();
            const org_slug  = document.getElementById('orgSlug').value.trim();
            const org_email = document.getElementById('orgEmail').value.trim();
            const org_country = document.getElementById('orgCountry').value.trim();
            if (!org_name || !org_slug) {
                alert('Organization name and slug are required.');
                return;
            }
            data = await api('/auth/org/create', 'POST', {
                full_name, phone, password,
                org_name, org_slug,
                org_email: org_email || null,
                org_country: org_country || 'Nigeria',
                language: 'en',
            });
            if (data && data.worker_credential) {
                alert(`Organization created.\n\nWorker credential (share with workers):\n${data.worker_credential}\n\nSave it - you'll need it to onboard staff.`);
            }

        } else if (signupMode === 'org-join') {
            const worker_credential = document.getElementById('workerCred').value.trim();
            const department = document.getElementById('joinDept').value.trim();
            const role = document.getElementById('joinRole').value.trim() || 'member';
            const title = document.getElementById('joinTitle').value.trim();
            if (!worker_credential || !department) {
                alert('Worker credential and department are required.');
                return;
            }
            data = await api('/auth/org/join', 'POST', {
                full_name, phone, password,
                worker_credential, department, role,
                title: title || null,
                language: 'en',
            });
            if (data && data.pending) {
                alert('Signup submitted. An org admin must approve you before you can enter the org space.');
            }
        }

        if (data && data.access_token) {
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('coMpaNeoN_token', authToken);
            localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
            showScreen('mainScreen');
            await loadWorkspaces();
        } else {
            showScreen('authScreen');
        }
    } catch (e) {
        alert(`Registration Fault: ${e.message}`);
    }
}

// Signup mode tabs
function bindSignupModeTabs() {
    document.querySelectorAll('.signup-mode').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.signup-mode').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            signupMode = btn.dataset.mode;

            const solo = document.getElementById('signupCountry');
            const soloTemp = document.getElementById('signupTemperament');
            const oc = document.getElementById('orgCreateFields');
            const oj = document.getElementById('orgJoinFields');

            const showSolo = signupMode === 'solo';
            if (solo) solo.style.display = showSolo ? '' : 'none';
            if (soloTemp) soloTemp.style.display = showSolo ? '' : 'none';
            if (oc) oc.style.display = signupMode === 'org-create' ? 'block' : 'none';
            if (oj) oj.style.display = signupMode === 'org-join' ? 'block' : 'none';

            const btnSignup = document.getElementById('btnSignup');
            if (btnSignup) {
                btnSignup.textContent = showSolo ? 'Create Account'
                    : (signupMode === 'org-create' ? 'Create Organization'
                    : 'Request to Join Org');
            }
        });
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
}

// Bind signup mode tabs
try { bindSignupModeTabs(); } catch (_) {}
