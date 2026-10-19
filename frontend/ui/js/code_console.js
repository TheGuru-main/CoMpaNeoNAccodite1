/**
 * Accodite Codespace — Phase 1
 * - Back / ✕ → Home only
 * - No User/Org/AI dropdown (scope from session later)
 * - Collapsible console + $ input
 * - Run → POST /sandbox/run → SandboxRunner
 * - Nested back stack stub for Phase 2
 */
(function () {
  "use strict";

  let monacoEditor = null;
  let consoleCollapsed = false;
  let consoleLog = "";
  // Phase 2: nested screens push/pop here; top-level back ignores this and goes Home
  const viewStack = [];

  function $(id) {
    return document.getElementById(id);
  }

  function goHome() {
    const panel = $("codePanel");
    if (panel) panel.style.display = "none";

    // clear nested stack
    viewStack.length = 0;

    // activate Home / mainScreen
    document.querySelectorAll(".screen").forEach(function (s) {
      s.classList.remove("active");
      if (s.style) s.style.display = "none";
    });
    const main = $("mainScreen");
    if (main) {
      main.classList.add("active");
      main.style.display = "flex";
    }
    const chat = $("chatBox");
    if (chat) chat.style.display = "";

    // nav highlight home
    document.querySelectorAll(".nav-link").forEach(function (n) {
      n.classList.remove("active");
    });
    const homeNav = document.querySelector('.nav-link[data-action="home"]');
    if (homeNav) homeNav.classList.add("active");

    if (typeof window.acdSetScreenMode === "function") {
      window.acdSetScreenMode("home");
    }
  }

  /** Nested back: previous Codespace view, or Home if stack empty */
  function nestedBack() {
    if (viewStack.length > 0) {
      const prev = viewStack.pop();
      if (typeof prev === "function") prev();
      return;
    }
    goHome();
  }

  function openCodePanel() {
    const panel = $("codePanel");
    if (!panel) {
      console.warn("[codespace] codePanel missing");
      return;
    }
    panel.style.display = "flex";
    panel.style.flexDirection = "column";
    initMonaco();
    setTimeout(function () {
      if (monacoEditor) {
        try { monacoEditor.layout(); } catch (_) {}
      }
      const input = $("consoleInput");
      if (input) input.focus();
    }, 120);
  }

  function initMonaco() {
    const el = $("monacoContainer");
    if (!el) return;
    if (monacoEditor) {
      try { monacoEditor.layout(); } catch (_) {}
      return;
    }
    if (typeof require === "undefined") {
      el.innerHTML = "<p style='color:#f87171;padding:1rem;font-size:13px'>Monaco loader missing — hard-refresh the app.</p>";
      return;
    }
    require.config({
      paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" },
    });
    require(["vs/editor/editor.main"], function () {
      monacoEditor = monaco.editor.create(el, {
        value: '# Codespace\nprint("Hello from sandbox")\n',
        language: "python",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: "on",
      });
    });
  }

  function appendLog(text) {
    consoleLog += text;
    if (consoleLog.length > 80000) consoleLog = consoleLog.slice(-60000);
    const out = $("codeOutput");
    if (out) {
      out.textContent = consoleLog;
      out.scrollTop = out.scrollHeight;
    }
  }

  function setStatus(s) {
    const el = $("codeRunStatus");
    if (el) el.textContent = s || "";
  }

  function toggleConsole() {
    const box = $("codeConsole");
    const btn = $("btnToggleConsole");
    if (!box) return;
    consoleCollapsed = !consoleCollapsed;
    if (consoleCollapsed) {
      box.style.flex = "0 0 36px";
      box.style.maxHeight = "36px";
      const pre = $("codeOutput");
      const row = box.querySelector('div[style*="border-top"]');
      if (pre) pre.style.display = "none";
      // keep header visible; hide input row roughly
      const inputRow = $("consoleInput");
      if (inputRow && inputRow.parentElement) inputRow.parentElement.style.display = "none";
      if (btn) btn.textContent = "Console ▸";
    } else {
      box.style.flex = "0 0 200px";
      box.style.maxHeight = "45%";
      const pre = $("codeOutput");
      if (pre) pre.style.display = "block";
      const inputRow = $("consoleInput");
      if (inputRow && inputRow.parentElement) inputRow.parentElement.style.display = "flex";
      if (btn) btn.textContent = "Console ▾";
      if (monacoEditor) {
        try { monacoEditor.layout(); } catch (_) {}
      }
    }
  }

  async function runCode() {
    if (!monacoEditor) {
      appendLog("Editor not ready — wait a moment.\n");
      initMonaco();
      return;
    }
    const source = monacoEditor.getValue();
    const lang = ($("codeLang") || {}).value || "python";
    setStatus("running…");
    appendLog("$ run (" + lang + ")\n");

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
          filename: lang === "python" ? "main.py" : lang === "bash" ? "main.sh" : "main.js",
          lang: lang,
          context: "user",
        }),
      });
      let data;
      try {
        data = await res.json();
      } catch (_) {
        data = {
          ok: false,
          error: "HTTP " + res.status,
          stdout: "",
          stderr: await res.text().catch(function () { return ""; }),
          backend: "?",
          exit_code: -1,
          duration_s: 0,
        };
      }
      const block = [
        "backend: " + (data.backend || "?") + "  exit: " + data.exit_code + "  " + (data.duration_s || 0) + "s",
        data.timed_out ? "TIMEOUT" : "",
        data.error ? "ERROR: " + data.error : "",
        data.stdout ? data.stdout : "",
        data.stderr ? data.stderr : "",
        "",
      ].filter(function (x) { return x !== ""; }).join("\n");
      appendLog(block + (block.endsWith("\n") ? "" : "\n"));
      setStatus(data.ok ? "ok" : "failed");
    } catch (e) {
      appendLog("Request failed: " + e.message + "\n");
      setStatus("error");
    }
  }

  function clearConsole() {
    consoleLog = "";
    const out = $("codeOutput");
    if (out) out.textContent = "";
    setStatus("");
  }

  function handleConsoleCommand(raw) {
    const line = (raw || "").trim();
    if (!line) return;
    appendLog("$ " + line + "\n");
    const parts = line.split(/\s+/);
    const cmd = parts[0].toLowerCase();

    if (cmd === "clear" || cmd === "cls") {
      clearConsole();
      return;
    }
    if (cmd === "help") {
      appendLog("commands: run | clear | help\n(Phase 2: ls, mkdir, …)\n");
      return;
    }
    if (cmd === "run") {
      runCode();
      return;
    }
    appendLog("unknown command: " + cmd + " (try help)\n");
  }

  function bind() {
    const back = $("btnCodeBack");
    const close = $("btnCloseCode");
    const run = $("btnRunCode");
    const toggle = $("btnToggleConsole");
    const send = $("btnConsoleSend");
    const input = $("consoleInput");
    const lang = $("codeLang");

    // Phase 1: both back and close → Home (nested stack empty)
    if (back) {
      back.onclick = function (e) {
        e.preventDefault();
        nestedBack(); // empty stack → Home
      };
    }
    if (close) {
      close.onclick = function (e) {
        e.preventDefault();
        goHome();
      };
    }
    if (run) {
      run.onclick = function (e) {
        e.preventDefault();
        runCode();
      };
    }
    if (toggle) {
      toggle.onclick = function (e) {
        e.preventDefault();
        toggleConsole();
      };
    }
    if (send) {
      send.onclick = function (e) {
        e.preventDefault();
        if (!input) return;
        handleConsoleCommand(input.value);
        input.value = "";
        input.focus();
      };
    }
    if (input) {
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          handleConsoleCommand(input.value);
          input.value = "";
        }
      });
    }
    if (lang) {
      lang.onchange = function () {
        if (monacoEditor && window.monaco) {
          try {
            monaco.editor.setModelLanguage(monacoEditor.getModel(), lang.value);
          } catch (_) {}
        }
      };
    }

    // Home entry points
    const homeCode = $("btnHomeCode");
    const homeConsole = $("btnHomeConsole");
    if (homeCode) {
      homeCode.onclick = function (e) {
        e.preventDefault();
        openCodePanel();
      };
    }
    if (homeConsole) {
      homeConsole.onclick = function (e) {
        e.preventDefault();
        openCodePanel();
      };
    }
  }

  // Public API
  window.openCodePanel = openCodePanel;
  window.closeCodePanel = goHome;
  window.hideCodeScreen = goHome;
  window.acdCodespaceNestedBack = nestedBack;
  window.acdCodespacePushView = function (restoreFn) {
    viewStack.push(restoreFn);
  };
  window.runInSandbox = async function (source, lang) {
    lang = lang || "python";
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
        context: "ai",
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
