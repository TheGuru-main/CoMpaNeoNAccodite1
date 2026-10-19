/**
 * Codespace — editor + files + true terminal console (typed commands)
 * No account/type dropdown. Back → Home.
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var consoleLog = "";
  var files = { "main.py": '# Codespace\nprint("Hello")\n' };
  var folders = {};
  var currentFile = "main.py";
  var termFocused = false;

  function $(id) { return document.getElementById(id); }

  function goHome() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
    if (typeof window.acdGoHomeStrict === "function") window.acdGoHomeStrict();
    else if (typeof window.acdOpenHub === "function") window.acdOpenHub("home");
  }

  function showPanel() {
    var panel = $("codePanel");
    if (!panel) return;
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    renderFiles();
    initMonaco();
    setTimeout(function () {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
      focusTerminal();
    }, 100);
  }

  function renderFiles() {
    var ul = $("codeFileList");
    if (!ul) return;
    ul.innerHTML = "";
    Object.keys(folders).forEach(function (d) {
      var li = document.createElement("li");
      li.textContent = "📁 " + d;
      li.style.padding = "4px 0";
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
        renderFiles();
      };
      ul.appendChild(li);
    });
  }

  function initMonaco() {
    var el = $("monacoContainer");
    if (!el || monacoEditor) {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
      return;
    }
    if (typeof require === "undefined") {
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco loader missing</p>";
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

  function paintTerminal() {
    var out = $("codeOutput");
    if (!out) return;
    var caret = termFocused ? '<span class="term-caret">▍</span>' : "";
    var cmd = ($("consoleInput") && $("consoleInput").value) || "";
    out.innerHTML =
      "<div class=\"term-log\">" + escapeHtml(consoleLog) + "</div>" +
      "<div class=\"term-line\"><span style=\"color:#22d3ee\">$</span> " +
      escapeHtml(cmd) + caret + "</div>";
    out.scrollTop = out.scrollHeight;
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function focusTerminal() {
    var input = $("consoleInput");
    if (!input) return;
    termFocused = true;
    input.focus();
    paintTerminal();
  }

  function appendLog(t) {
    consoleLog += t;
    if (consoleLog.length > 80000) consoleLog = consoleLog.slice(-60000);
    paintTerminal();
  }

  function detectLang(filename) {
    var n = (filename || "").toLowerCase();
    if (n.endsWith(".py")) return "python";
    if (n.endsWith(".ts") || n.endsWith(".tsx")) return "typescript";
    if (n.endsWith(".js") || n.endsWith(".jsx")) return "javascript";
    if (n.endsWith(".sh") || n.endsWith(".bash")) return "bash";
    return "python";
  }

  async function runCode() {
    if (!monacoEditor) {
      appendLog("Editor not ready\n");
      initMonaco();
      return;
    }
    files[currentFile] = monacoEditor.getValue();
    var source = monacoEditor.getValue();
    var lang = detectLang(currentFile);
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
        return { ok: false, error: "HTTP " + res.status, stdout: "", stderr: "", backend: "?", exit_code: -1 };
      });
      appendLog(
        [data.error, data.stdout, data.stderr].filter(Boolean).join("\n") +
        "\n[exit " + data.exit_code + " via " + (data.backend || "?") + "]\n"
      );
    } catch (e) {
      appendLog("Request failed: " + e.message + "\n");
    }
  }

  function onCmd(raw) {
    var line = (raw || "").trim();
    if (!line) return;
    appendLog("$ " + line + "\n");
    var cmd = line.split(/\s+/)[0].toLowerCase();
    if (cmd === "clear") {
      consoleLog = "";
      paintTerminal();
      return;
    }
    if (cmd === "help") {
      appendLog("run | clear | ls | help\n");
      return;
    }
    if (cmd === "ls") {
      appendLog(
        Object.keys(folders).map(function (d) { return d + "/"; })
          .concat(Object.keys(files)).join("\n") + "\n"
      );
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
    if (!name || !name.trim()) return;
    name = name.trim();
    if (monacoEditor) files[currentFile] = monacoEditor.getValue();
    files[name] = "";
    currentFile = name;
    if (monacoEditor) monacoEditor.setValue("");
    renderFiles();
  }

  function newOrOpenFolder() {
    var choice = prompt(
      "Folder:\n1 = Create new folder name\n2 = Open folder from this device\n\nType 1 or 2:",
      "1"
    );
    if (choice === "2") {
      var inp = $("folderPickerInput");
      if (inp) inp.click();
      return;
    }
    var name = prompt("New folder name:", "src");
    if (!name || !name.trim()) return;
    folders[name.trim()] = true;
    renderFiles();
    appendLog("mkdir " + name.trim() + "\n");
  }

  function onFolderPicked(ev) {
    var list = ev.target && ev.target.files;
    if (!list || !list.length) return;
    var root = null;
    for (var i = 0; i < list.length; i++) {
      var f = list[i];
      var path = f.webkitRelativePath || f.name;
      var parts = path.split("/");
      if (parts.length > 1) {
        root = parts[0];
        folders[root] = true;
      }
      // read text files into virtual FS (best-effort)
      (function (file, rel) {
        var reader = new FileReader();
        reader.onload = function () {
          files[rel] = String(reader.result || "");
          renderFiles();
        };
        if (file.size < 500000) reader.readAsText(file);
      })(f, path);
    }
    if (root) appendLog("opened folder " + root + " (" + list.length + " files)\n");
    renderFiles();
    ev.target.value = "";
  }

  function bind() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");

    function wire(id, fn) {
      var el = $(id);
      if (el) el.onclick = function (e) { e.preventDefault(); fn(); };
    }
    wire("btnCodeBack", goHome);
    wire("btnCloseCode", goHome);
    wire("btnRunCode", runCode);
    wire("btnNewFile", newFile);
    wire("btnNewFolder", newOrOpenFolder);
    wire("btnSaveFile", function () {
      if (monacoEditor) files[currentFile] = monacoEditor.getValue();
      appendLog("saved " + currentFile + "\n");
    });
    wire("btnHomeCode", showPanel);

    var input = $("consoleInput");
    if (input) {
      // visually hidden but drives the terminal line + caret
      input.style.position = "absolute";
      input.style.opacity = "0";
      input.style.height = "1px";
      input.style.width = "1px";
      input.addEventListener("focus", function () { termFocused = true; paintTerminal(); });
      input.addEventListener("blur", function () { termFocused = false; paintTerminal(); });
      input.addEventListener("input", paintTerminal);
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          onCmd(input.value);
          input.value = "";
          paintTerminal();
        }
      });
    }

    var term = $("codeOutput");
    if (term) {
      term.style.cursor = "text";
      term.addEventListener("click", focusTerminal);
    }

    var picker = $("folderPickerInput");
    if (picker) picker.addEventListener("change", onFolderPicked);

    // click anywhere in console header focuses typing
    var cons = $("codeConsole");
    if (cons) cons.addEventListener("click", focusTerminal);

    document.addEventListener("click", function (e) {
      var t = e.target && e.target.closest && e.target.closest("#btnCodeBack, #btnCloseCode");
      if (t) { e.preventDefault(); goHome(); }
    }, true);

    paintTerminal();
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

  window.__acdGetSource = function () {
    try {
      if (typeof monacoEditor !== "undefined" && monacoEditor) return monacoEditor.getValue();
    } catch (e) {}
    return "print(1)\n";
  };
  window.__acdCurrentFile = function () {
    try { return currentFile || "main.py"; } catch (e) { return "main.py"; }
  };


// ============================================================
// ACCD-RUN-FIX (EOF) — force Run to work
// ============================================================
(function () {
  function $(id) { return document.getElementById(id); }

  function termWrite(msg) {
    var out = $("codeOutput");
    if (!out) {
      console.warn("[run]", msg);
      return;
    }
    // support both textContent log and HTML terminal
    if (out.querySelector && out.querySelector(".term-log")) {
      var log = out.querySelector(".term-log");
      log.textContent = (log.textContent || "") + msg;
      out.scrollTop = out.scrollHeight;
    } else {
      out.textContent = (out.textContent || "") + msg;
      out.scrollTop = out.scrollHeight;
    }
  }

  async function forceRun() {
    termWrite("\n$ run\n");
    var source = "";
    try {
      if (window.monaco && document.querySelector(".monaco-editor")) {
        // try global editor from our module
      }
    } catch (e) {}

    // Prefer existing monacoEditor via open API
    var editorValue = null;
    try {
      // codespace stores files; try DOM mirror
      var pre = document.querySelector("#monacoContainer textarea");
      if (pre) editorValue = pre.value;
    } catch (e) {}

    // Call into module if expose
    if (typeof window.__acdGetSource === "function") {
      source = window.__acdGetSource();
    } else if (editorValue) {
      source = editorValue;
    } else {
      // last resort: prompt
      source = "print(1)\n";
      termWrite("(no editor buffer — running default print(1))\n");
    }

    var filename = "main.py";
    if (typeof window.__acdCurrentFile === "function") {
      filename = window.__acdCurrentFile() || filename;
    }
    var lang = "python";
    if (filename.endsWith(".js")) lang = "javascript";
    if (filename.endsWith(".ts")) lang = "typescript";
    if (filename.endsWith(".sh")) lang = "bash";

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
          filename: filename,
          lang: lang,
          context: "user",
        }),
      });

      var text = await res.text();
      var data;
      try { data = JSON.parse(text); } catch (_) {
        termWrite("HTTP " + res.status + " non-JSON: " + text.slice(0, 500) + "\n");
        return;
      }
      if (!res.ok) {
        termWrite("HTTP " + res.status + ": " + (data.detail || data.error || text).toString().slice(0, 500) + "\n");
      }
      termWrite(
        (data.stdout || "") +
        (data.stderr ? data.stderr + "\n" : "") +
        (data.error ? "ERROR: " + data.error + "\n" : "") +
        "[exit " + data.exit_code + " · " + (data.backend || "?") + "]\n"
      );
    } catch (e) {
      termWrite("Run failed: " + e.message + "\n");
    }
  }

  window.__acdForceRun = forceRun;

  function bindRun() {
    var btn = $("btnRunCode");
    if (btn) {
      btn.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();
        forceRun();
      };
    }
    // Delegation on whole panel
    var panel = $("codePanel");
    if (panel && !panel.dataset.runBound) {
      panel.dataset.runBound = "1";
      panel.addEventListener("click", function (e) {
        var t = e.target;
        if (!t) return;
        if (t.id === "btnRunCode" || (t.closest && t.closest("#btnRunCode"))) {
          e.preventDefault();
          e.stopPropagation();
          forceRun();
        }
      }, true);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindRun);
  } else {
    bindRun();
  }
  setTimeout(bindRun, 800);
})();
