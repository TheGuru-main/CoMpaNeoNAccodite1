/**
 * Accodite Codespace Phase 2
 * Repos + FS API + Terminal + nested back stack
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var log = "";
  var scope = "user";
  var repo = null;
  var cwd = "";
  var currentFile = "main.py";
  var viewMode = "edit"; // edit | preview
  var stack = []; // nested restore fns; empty → Home

  var TEMPLATES = {
    ".py": 'print("ok")\n',
    ".js": 'console.log("ok");\n',
    ".html": "<!DOCTYPE html>\n<html><body><h1>ok</h1></body></html>\n",
    ".css": "body { margin: 0; }\n",
    ".md": "# note\n",
    ".ts": 'const x: string = "ok";\nconsole.log(x);\n',
    ".sh": "#!/bin/bash\necho ok\n",
  };

  function $(id) { return document.getElementById(id); }

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    var token = (typeof authToken !== "undefined" && authToken) ||
                localStorage.getItem("coMpaNeoN_token") || "";
    if (token) h["Authorization"] = "Bearer " + token;
    return h;
  }

  function writeLog(s) {
    log += s;
    if (log.length > 120000) log = log.slice(-90000);
    var out = $("codeOutput");
    if (out) { out.textContent = log; out.scrollTop = out.scrollHeight; }
  }

  function detectLang(path) {
    var n = (path || "").toLowerCase();
    if (n.endsWith(".py")) return "python";
    if (n.endsWith(".js") || n.endsWith(".jsx")) return "javascript";
    if (n.endsWith(".ts") || n.endsWith(".tsx")) return "typescript";
    if (n.endsWith(".html")) return "html";
    if (n.endsWith(".css")) return "css";
    if (n.endsWith(".md")) return "markdown";
    if (n.endsWith(".sh")) return "shell";
    return "plaintext";
  }

  function goHome() {
    stack.length = 0;
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
    if (typeof window.acdGoHomeStrict === "function") window.acdGoHomeStrict();
  }

  function nestedBack() {
    if (stack.length) {
      var fn = stack.pop();
      if (typeof fn === "function") fn();
      return;
    }
    goHome();
  }

  function pushView(restore) {
    stack.push(restore);
  }

  async function api(path, method, body) {
    var opt = { method: method || "GET", headers: authHeaders() };
    if (body != null) opt.body = JSON.stringify(body);
    var res = await fetch(path, opt);
    var text = await res.text();
    var data;
    try { data = JSON.parse(text); } catch (e) {
      throw new Error("HTTP " + res.status + " " + text.slice(0, 200));
    }
    if (!res.ok) throw new Error(data.detail || data.error || ("HTTP " + res.status));
    return data;
  }

  async function refreshRepos() {
    var sel = $("codeRepoSelect");
    if (!sel) return;
    var data = await api("/sandbox/repos?scope=" + encodeURIComponent(scope));
    var repos = data.repos || [];
    sel.innerHTML = "";
    if (!repos.length) {
      var o = document.createElement("option");
      o.value = "";
      o.textContent = "(no repo)";
      sel.appendChild(o);
      repo = null;
      return;
    }
    repos.forEach(function (r) {
      var o = document.createElement("option");
      o.value = r.name;
      o.textContent = r.name;
      sel.appendChild(o);
    });
    if (!repo || !repos.find(function (r) { return r.name === repo; })) {
      repo = repos[0].name;
    }
    sel.value = repo;
  }

  async function loadTree() {
    var ul = $("codeFileList");
    if (!ul) return;
    ul.innerHTML = "";
    if (!repo) {
      ul.innerHTML = "<li style='opacity:0.5'>Create a repo</li>";
      return;
    }
    try {
      var data = await api(
        "/sandbox/fs/list?scope=" + encodeURIComponent(scope) +
        "&repo=" + encodeURIComponent(repo) +
        "&path=" + encodeURIComponent(cwd)
      );
      if (cwd) {
        var up = document.createElement("li");
        up.textContent = "‥ /";
        up.style.cssText = "padding:3px 0;cursor:pointer;color:#94a3b8;";
        up.onclick = function () {
          var parts = cwd.split("/").filter(Boolean);
          parts.pop();
          cwd = parts.join("/");
          loadTree();
        };
        ul.appendChild(up);
      }
      (data.entries || []).forEach(function (e) {
        var li = document.createElement("li");
        li.textContent = (e.type === "dir" ? "📁 " : "📄 ") + e.name;
        li.style.cssText = "padding:3px 0;cursor:pointer;";
        if (e.type === "file" && e.path === currentFile) li.style.color = "#22d3ee";
        li.onclick = function () {
          if (e.type === "dir") {
            cwd = e.path;
            loadTree();
          } else {
            openFile(e.path);
          }
        };
        ul.appendChild(li);
      });
    } catch (err) {
      writeLog("tree: " + err.message + "\n");
    }
  }

  async function openFile(path) {
    if (!repo) return;
    try {
      if (monacoEditor) {
        // auto-save previous
        try {
          await api("/sandbox/fs/write", "POST", {
            scope: scope, repo: repo, path: currentFile,
            content: monacoEditor.getValue(),
          });
        } catch (e) {}
      }
      var data = await api(
        "/sandbox/fs/read?scope=" + encodeURIComponent(scope) +
        "&repo=" + encodeURIComponent(repo) +
        "&path=" + encodeURIComponent(path)
      );
      currentFile = path;
      if (monacoEditor) {
        monacoEditor.setValue(data.content || "");
        try {
          monaco.editor.setModelLanguage(monacoEditor.getModel(), detectLang(path));
        } catch (e) {}
      }
      if (viewMode === "preview") showPreview(data.content || "");
      loadTree();
      writeLog("opened " + path + "\n");
    } catch (err) {
      writeLog("open: " + err.message + "\n");
    }
  }

  function showPreview(text) {
    var prev = $("codePreview");
    var mon = $("monacoContainer");
    if (!prev || !mon) return;
    prev.style.display = "block";
    mon.style.display = "none";
    prev.textContent = text;
  }

  function showEditor() {
    var prev = $("codePreview");
    var mon = $("monacoContainer");
    if (!prev || !mon) return;
    prev.style.display = "none";
    mon.style.display = "block";
    if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
  }

  function initMonaco() {
    var el = $("monacoContainer");
    if (!el) return;
    if (monacoEditor) {
      try { monacoEditor.layout(); } catch (e) {}
      return;
    }
    if (typeof require === "undefined") {
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco missing</p>";
      return;
    }
    require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" } });
    require(["vs/editor/editor.main"], function () {
      monacoEditor = monaco.editor.create(el, {
        value: "",
        language: "python",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
      });
    });
  }

  async function ensureDefaultRepo() {
    await refreshRepos();
    if (!repo) {
      var name = "demo";
      try {
        await api("/sandbox/repos", "POST", { name: name, scope: scope });
        repo = name;
        await refreshRepos();
        writeLog("created repo " + name + "\n");
      } catch (e) {
        writeLog("repo: " + e.message + "\n");
      }
    }
    await loadTree();
    // open main.py if present
    try {
      await openFile("main.py");
    } catch (e) {}
  }

  async function createRepo() {
    var name = prompt("Repo name:", "app");
    if (!name || !name.trim()) return;
    name = name.trim().replace(/\s+/g, "-");
    try {
      await api("/sandbox/repos", "POST", { name: name, scope: scope });
      repo = name;
      cwd = "";
      await refreshRepos();
      await loadTree();
      await openFile("main.py");
      writeLog("repo " + name + " ready\n");
    } catch (e) {
      writeLog("repo: " + e.message + "\n");
    }
  }

  async function saveFile() {
    if (!repo || !monacoEditor) {
      writeLog("nothing to save\n");
      return;
    }
    try {
      await api("/sandbox/fs/write", "POST", {
        scope: scope,
        repo: repo,
        path: currentFile,
        content: monacoEditor.getValue(),
      });
      writeLog("saved " + currentFile + "\n");
      await loadTree();
    } catch (e) {
      writeLog("save: " + e.message + "\n");
    }
  }

  async function newFile() {
    if (!repo) { writeLog("create a repo first\n"); return; }
    var name = prompt("File name (.py .js .html .css .md):", "app.py");
    if (!name || !name.trim()) return;
    name = name.trim();
    var path = cwd ? cwd + "/" + name : name;
    var ext = "";
    Object.keys(TEMPLATES).forEach(function (e) {
      if (path.toLowerCase().endsWith(e)) ext = e;
    });
    if (!ext) { path += ".py"; ext = ".py"; }
    try {
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: path, content: TEMPLATES[ext] || "",
      });
      currentFile = path;
      await loadTree();
      await openFile(path);
      writeLog("created " + path + "\n");
    } catch (e) {
      writeLog("file: " + e.message + "\n");
    }
  }

  async function newFolder() {
    if (!repo) { writeLog("create a repo first\n"); return; }
    var choice = prompt("1 = create folder\n2 = import from phone\n\n1 or 2:", "1");
    if (choice === "2") {
      var inp = $("folderPickerInput");
      if (inp) inp.click();
      return;
    }
    var name = prompt("Folder name:", "src");
    if (!name || !name.trim()) return;
    var path = cwd ? cwd + "/" + name.trim() : name.trim();
    try {
      await api("/sandbox/fs/mkdir", "POST", { scope: scope, repo: repo, path: path });
      cwd = path;
      await loadTree();
      writeLog("mkdir " + path + "\n");
    } catch (e) {
      writeLog("mkdir: " + e.message + "\n");
    }
  }

  async function onFolderPicked(ev) {
    var list = ev.target.files;
    if (!list || !list.length || !repo) return;
    var n = 0;
    for (var i = 0; i < list.length; i++) {
      await (function (file) {
        return new Promise(function (resolve) {
          var rel = file.webkitRelativePath || file.name;
          if (file.size > 400000) return resolve();
          var reader = new FileReader();
          reader.onload = async function () {
            try {
              await api("/sandbox/fs/write", "POST", {
                scope: scope, repo: repo, path: rel,
                content: String(reader.result || ""),
              });
              n++;
            } catch (e) {}
            resolve();
          };
          reader.readAsText(file);
        });
      })(list[i]);
    }
    writeLog("imported " + n + " files\n");
    await loadTree();
    ev.target.value = "";
  }

  async function importMemory() {
    if (!repo) { writeLog("create a repo first\n"); return; }
    writeLog("importing from /documents…\n");
    try {
      var docs = await api("/documents?limit=20");
      var rows = Array.isArray(docs) ? docs : (docs.items || docs.documents || []);
      if (!rows.length) {
        writeLog("no documents/artifacts found\n");
        return;
      }
      // nested picker screen via prompt for demo speed
      var names = rows.slice(0, 12).map(function (r, i) {
        return (i + 1) + ". " + (r.title || r.name || r.kind || r.id);
      }).join("\n");
      var pick = prompt("Import which document?\n" + names + "\n\nNumber:", "1");
      var idx = parseInt(pick, 10) - 1;
      if (isNaN(idx) || idx < 0 || idx >= rows.length) return;
      var row = rows[idx];
      var content = row.content || row.text || row.body || JSON.stringify(row, null, 2);
      var fname = "import_" + (row.id || Date.now()).toString().slice(0, 8) + ".md";
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: fname, content: String(content),
      });
      await loadTree();
      await openFile(fname);
      writeLog("imported → " + fname + "\n");
    } catch (e) {
      writeLog("import: " + e.message + "\n");
    }
  }

  async function pushRepo() {
    if (!repo) { writeLog("no repo\n"); return; }
    await saveFile();
    var msg = prompt("Push message:", "codespace snapshot") || "push";
    try {
      var data = await api("/sandbox/repos/" + encodeURIComponent(repo) + "/push", "POST", {
        scope: scope, repo: repo, message: msg,
      });
      writeLog("push ok · " + data.files + " files · " + (data.note || "") + "\n");
    } catch (e) {
      writeLog("push: " + e.message + "\n");
    }
  }

  function toggleView() {
    if (viewMode === "edit") {
      viewMode = "preview";
      var text = monacoEditor ? monacoEditor.getValue() : "";
      showPreview(text);
      writeLog("view: preview\n");
    } else {
      viewMode = "edit";
      showEditor();
      writeLog("view: editor\n");
    }
  }

  async function runActive() {
    if (!monacoEditor) {
      writeLog("editor not ready\n");
      return;
    }
    await saveFile();
    var source = monacoEditor.getValue();
    var lang = detectLang(currentFile);
    if (lang === "html" || lang === "css" || lang === "markdown") {
      writeLog("cannot execute " + lang + "\n");
      return;
    }
    if (lang === "typescript") lang = "javascript";
    if (lang === "shell") lang = "bash";
    if (lang === "plaintext") lang = "python";
    writeLog("$ run " + currentFile + "\n");
    try {
      var data = await api("/sandbox/run", "POST", {
        source: source,
        filename: currentFile.split("/").pop(),
        lang: lang,
        context: scope,
        repo: repo,
      });
      if (data.stdout) writeLog(data.stdout.replace(/\n?$/, "\n"));
      if (data.stderr) writeLog(data.stderr.replace(/\n?$/, "\n"));
      if (data.error) writeLog("ERROR: " + data.error + "\n");
      writeLog("[exit " + data.exit_code + " · " + data.backend + "]\n");
    } catch (e) {
      writeLog("run: " + e.message + "\n");
    }
  }

  async function onCmd(line) {
    line = (line || "").trim();
    if (!line) return;
    writeLog("$ " + line + "\n");
    var parts = line.split(/\s+/);
    var cmd = parts[0].toLowerCase();
    var arg = parts[1] || "";
    if (cmd === "help") {
      writeLog("pwd ls cd cat run clear help · toolbar: Repo File Folder Save Import View Push\n");
      return;
    }
    if (cmd === "clear") { log = ""; writeLog(""); return; }
    if (cmd === "pwd") { writeLog("/" + (repo || "") + "/" + cwd + "\n"); return; }
    if (cmd === "ls") { await loadTree(); writeLog("(tree refreshed)\n"); return; }
    if (cmd === "cd") {
      if (!arg || arg === "/") cwd = "";
      else if (arg === "..") {
        var p = cwd.split("/").filter(Boolean); p.pop(); cwd = p.join("/");
      } else cwd = cwd ? cwd + "/" + arg : arg;
      await loadTree();
      return;
    }
    if (cmd === "cat" && arg) {
      try {
        var data = await api(
          "/sandbox/fs/read?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(cwd ? cwd + "/" + arg : arg)
        );
        writeLog(data.content + (data.content.endsWith("\n") ? "" : "\n"));
      } catch (e) { writeLog(e.message + "\n"); }
      return;
    }
    if (cmd === "run") { await runActive(); return; }
    writeLog("unknown: " + cmd + "\n");
  }

  async function showPanel() {
    var panel = $("codePanel");
    if (!panel) return;
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    initMonaco();
    try {
      await ensureDefaultRepo();
    } catch (e) {
      writeLog("boot: " + e.message + "\n");
    }
    setTimeout(function () {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
      var input = $("consoleInput");
      if (input) input.focus();
    }, 150);
  }

  function bind() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");

    function wire(id, fn) {
      var el = $(id);
      if (el) el.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();
        fn();
      };
    }

    wire("btnCodeBack", nestedBack);
    wire("btnCloseCode", goHome);
    wire("btnRunCode", runActive);
    wire("btnNewRepo", createRepo);
    wire("btnNewFile", newFile);
    wire("btnNewFolder", newFolder);
    wire("btnSaveFile", saveFile);
    wire("btnImportMem", importMemory);
    wire("btnViewToggle", toggleView);
    wire("btnPushRepo", pushRepo);
    wire("btnHomeCode", showPanel);

    var sel = $("codeRepoSelect");
    if (sel) {
      sel.onchange = async function () {
        repo = sel.value || null;
        cwd = "";
        await loadTree();
        try { await openFile("main.py"); } catch (e) {}
      };
    }

    var input = $("consoleInput");
    if (input) {
      input.onkeydown = function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          var v = input.value;
          input.value = "";
          onCmd(v);
        }
      };
    }
    var out = $("codeOutput");
    if (out) out.onclick = function () { if (input) input.focus(); };

    var picker = $("folderPickerInput");
    if (picker) picker.onchange = onFolderPicked;

    writeLog("Codespace Phase 2 · type help\n");
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
