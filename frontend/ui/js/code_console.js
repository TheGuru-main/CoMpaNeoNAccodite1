/**
 * Accodite Code / Console panel
 * IDs: codePanel, monacoContainer, codeOutput, btnRunCode,
 *      btnClearConsole, btnCodeBack, btnCloseCode, btnNewRepo
 */
(function () {
  "use strict";

  let monacoEditor = null;
  let previousScreen = null;
  const buffers = { user: "", org: "", ai: "" };

  function $(id) {
    return document.getElementById(id);
  }

  function initMonaco() {
    const el = $("monacoContainer");
    if (!el) {
      console.warn("[code] monacoContainer missing");
      return;
    }
    if (monacoEditor) {
      try { monacoEditor.layout(); } catch (_) {}
      return;
    }
    if (typeof require === "undefined") {
      console.warn("[code] Monaco loader not present");
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco loader missing. Hard-refresh.</p>";
      return;
    }
    require.config({
      paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" },
    });
    require(["vs/editor/editor.main"], function () {
      monacoEditor = monaco.editor.create(el, {
        value: '# Accodite sandbox\nprint("Hello from User console")\n',
        language: "python",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: "on",
      });
    });
  }

  function updateLabel() {
    const ctx = ($("codeContext") || {}).value || "user";
    const label = $("consoleContextLabel");
    if (label) label.textContent = ctx;
    const out = $("codeOutput");
    if (out) out.textContent = buffers[ctx] || "";
  }

  function openCodePanel() {
    // remember what was visible
    previousScreen = document.querySelector(".screen.active") || $("mainScreen");

    const panel = $("codePanel");
    if (!panel) {
      console.warn("[code] codePanel missing");
      return;
    }
    panel.style.display = "flex";
    panel.style.flexDirection = "column";

    // do not destroy other screens; just cover them
    initMonaco();
    updateLabel();
    setTimeout(function () {
      if (monacoEditor) {
        try { monacoEditor.layout(); } catch (_) {}
      }
    }, 100);
  }

  function closeCodePanel() {
    const panel = $("codePanel");
    if (panel) panel.style.display = "none";

    // restore previous screen
    if (previousScreen) {
      document.querySelectorAll(".screen").forEach(function (s) {
        s.classList.remove("active");
        if (s.style) s.style.display = "none";
      });
      previousScreen.classList.add("active");
      previousScreen.style.display = previousScreen.id === "mainScreen" ? "flex" : "";
      if (previousScreen.id === "mainScreen") {
        previousScreen.style.display = "flex";
      }
    } else {
      const main = $("mainScreen");
      if (main) {
        main.classList.add("active");
        main.style.display = "flex";
      }
    }
    previousScreen = null;
  }

  async function runCode() {
    const out = $("codeOutput");
    const status = $("codeRunStatus");
    if (!monacoEditor) {
      if (out) out.textContent = "Editor not ready – wait a second and try again.\n";
      initMonaco();
      return;
    }
    const source = monacoEditor.getValue();
    const lang = ($("codeLang") || {}).value || "python";
    const context = ($("codeContext") || {}).value || "user";

    if (status) status.textContent = "running…";
    if (out) out.textContent = "[" + context + "] Running…\n";

    try {
      const headers = { "Content-Type": "application/json" };
      if (typeof authToken !== "undefined" && authToken) {
        headers["Authorization"] = "Bearer " + authToken;
      }
      const res = await fetch("/sandbox/run", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          source: source,
          filename: lang === "python" ? "main.py" : "main.js",
          lang: lang,
          context: context,
        }),
      });
      let data;
      try {
        data = await res.json();
      } catch (_) {
        data = { ok: false, error: "HTTP " + res.status, stdout: "", stderr: "", backend: "?", exit_code: -1, duration_s: 0 };
      }
      const text = [
        "backend: " + (data.backend || "?") + "  exit: " + data.exit_code + "  " + (data.duration_s || 0) + "s",
        data.timed_out ? "TIMEOUT" : "",
        data.error ? "ERROR: " + data.error : "",
        "── stdout ──",
        data.stdout || "(empty)",
        "── stderr ──",
        data.stderr || "(empty)",
      ].filter(Boolean).join("\n");

      buffers[context] = (buffers[context] || "") + text + "\n\n";
      if (out) {
        out.textContent = buffers[context];
        out.scrollTop = out.scrollHeight;
      }
      if (status) status.textContent = data.ok ? "ok" : "failed";
    } catch (e) {
      const err = "Request failed: " + e.message + "\n";
      buffers[context] = (buffers[context] || "") + err;
      if (out) out.textContent = buffers[context];
      if (status) status.textContent = "error";
    }
  }

  function clearConsole() {
    const context = ($("codeContext") || {}).value || "user";
    buffers[context] = "";
    const out = $("codeOutput");
    if (out) out.textContent = "";
    const status = $("codeRunStatus");
    if (status) status.textContent = "";
  }

  function newRepoSpace() {
    // Placeholder: local “repo space” name in console until FS API exists
    const name = prompt("Repo space name (local label):", "my-repo");
    if (!name) return;
    const context = ($("codeContext") || {}).value || "user";
    const line = "[repo] created space: " + name + " (context=" + context + ")\n";
    buffers[context] = (buffers[context] || "") + line;
    const out = $("codeOutput");
    if (out) out.textContent = buffers[context];
    if (monacoEditor) {
      const cur = monacoEditor.getValue();
      monacoEditor.setValue("# repo: " + name + "\n" + cur);
    }
  }

  function bind() {
    const run = $("btnRunCode");
    const clear = $("btnClearConsole");
    const back = $("btnCodeBack");
    const close = $("btnCloseCode");
    const repo = $("btnNewRepo");
    const ctx = $("codeContext");
    const lang = $("codeLang");

    if (run) run.onclick = function (e) { e.preventDefault(); runCode(); };
    if (clear) clear.onclick = function (e) { e.preventDefault(); clearConsole(); };
    if (back) back.onclick = function (e) { e.preventDefault(); closeCodePanel(); };
    if (close) close.onclick = function (e) { e.preventDefault(); closeCodePanel(); };
    if (repo) repo.onclick = function (e) { e.preventDefault(); newRepoSpace(); };
    if (ctx) ctx.onchange = updateLabel;
    if (lang) {
      lang.onchange = function () {
        if (monacoEditor && window.monaco) {
          monaco.editor.setModelLanguage(monacoEditor.getModel(), lang.value);
        }
      };
    }

    // Home buttons if present
    const homeCode = $("btnHomeCode");
    const homeConsole = $("btnHomeConsole");
    if (homeCode) homeCode.onclick = function (e) { e.preventDefault(); openCodePanel(); };
    if (homeConsole) homeConsole.onclick = function (e) { e.preventDefault(); openCodePanel(); };
  }

  // Public API
  window.openCodePanel = openCodePanel;
  window.closeCodePanel = closeCodePanel;
  window.hideCodeScreen = closeCodePanel;
  window.runInSandbox = async function (source, lang, context) {
    lang = lang || "python";
    context = context || "ai";
    const headers = { "Content-Type": "application/json" };
    if (typeof authToken !== "undefined" && authToken) {
      headers["Authorization"] = "Bearer " + authToken;
    }
    const res = await fetch("/sandbox/run", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        source: source,
        filename: "main.py",
        lang: lang,
        context: context,
      }),
    });
    return res.json();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
