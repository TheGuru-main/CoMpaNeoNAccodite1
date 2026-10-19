/**
 * Codespace: Monaco editor + file tree + terminal console
 * Back → Home. Console is NOT the editor.
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var consoleLog = "";
  var consoleCollapsed = false;
  var files = {
    "main.py": '# Codespace\nprint("Hello from sandbox")\n'
  };
  var currentFile = "main.py";
  var folders = {};

  function $(id) { return document.getElementById(id); }

  function hidePanel() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
  }

  function goHome() {
    hidePanel();
    if (typeof window.acdOpenHub === "function") {
      window.acdOpenHub("home");
      return;
    }
    var main = $("mainScreen");
    if (main) {
      main.classList.add("active");
      main.style.display = "flex";
    }
  }

  function showPanel() {
    var panel = $("codePanel");
    if (!panel) return;
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    renderFileList();
    initMonaco();
    setTimeout(function () {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
    }, 80);
  }

  function renderFileList() {
    var ul = $("codeFileList");
    if (!ul) return;
    ul.innerHTML = "";
    Object.keys(folders).forEach(function (dir) {
      var li = document.createElement("li");
      li.textContent = "📁 " + dir;
      li.style.padding = "4px 0";
      li.style.opacity = "0.85";
      ul.appendChild(li);
    });
    Object.keys(files).forEach(function (name) {
      var li = document.createElement("li");
      li.textContent = "📄 " + name;
      li.style.padding = "4px 0";
      li.style.cursor = "pointer";
      if (name === currentFile) li.style.color = "#22d3ee";
      li.onclick = function () {
        if (monacoEditor) files[currentFile] = monacoEditor.getValue();
        currentFile = name;
        if (monacoEditor) monacoEditor.setValue(files[name] || "");
        renderFileList();
      };
      ul.appendChild(li);
    });
  }

  function initMonaco() {
    var el = $("monacoContainer");
    if (!el) return;
    if (monacoEditor) {
      try { monacoEditor.layout(); } catch (e) {}
      return;
    }
    if (typeof require === "undefined") {
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco missing — hard refresh</p>";
      return;
    }
    require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" } });
    require(["vs/editor/editor.main"], function () {
      monacoEditor = monaco.editor.create(el, {
        value: files[currentFile] || "",
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
      box.style.flex = "0 0 36px";
      if ($("codeOutput")) $("codeOutput").style.display = "none";
      var inp = $("consoleInput");
      if (inp && inp.parentElement) inp.parentElement.style.display = "none";
      if (btn) btn.textContent = "Console ▸";
    } else {
      box.style.flex = "0 0 180px";
      if ($("codeOutput")) $("codeOutput").style.display = "block";
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
    files[currentFile] = monacoEditor.getValue();
    var source = monacoEditor.getValue();
    var lang = ($("codeLang") && $("codeLang").value) || "python";
    setStatus("running…");
    appendLog("$ run " + currentFile + "\n");
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
          filename: currentFile,
          lang: lang,
          context: "user",
        }),
      });
      var data = await res.json().catch(function () {
        return { ok: false, error: "HTTP " + res.status, stdout: "", stderr: "", backend: "?", exit_code: -1, duration_s: 0 };
      });
      appendLog(
        ["backend: " + (data.backend || "?") + " exit:" + data.exit_code,
         data.error || "", data.stdout || "", data.stderr || "", ""].filter(Boolean).join("\n") + "\n"
      );
      setStatus(data.ok ? "ok" : "failed");
    } catch (e) {
      appendLog("Request failed: " + e.message + "\n");
      setStatus("error");
    }
  }

  function onCmd(raw) {
    var line = (raw || "").trim();
    if (!line) return;
    appendLog("$ " + line + "\n");
    var parts = line.split(/\s+/);
    var cmd = parts[0].toLowerCase();
    if (cmd === "clear") {
      consoleLog = "";
      if ($("codeOutput")) $("codeOutput").textContent = "";
      return;
    }
    if (cmd === "help") {
      appendLog("run | clear | ls | help\n");
      return;
    }
    if (cmd === "ls") {
      appendLog(Object.keys(folders).map(function (d) { return d + "/"; }).concat(Object.keys(files)).join("\n") + "\n");
      return;
    }
    if (cmd === "run") {
      runCode();
      return;
    }
    appendLog("unknown: " + cmd + "\n");
  }

  function newFile() {
    var name = prompt("File name:", "untitled.py");
    if (!name) return;
    name = name.trim();
    if (!name) return;
    if (monacoEditor) files[currentFile] = monacoEditor.getValue();
    files[name] = "";
    currentFile = name;
    if (monacoEditor) monacoEditor.setValue("");
    renderFileList();
  }

  function newFolder() {
    var name = prompt("Folder name:", "src");
    if (!name) return;
    name = name.trim();
    if (!name) return;
    folders[name] = true;
    renderFileList();
    appendLog("folder: " + name + "/\n");
  }

  function saveFile() {
    if (monacoEditor) files[currentFile] = monacoEditor.getValue();
    appendLog("saved " + currentFile + "\n");
    setStatus("saved");
  }

  function bind() {
    hidePanel();
    function wire(id, fn) {
      var el = $(id);
      if (el) el.onclick = function (e) {
        e.preventDefault();
        fn();
      };
    }
    wire("btnCodeBack", goHome);
    wire("btnCloseCode", goHome);
    wire("btnRunCode", runCode);
    wire("btnToggleConsole", toggleConsole);
    wire("btnNewFile", newFile);
    wire("btnNewFolder", newFolder);
    wire("btnSaveFile", saveFile);
    wire("btnConsoleSend", function () {
      var input = $("consoleInput");
      if (!input) return;
      onCmd(input.value);
      input.value = "";
    });
    var input = $("consoleInput");
    if (input) {
      input.onkeydown = function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          onCmd(input.value);
          input.value = "";
        }
      };
    }
    wire("btnHomeCode", showPanel);
    document.addEventListener("click", function (e) {
      var t = e.target && e.target.closest && e.target.closest("#btnCodeBack, #btnCloseCode");
      if (t) {
        e.preventDefault();
        goHome();
      }
    }, true);
  }

  window.openCodePanel = showPanel;
  window.closeCodePanel = goHome;
  window.hideCodeScreen = goHome;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
