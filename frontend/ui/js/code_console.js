// Accodite multi-context Monaco + bottom Console
// Contexts: user | org | ai – each keeps its own output buffer
// AI can call the same sandbox automatically via context="ai"

let monacoEditor = null;
const consoleBuffers = { user: "", org: "", ai: "" };

function initMonaco() {
    if (monacoEditor) return;
    const el = document.getElementById("monacoContainer");
    if (!el) return;

    require.config({
        paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" }
    });
    require(["vs/editor/editor.main"], function () {
        monacoEditor = monaco.editor.create(el, {
            value: '# Accodite – User console\\nprint("Hello from sandbox")\\n',
            language: "python",
            theme: "vs-dark",
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: "on",
        });
    });
}

function showCodeScreen() {
    // hide other screens
    document.querySelectorAll(".screen").forEach(s => {
        s.classList.remove("active");
        s.style.display = "none";
    });
    const screen = document.getElementById("codeScreen");
    if (screen) {
        screen.style.display = "flex";
        screen.classList.add("active");
    }
    // hide chat box if present
    const chat = document.getElementById("chatBox");
    if (chat) chat.style.display = "none";

    initMonaco();
    updateConsoleLabel();
}

function hideCodeScreen() {
    const screen = document.getElementById("codeScreen");
    if (screen) {
        screen.style.display = "none";
        screen.classList.remove("active");
    }
    // restore main chat view
    const main = document.getElementById("mainScreen");
    if (main) {
        main.style.display = "block";
        main.classList.add("active");
    }
    const chat = document.getElementById("chatBox");
    if (chat) chat.style.display = "";
}

function updateConsoleLabel() {
    const sel = document.getElementById("codeContext");
    if (!sel) return;
    const ctx = sel.value;
    const label = document.getElementById("consoleContextLabel");
    if (label) label.textContent = ctx;
    const out = document.getElementById("codeOutput");
    if (out) out.textContent = consoleBuffers[ctx] || "";
}

async function runCode() {
    if (!monacoEditor) return;
    const source = monacoEditor.getValue();
    const lang = (document.getElementById("codeLang") || {}).value || "python";
    const context = (document.getElementById("codeContext") || {}).value || "user";
    const outputEl = document.getElementById("codeOutput");
    if (!outputEl) return;

    outputEl.textContent = `[${context}] Running...\\n`;

    try {
        const headers = { "Content-Type": "application/json" };
        if (typeof authToken !== "undefined" && authToken) {
            headers["Authorization"] = `Bearer ${authToken}`;
        }

        const res = await fetch("/sandbox/run", {
            method: "POST",
            headers,
            body: JSON.stringify({
                source,
                filename: lang === "python" ? "main.py" : "main.js",
                lang,
                context,
            }),
        });

        const data = await res.json();
        const text = [
            `backend: ${data.backend}  exit: ${data.exit_code}  ${data.duration_s}s`,
            data.timed_out ? "TIMEOUT" : "",
            data.error ? `ERROR: ${data.error}` : "",
            "── stdout ──",
            data.stdout || "(empty)",
            "── stderr ──",
            data.stderr || "(empty)",
        ].filter(Boolean).join("\\n");

        consoleBuffers[context] = (consoleBuffers[context] || "") + text + "\\n\\n";
        outputEl.textContent = consoleBuffers[context];
        outputEl.scrollTop = outputEl.scrollHeight;
    } catch (e) {
        const err = `Request failed: ${e.message}\\n`;
        consoleBuffers[context] = (consoleBuffers[context] || "") + err;
        outputEl.textContent = consoleBuffers[context];
    }
}

function clearConsole() {
    const ctx = (document.getElementById("codeContext") || {}).value || "user";
    consoleBuffers[ctx] = "";
    const out = document.getElementById("codeOutput");
    if (out) out.textContent = "";
}

// Hook into existing nav system
const _origAcdNav = window.acdNav;
window.acdNav = function (action, el) {
    if (action === "code") {
        document.querySelectorAll(".nav-link").forEach(n => n.classList.remove("active"));
        if (el) el.classList.add("active");
        showCodeScreen();
        return false;
    }
    // leaving code screen
    hideCodeScreen();
    if (typeof _origAcdNav === "function") {
        return _origAcdNav(action, el);
    }
    return false;
};

document.addEventListener("DOMContentLoaded", () => {
    const btnRun = document.getElementById("btnRunCode");
    const btnBack = document.getElementById("btnCodeBack");
    const btnClear = document.getElementById("btnClearConsole");
    const ctxSelect = document.getElementById("codeContext");
    const langSelect = document.getElementById("codeLang");

    if (btnRun) btnRun.addEventListener("click", runCode);
    if (btnBack) btnBack.addEventListener("click", () => {
        hideCodeScreen();
        // activate home nav
        const home = document.querySelector('.nav-link[data-action="home"]');
        if (home) home.classList.add("active");
    });
    if (btnClear) btnClear.addEventListener("click", clearConsole);
    if (ctxSelect) ctxSelect.addEventListener("change", updateConsoleLabel);
    if (langSelect) {
        langSelect.addEventListener("change", () => {
            if (monacoEditor) {
                monaco.editor.setModelLanguage(monacoEditor.getModel(), langSelect.value);
            }
        });
    }
});

// AI can call this later with context="ai"
window.runInSandbox = async function (source, lang = "python", context = "ai") {
    const headers = { "Content-Type": "application/json" };
    if (typeof authToken !== "undefined" && authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
    }
    const res = await fetch("/sandbox/run", {
        method: "POST",
        headers,
        body: JSON.stringify({ source, filename: "main.py", lang, context }),
    });
    return res.json();
};

window.openCodePanel = showCodeScreen; // backward compat
