/**
 * Codespace Phase 1 — fixed navigation
 * Never auto-open. Back/Close always hide panel and show Home (or auth).
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var consoleLog = "";
  var consoleCollapsed = false;

  function $(id) { return document.getElementById(id); }

  function hideCodespace() {
    var panel = $("codePanel");
    if (panel) {
      panel.style.setProperty("display", "none", "important");
    }
  }

  function showCodespace() {
    var panel = $("codePanel");
    if (!panel) {
      console.warn("[codespace] panel missing");
      return;
    }
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    initMonaco();
    setTimeout(function () {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
    }, 100);
  }

  function goHome() {
    hideCodespace();

    // Prefer main app if logged in
    var main = $("mainScreen");
    var auth = $("authScreen");
    var token = (typeof authToken !== "undefined" && authToken) ||
                localStorage.getItem("coMpaNeoN_token") ||
                localStorage.getItem("accodite_token") || "";

    document.querySelectorAll(".screen").forEach(function (s) {
      s.classList.remove("active");
      s.style.display = "none";
    });

    if (token && main) {
      main.classList.add("active");
      main.style.display = "flex";
      var chat = $("chatBox");
      if (chat) chat.style.display = "";
      document.querySelectorAll(".nav-link").forEach(function (n) {
        n.classList.remove("active");
      });
      var homeNav = document.querySelector('.nav-link[data-action="home"]');
      if (homeNav) homeNav.classList.add("active");
      if (typeof window.acdSetScreenMode === "function") {
        try { window.acdSetScreenMode("home"); } catch (e) {}
      }
    } else if (auth) {
      auth.classList.add("active");
      auth.style.display = "flex";
    } else if (main) {
      main.classList.add("active");
      main.style.display = "flex";
    }
  }

  function initMonaco() {
    var el = $("monacoContainer");
    if (!el) return;
    if (monacoEditor) {
      try { monacoEditor.layout(); } catch (e) {}
      return;
    }
    if (typeof require === "undefined") {
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco loader missing — hard refresh.</p>";
      return;
    }
    require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" } });
    require(["vs/editor/editor.main"], function () {
      monacoEditor = monaco.editor.create(el, {
        value: '# Codespace\nprint("Hello from sandbox")\n',
        language: "python",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
      });
    });
  }

  function appendLog(t) {
    consoleLog += t;
    if (consoleLog.length > 80000) consoleLog = consoleLog.slice(-60000);
    var out = $("codeOutput");
    if (out) {
      out.textContent = consoleLog;
      out.scrollTop = out.scrollHeight;
    }
  }

  function setStatus(s) {
    var el = $("codeRunStatus");
    if (el) el.textContent = s || "";
  }

  function toggleConsole() {
    var box = $("codeConsole");
    var btn = $("btnToggleConsole");
    if (!box) return;
    consoleCollapsed = !consoleCollapsed;
    if (consoleCollapsed) {
      box.style.flex = "0 0 40px";
      var pre = $("codeOutput");
      if (pre) pre.style.display = "none";
      var inp = $("consoleInput");
      if (inp && inp.parentElement) inp.parentElement.style.display = "none";
      if (btn) btn.textContent = "Console ▸";
    } else {
      box.style.flex = "0 0 200px";
      var pre2 = $("codeOutput");
      if (pre2) pre2.style.display = "block";
      var inp2 = $("consoleInput");
      if (inp2 && inp2.parentElement) inp2.parentElement.style.display = "flex";
      if (btn) btn.textContent = "Console ▾";
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
    }
  }

  async function runCode() {
    if (!monacoEditor) {
      appendLog("Editor not ready\n");
      initMonaco();
      return;
    }
    var source = monacoEditor.getValue();
    var lang = ($("codeLang") && $("codeLang").value) || "python";
    setStatus("running…");
    appendLog("$ run (" + lang + ")\n");
    try {
      var headers = { "Content-Type": "application/json" };
      var token = (typeof authToken !== "undefined" && authToken) ||
                  localStorage.getItem("coMpaNeoN_token") || "";
      if (token) headers["Authorization"] = "Bearer " + token;
      var res = await fetch("/sandbox/run", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          source: source,
          filename: lang === "python" ? "main.py" : "main.js",
          lang: lang,
          context: "user",
        }),
      });
      var data = await res.json().catch(function () {
        return { ok: false, error: "HTTP " + res.status, stdout: "", stderr: "", backend: "?", exit_code: -1, duration_s: 0 };
      });
      var lines = [
        "backend: " + (data.backend || "?") + "  exit: " + data.exit_code + "  " + (data.duration_s || 0) + "s",
        data.error ? "ERROR: " + data.error : "",
        data.stdout || "",
        data.stderr || "",
        "",
      ];
      appendLog(lines.filter(Boolean).join("\n") + "\n");
      setStatus(data.ok ? "ok" : "failed");
    } catch (e) {
      appendLog("Request failed: " + e.message + "\n");
      setStatus("error");
    }
  }

  function onConsoleCommand(raw) {
    var line = (raw || "").trim();
    if (!line) return;
    appendLog("$ " + line + "\n");
    var cmd = line.split(/\s+/)[0].toLowerCase();
    if (cmd === "clear" || cmd === "cls") {
      consoleLog = "";
      var out = $("codeOutput");
      if (out) out.textContent = "";
      setStatus("");
      return;
    }
    if (cmd === "help") {
      appendLog("commands: run | clear | help\n");
      return;
    }
    if (cmd === "run") {
      runCode();
      return;
    }
    appendLog("unknown: " + cmd + "\n");
  }

  function bind() {
    // ALWAYS start hidden — fixes stuck overlay after reload
    hideCodespace();

    function wire(id, fn) {
      var el = $(id);
      if (el) el.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();
        fn();
      };
    }

    wire("btnCodeBack", goHome);
    wire("btnCloseCode", goHome);
    wire("btnRunCode", runCode);
    wire("btnToggleConsole", toggleConsole);
    wire("btnConsoleSend", function () {
      var input = $("consoleInput");
      if (!input) return;
      onConsoleCommand(input.value);
      input.value = "";
      input.focus();
    });

    var input = $("consoleInput");
    if (input) {
      input.onkeydown = function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          onConsoleCommand(input.value);
          input.value = "";
        }
      };
    }

    var lang = $("codeLang");
    if (lang) {
      lang.onchange = function () {
        if (monacoEditor && window.monaco) {
          try {
            monaco.editor.setModelLanguage(monacoEditor.getModel(), lang.value);
          } catch (e) {}
        }
      };
    }

    wire("btnHomeCode", showCodespace);
    wire("btnHomeConsole", showCodespace);

    // Event delegation backup (in case nodes were replaced)
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t) return;
      var id = t.id || (t.closest && t.closest("[id]") && t.closest("[id]").id);
      if (id === "btnCodeBack" || id === "btnCloseCode") {
        e.preventDefault();
        goHome();
      }
    }, true);
  }

  window.openCodePanel = showCodespace;
  window.closeCodePanel = goHome;
  window.hideCodeScreen = goHome;

  // Do NOT open on load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
