// Accodite multi-context Monaco + Terminal
// Contexts: user | org | ai – each keeps its own output buffer

let monacoEditor = null;
const consoleBuffers = { user: "", org: "", ai: "" };

function initMonaco() {
    if (monacoEditor) return;
    require.config({
        paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" }
    });
    require(["vs/editor/editor.main"], function () {
        monacoEditor = monaco.editor.create(
            document.getElementById("monacoContainer"),
            {
                value: '# Accodite sandbox\\nprint("Hello from User console")\\n',
                language: "python",
                theme: "vs-dark",
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 14,
            }
        );
    });
}

function openCodePanel() {
    const panel = document.getElementById("codePanel");
    if (!panel) return;
    panel.style.display = "flex";
    initMonaco();
    updateConsoleLabel();
}

function closeCodePanel() {
    const panel = document.getElementById("codePanel");
    if (panel) panel.style.display = "none";
}

function updateConsoleLabel() {
    const ctx = document.getElementById("codeContext").value;
    document.getElementById("consoleContextLabel").textContent = ctx;
    document.getElementById("codeOutput").textContent = consoleBuffers[ctx] || "";
}

async function runCode() {
    if (!monacoEditor) return;
    const source = monacoEditor.getValue();
    const lang = document.getElementById("codeLang").value;
    const context = document.getElementById("codeContext").value;
    const outputEl = document.getElementById("codeOutput");

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
        consoleBuffers[context] += err;
        outputEl.textContent = consoleBuffers[context];
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const btnRun = document.getElementById("btnRunCode");
    const btnClose = document.getElementById("btnCloseCode");
    const ctxSelect = document.getElementById("codeContext");
    const langSelect = document.getElementById("codeLang");

    if (btnRun) btnRun.addEventListener("click", runCode);
    if (btnClose) btnClose.addEventListener("click", closeCodePanel);
    if (ctxSelect) ctxSelect.addEventListener("change", updateConsoleLabel);
    if (langSelect) {
        langSelect.addEventListener("change", () => {
            if (monacoEditor) {
                monaco.editor.setModelLanguage(
                    monacoEditor.getModel(),
                    langSelect.value
                );
            }
        });
    }
});

window.openCodePanel = openCodePanel;
