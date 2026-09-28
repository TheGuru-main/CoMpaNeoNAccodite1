const API_BASE = '';  // Stays empty to dynamically evaluate your Render URL paths
let authToken = localStorage.getItem('coMpaNeoN_token') || '';
let currentUser = null;
let currentWorkspaceId = null;
let workspaceList = [];

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
    const phone = document.getElementById('signupPhone').value.trim();
    const password = document.getElementById('signupPassword').value;
    const country = document.getElementById('signupCountry').value;
    const temperament = document.getElementById('signupTemperament').value;
    if (!full_name || !phone || !password) {
        alert('Please fill in all registration fields.');
        return;
    }
    try {
        const data = await api('/auth/signup', 'POST', { full_name, phone, password, country, temperament, language: 'en' });
        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('coMpaNeoN_token', authToken);
        localStorage.setItem('coMpaNeoN_user', JSON.stringify(currentUser));
        showScreen('mainScreen');
        await loadWorkspaces();
    } catch (e) { 
        alert(`Registration Fault: ${e.message}`); 
    }
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
        
        appendMessage('ai', data.generated, data.follow_ups || []);
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

    // 1. Evaluate Wikipedia Extraction Matrix
    if (data.wikipedia && data.wikipedia.extract) {
        fragmentsFound = true;
        container.innerHTML += `
            <div style="margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                <h4 style="color:var(--neon-blue);">📚 Wikipedia Extract</h4>

});

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
            const trainBtn = e.currentTarget;
            trainBtn.style.opacity = '0.4';
            api('/train', 'POST', { epochs: 5 }).then(data => alert(data.message || 'Model optimization cycle completed.')).catch(err => alert(`Training rejected: ${err.message}`)).finally(() => trainBtn.style.opacity = '1');
        }
    });
});

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
