/**
 * Accodite Codespace — demo-ready
 * Editor (Monaco) + virtual FS + bottom Terminal
 * ONE run path → /sandbox/run → SandboxRunner
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var log = "";
  var cwd = "/";
  var currentFile = "main.py";
  // path -> content  (paths always start with /)
  var fs = {
    "/main.py": '# Accodite Codespace\nprint("Hello from sandbox")\n',
  };
  var dirs = { "/": true };

  var TEMPLATES = {
    ".py": '# new file\nprint("ok")\n',
    ".js": '// new file\nconsole.log("ok");\n',
    ".html": "<!DOCTYPE html>\n<html><body><h1>ok</h1></body></html>\n",
    ".css": "/* new stylesheet */\nbody { margin: 0; }\n",
    ".ts": "// typescript\nconst x: string = 'ok';\nconsole.log(x);\n",
    ".sh": "#!/bin/bash\necho ok\n",
  };

  function $(id) { return document.getElementById(id); }

  function norm(p) {
    if (!p) return cwd;
    var base = p.startsWith("/") ? p : (cwd.replace(/\/$/, "") + "/" + p);
    var parts = [];
    base.split("/").forEach(function (s) {
      if (!s || s === ".") return;
      if (s === "..") { parts.pop(); return; }
      parts.push(s);
    });
    return "/" + parts.join("/");
  }

  function parentDir(p) {
    var i = p.lastIndexOf("/");
    return i <= 0 ? "/" : p.slice(0, i);
  }

  function ensureDir(d) {
    d = norm(d);
    if (d !== "/") dirs[d] = true;
    var cur = d;
    while (cur && cur !== "/") {
      dirs[cur] = true;
      cur = parentDir(cur);
    }
  }

  function detectLang(path) {
    var n = (path || "").toLowerCase();
    if (n.endsWith(".py")) return "python";
    if (n.endsWith(".js") || n.endsWith(".jsx")) return "javascript";
    if (n.endsWith(".ts") || n.endsWith(".tsx")) return "typescript";
    if (n.endsWith(".html") || n.endsWith(".htm")) return "html";
    if (n.endsWith(".css")) return "css";
    if (n.endsWith(".sh")) return "bash";
    return "plaintext";
  }

  function writeLog(s) {
    log += s;
    if (log.length > 100000) log = log.slice(-80000);
    var out = $("codeOutput");
    if (out) {
      out.textContent = log;
      out.scrollTop = out.scrollHeight;
    }
  }

  function setCwdLabel() {
    var el = $("codeCwdLabel");
    if (el) el.textContent = cwd;
  }

  function syncEditorFromFs() {
    if (!monacoEditor) return;
    var path = norm(currentFile);
    var body = fs[path] != null ? fs[path] : "";
    monacoEditor.setValue(body);
    try {
      if (window.monaco) {
        monaco.editor.setModelLanguage(monacoEditor.getModel(), detectLang(path));
      }
    } catch (e) {}
  }

  function saveEditorToFs() {
    if (!monacoEditor) return;
    fs[norm(currentFile)] = monacoEditor.getValue();
  }

  function renderFiles() {
    var ul = $("codeFileList");
    if (!ul) return;
    ul.innerHTML = "";
    Object.keys(dirs).sort().forEach(function (d) {
      if (d === "/") return;
      var li = document.createElement("li");
      li.textContent = "📁 " + d;
      li.style.cssText = "padding:3px 0;cursor:pointer;opacity:0.9;";
      li.onclick = function () { cwd = d; setCwdLabel(); writeLog("$ cd " + d + "\n"); };
      ul.appendChild(li);
    });
    Object.keys(fs).sort().forEach(function (path) {
      var li = document.createElement("li");
      var name = path === "/" ? path : path.split("/").pop();
      li.textContent = "📄 " + name;
      li.style.cssText = "padding:3px 0;cursor:pointer;";
      if (norm(currentFile) === path) li.style.color = "#22d3ee";
      li.onclick = function () {
        saveEditorToFs();
        currentFile = path;
        cwd = parentDir(path);
        setCwdLabel();
        syncEditorFromFs();
        renderFiles();
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
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco loader missing — hard refresh</p>";
      return;
    }
    require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" } });
    require(["vs/editor/editor.main"], function () {
      monacoEditor = monaco.editor.create(el, {
        value: fs[norm(currentFile)] || "",
        language: detectLang(currentFile),
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
      });
    });
  }

  async function sandboxRun(source, filename, lang) {
    var headers = { "Content-Type": "application/json" };
    var token = (typeof authToken !== "undefined" && authToken) ||
                localStorage.getItem("coMpaNeoN_token") || "";
    if (token) headers["Authorization"] = "Bearer " + token;
    var res = await fetch("/sandbox/run", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        source: source,
        filename: filename || "main.py",
        lang: lang || "python",
        context: "user",
      }),
    });
    var text = await res.text();
    try {
      return JSON.parse(text);
    } catch (e) {
      return { ok: false, error: "HTTP " + res.status + " " + text.slice(0, 300), exit_code: -1, backend: "?", stdout: "", stderr: "" };
    }
  }

  async function runActiveFile() {
    if (!monacoEditor) {
      writeLog("Editor not ready — open Codespace again\n");
      initMonaco();
      return;
    }
    saveEditorToFs();
    var path = norm(currentFile);
    var source = fs[path] || monacoEditor.getValue();
    var lang = detectLang(path);
    if (lang === "html" || lang === "css") {
      writeLog("Cannot execute " + lang + " via sandbox — open/edit only\n");
      return;
    }
    if (lang === "plaintext") lang = "python";
    writeLog("$ run " + path + "\n");
    var data = await sandboxRun(source, path.split("/").pop(), lang === "typescript" ? "javascript" : lang);
    if (data.stdout) writeLog(data.stdout.replace(/\n?$/, "\n"));
    if (data.stderr) writeLog(data.stderr.replace(/\n?$/, "\n"));
    if (data.error) writeLog("ERROR: " + data.error + "\n");
    writeLog("[exit " + data.exit_code + " · " + (data.backend || "?") + "]\n");
  }

  async function onCommand(line) {
    line = (line || "").trim();
    if (!line) return;
    writeLog("$ " + line + "\n");
    var parts = line.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
    parts = parts.map(function (p) { return p.replace(/^"|"$/g, ""); });
    var cmd = (parts[0] || "").toLowerCase();
    var arg = parts[1] || "";

    if (cmd === "help") {
      writeLog("pwd  ls  cd <dir>  cat <file>  touch <file>  mkdir <dir>\n");
      writeLog("run [file]  python <file>  clear  help\n");
      return;
    }
    if (cmd === "clear" || cmd === "cls") {
      log = "";
      writeLog("");
      return;
    }
    if (cmd === "pwd") {
      writeLog(cwd + "\n");
      return;
    }
    if (cmd === "ls") {
      var prefix = cwd === "/" ? "/" : cwd + "/";
      var names = [];
      Object.keys(dirs).forEach(function (d) {
        if (d === cwd) return;
        if (parentDir(d) === cwd || (cwd === "/" && d.split("/").length === 2)) {
          names.push(d.split("/").pop() + "/");
        }
      });
      Object.keys(fs).forEach(function (f) {
        if (parentDir(f) === cwd || (cwd === "/" && f.split("/").length === 2)) {
          names.push(f.split("/").pop());
        }
      });
      writeLog((names.sort().join("  ") || "(empty)") + "\n");
      return;
    }
    if (cmd === "cd") {
      if (!arg || arg === "/") { cwd = "/"; setCwdLabel(); return; }
      var target = norm(arg);
      if (dirs[target] || target === "/") {
        cwd = target;
        setCwdLabel();
      } else {
        writeLog("cd: no such directory: " + arg + "\n");
      }
      return;
    }
    if (cmd === "cat") {
      if (!arg) { writeLog("cat: missing file\n"); return; }
      var cp = norm(arg);
      if (fs[cp] == null) { writeLog("cat: no such file\n"); return; }
      writeLog(fs[cp] + (fs[cp].endsWith("\n") ? "" : "\n"));
      return;
    }
    if (cmd === "touch") {
      if (!arg) { writeLog("touch: missing name\n"); return; }
      var tp = norm(arg);
      ensureDir(parentDir(tp));
      if (fs[tp] == null) {
        var ext = "";
        Object.keys(TEMPLATES).forEach(function (e) {
          if (tp.toLowerCase().endsWith(e)) ext = e;
        });
        fs[tp] = TEMPLATES[ext] || "";
      }
      renderFiles();
      writeLog("created " + tp + "\n");
      return;
    }
    if (cmd === "mkdir") {
      if (!arg) { writeLog("mkdir: missing name\n"); return; }
      var dp = norm(arg);
      ensureDir(dp);
      renderFiles();
      writeLog("mkdir " + dp + "\n");
      return;
    }
    if (cmd === "run" || cmd === "python" || cmd === "node") {
      if (arg) {
        var rp = norm(arg);
        if (fs[rp] == null) { writeLog("no such file: " + arg + "\n"); return; }
        saveEditorToFs();
        currentFile = rp;
        syncEditorFromFs();
      }
      await runActiveFile();
      return;
    }
    writeLog("unknown command: " + cmd + " (try help)\n");
  }

  function newFile() {
    var name = prompt("File name (.py .js .html .css .ts .sh):", "app.py");
    if (!name || !name.trim()) return;
    name = name.trim();
    var path = norm(name);
    ensureDir(parentDir(path));
    var ext = "";
    Object.keys(TEMPLATES).forEach(function (e) {
      if (path.toLowerCase().endsWith(e)) ext = e;
    });
    if (!ext) {
      path = path + ".py";
      ext = ".py";
    }
    saveEditorToFs();
    fs[path] = TEMPLATES[ext] || "";
    currentFile = path;
    cwd = parentDir(path);
    setCwdLabel();
    syncEditorFromFs();
    renderFiles();
    writeLog("created " + path + "\n");
  }

  function newFolder() {
    var choice = prompt("1 = create folder name\n2 = open folder from phone\n\nType 1 or 2:", "1");
    if (choice === "2") {
      var inp = $("folderPickerInput");
      if (inp) inp.click();
      return;
    }
    var name = prompt("Folder name:", "src");
    if (!name || !name.trim()) return;
    var d = norm(name.trim());
    ensureDir(d);
    cwd = d;
    setCwdLabel();
    renderFiles();
    writeLog("mkdir " + d + "\n");
  }

  function onFolderPicked(ev) {
    var list = ev.target.files;
    if (!list || !list.length) return;
    for (var i = 0; i < list.length; i++) {
      (function (file) {
        var rel = file.webkitRelativePath || file.name;
        var path = norm(rel);
        ensureDir(parentDir(path));
        if (file.size < 400000) {
          var reader = new FileReader();
          reader.onload = function () {
            fs[path] = String(reader.result || "");
            renderFiles();
          };
          reader.readAsText(file);
        }
      })(list[i]);
    }
    writeLog("imported " + list.length + " files\n");
    ev.target.value = "";
  }

  function goHome() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
    if (typeof window.acdGoHomeStrict === "function") window.acdGoHomeStrict();
    hideHomePrompt();
  }

  function showPanel() {
    var panel = $("codePanel");
    if (!panel) return;
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    setCwdLabel();
    renderFiles();
    initMonaco();
    setTimeout(function () {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
      var input = $("consoleInput");
      if (input) input.focus();
    }, 120);
  }

  function hideHomePrompt() {
    var input = $("inputArea");
    if (input && !window.currentRoomId) {
      input.style.setProperty("display", "none", "important");
    }
  }

  function bind() {
    hideHomePrompt();
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");

    function wire(id, fn) {
      var el = $(id);
      if (el) el.onclick = function (e) { e.preventDefault(); e.stopPropagation(); fn(); };
    }
    wire("btnCodeBack", goHome);
    wire("btnCloseCode", goHome);
    wire("btnRunCode", runActiveFile); // SINGLE run path
    wire("btnNewFile", newFile);
    wire("btnNewFolder", newFolder);
    wire("btnSaveFile", function () {
      saveEditorToFs();
      writeLog("saved " + norm(currentFile) + "\n");
    });
    wire("btnHomeCode", showPanel);

    var input = $("consoleInput");
    if (input) {
      input.onkeydown = function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          var v = input.value;
          input.value = "";
          onCommand(v);
        }
      };
    }
    var out = $("codeOutput");
    if (out) out.onclick = function () { if (input) input.focus(); };

    var picker = $("folderPickerInput");
    if (picker) picker.onchange = onFolderPicked;

    // keep home prompt dead when no room
    setInterval(hideHomePrompt, 1500);

    writeLog("Accodite terminal ready. Type help.\n");
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
