/**
 * Accodite Codespace P3
 * Layout: sidebar (closable) | Monaco | terminal ONE surface
 * No second $ input box. Caret lives on the active line.
 * Conventional roots: backend/ frontend/ public/ ...
 */
(function () {
  "use strict";


// ACCD-GSP-CLIENT
function acdIdentity() {
  var u = null;
  try { u = (typeof currentUser !== "undefined" && currentUser) || JSON.parse(localStorage.getItem("coMpaNeoN_user") || "null"); } catch (e) {}
  return {
    fullname: (u && (u.full_name || u.name)) || "",
    uid: (u && (u.phone || u.id || u.user_id)) || "",
  };
}


  var monacoEditor = null;
  var logLines = [];       // completed lines only
  var cmdBuf = "";         // current command being typed
  var scope = "user";
  var repo = null;
  var cwd = "";
  var currentFile = "backend/main.py";
  var sidebarOpen = true;
  var termCollapsed = false;
  var termFocused = false;
  var ROOT_SCAFFOLD = [
    "backend/main.py",
    "backend/__init__.py",
    "frontend/index.html",
    "frontend/js/app.js",
    "frontend/css/style.css",
    "public/index.html",
    "public/js/main.js",
    "public/css/main.css",
    "README.md",
  ];

  function $(id) { return document.getElementById(id); }

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    var token = (typeof authToken !== "undefined" && authToken) ||
                localStorage.getItem("coMpaNeoN_token") || "";
    if (token) h["Authorization"] = "Bearer " + token;
    return h;
  }

  function errText(e) {
    if (!e) return "unknown error";
    if (typeof e === "string") return e;
    if (e.message) return e.message;
    try { return JSON.stringify(e); } catch (x) { return String(e); }
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
    if (!res.ok) {
      var d = data.detail || data.error || data.message || data;
      throw new Error(typeof d === "string" ? d : JSON.stringify(d));
    }
    return data;
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
    if (n.endsWith(".json")) return "json";
    return "plaintext";
  }

  function paintTerm() {
    var out = $("codeOutput");
    if (!out) return;
    var caret = termFocused ? "█" : " ";
    var prompt = "$ ";
    var body = logLines.join("");
    out.innerHTML =
      '<span class="term-log">' + escapeHtml(body) + "</span>" +
      '<span class="term-line"><span style="color:#22d3ee">' + prompt + "</span>" +
      escapeHtml(cmdBuf) + '<span style="color:#22d3ee">' + caret + "</span></span>";
    out.scrollTop = out.scrollHeight;
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function writeLog(s) {
    logLines.push(s);
    if (logLines.length > 2000) logLines = logLines.slice(-1500);
    paintTerm();
  }

  function focusTerm() {
    termFocused = true;
    var out = $("codeOutput");
    if (out) out.focus();
    paintTerm();
  }

  function setSidebar(open) {
    sidebarOpen = open;
    var sb = $("codeSidebar");
    if (!sb) return;
    if (open) {
      sb.style.width = "180px";
      sb.style.flex = "0 0 180px";
      sb.style.marginLeft = "0";
      sb.style.display = "block";
    } else {
      sb.style.width = "0";
      sb.style.flex = "0 0 0";
      sb.style.marginLeft = "0";
      sb.style.display = "none";
    }
    if (monacoEditor) setTimeout(function () { try { monacoEditor.layout(); } catch (e) {} }, 160);
  }

  function setTermCollapsed(c) {
    termCollapsed = c;
    var cons = $("codeConsole");
    var btn = $("btnToggleTerm");
    if (!cons) return;
    if (c) {
      cons.style.flex = "0 0 28px";
      cons.style.minHeight = "28px";
      var out = $("codeOutput");
      if (out) out.style.display = "none";
      if (btn) btn.textContent = "Terminal ▸";
    } else {
      cons.style.flex = "0 0 28%";
      cons.style.minHeight = "100px";
      var out2 = $("codeOutput");
      if (out2) out2.style.display = "block";
      if (btn) btn.textContent = "Terminal ▾";
    }
    if (monacoEditor) setTimeout(function () { try { monacoEditor.layout(); } catch (e) {} }, 160);
  }

  /* ---------- tree (VS Code style) ---------- */
  function buildTree(entries) {
    // entries: [{name, path, type}]
    var root = {};
    (entries || []).forEach(function (e) {
      var parts = e.path.split("/").filter(Boolean);
      var node = root;
      parts.forEach(function (part, i) {
        var last = i === parts.length - 1;
        if (!node[part]) {
          node[part] = { __meta: { name: part, path: parts.slice(0, i + 1).join("/"), type: last ? e.type : "dir", children: {} } };
        }
        if (!last) {
          node[part].__meta.type = "dir";
          node = node[part].__meta.children;
        }
      });
    });
    return root;
  }

  function renderNode(container, nodeMap, depth) {
    Object.keys(nodeMap).sort().forEach(function (key) {
      var meta = nodeMap[key].__meta;
      var row = document.createElement("div");
      row.style.cssText = "padding:2px 0 2px " + (depth * 10) + "px; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;";
      if (meta.type === "dir") {
        row.textContent = "📁 " + meta.name;
        row.onclick = function (ev) {
          ev.stopPropagation();
          var kid = row.nextSibling;
          if (kid && kid.dataset && kid.dataset.folder === meta.path) {
            kid.style.display = kid.style.display === "none" ? "block" : "none";
          }
        };
        container.appendChild(row);
        var wrap = document.createElement("div");
        wrap.dataset.folder = meta.path;
        container.appendChild(wrap);
        renderNode(wrap, meta.children, depth + 1);
      } else {
        row.textContent = "📄 " + meta.name;
        if (meta.path === currentFile) row.style.color = "#22d3ee";
        row.onclick = function (ev) {
          ev.stopPropagation();
          openFile(meta.path);
        };
        container.appendChild(row);
      }
    });
  }

  async function loadTree() {
    var box = $("codeFileTree");
    if (!box) return;
    box.innerHTML = "";
    if (!repo) {
      box.innerHTML = "<div style='opacity:0.5'>No repo</div>";
      return;
    }
    try {
      // recursive list by walking — use flat list from root and nested
      var all = [];
      async function walk(path) {
        var data = await api(
          "/sandbox/fs/list?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(path || "")
        );
        (data.entries || []).forEach(function (e) {
          all.push(e);
          if (e.type === "dir") {
            // schedule nested — sequential
          }
        });
        for (var i = 0; i < (data.entries || []).length; i++) {
          var e = data.entries[i];
          if (e.type === "dir") await walk(e.path);
        }
      }
      await walk("");
      var tree = buildTree(all);
      renderNode(box, tree, 0);
      if (!all.length) box.innerHTML = "<div style='opacity:0.5'>Empty — use + File</div>";
    } catch (err) {
      writeLog("tree: " + errText(err) + "\n");
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
      el.innerHTML = "<p style='color:#f87171;padding:1rem'>Monaco missing — hard refresh</p>";
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

  async function openFile(path) {
    if (!repo || !path) return;
    try {
      if (monacoEditor && currentFile) {
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
      loadTree();
      // only log once per open
      writeLog("opened " + path + "\n");
    } catch (err) {
      writeLog("open: " + errText(err) + "\n");
    }
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

  async function scaffoldRepo(name) {
    // Conventional app roots
    for (var i = 0; i < ROOT_SCAFFOLD.length; i++) {
      var path = ROOT_SCAFFOLD[i];
      var body = "";
      if (path.endsWith("main.py") || path.endsWith("__init__.py")) {
        body = path.indexOf("__init__") >= 0 ? "" : '# ' + name + '\nprint("Hello from ' + name + '")\n';
      } else if (path.endsWith(".html")) {
        body = "<!DOCTYPE html>\n<html><head><title>" + name + "</title></head><body><h1>" + name + "</h1></body></html>\n";
      } else if (path.endsWith(".js")) {
        body = "// " + path + "\nconsole.log('ok');\n";
      } else if (path.endsWith(".css")) {
        body = "/* " + path + " */\nbody { margin: 0; }\n";
      } else if (path.endsWith(".md")) {
        body = "# " + name + "\n\nAccodite Codespace repo.\n";
      }
      try {
        await api("/sandbox/fs/write", "POST", {
          scope: scope, repo: name, path: path, content: body,
        });
      } catch (e) {}
    }
  }

  async function createRepo() {
    var name = prompt("Repo name:", "app");
    if (!name || !name.trim()) return;
    name = name.trim().replace(/\s+/g, "-");
    try {
      var idn = acdIdentity(); await api("/sandbox/repos", "POST", { name: name, scope: scope, fullname: idn.fullname, uid: String(idn.uid) });
    } catch (e) {
      // if exists, still scaffold / use it
      if (String(e.message || e).indexOf("already") < 0) {
        writeLog("repo: " + errText(e) + "\n");
        return;
      }
    }
    repo = name;
    await scaffoldRepo(name);
    await refreshRepos();
    await loadTree();
    await openFile("backend/main.py");
    writeLog("repo " + name + " ready (backend/ frontend/ public/)\n");
    if (typeof showRepoGsp === "function") await showRepoGsp(name);
  }

  async function ensureDefaultRepo() {
    await refreshRepos();
    if (!repo) {
      try {
        await api("/sandbox/repos", "POST", { name: "demo", scope: scope });
      } catch (e) {}
      repo = "demo";
      await scaffoldRepo("demo");
      await refreshRepos();
    }
    await loadTree();
    // prefer backend/main.py
    try {
      await openFile("backend/main.py");
    } catch (e) {
      try { await openFile("main.py"); } catch (e2) {}
    }
  }

  async function saveFile() {
    if (!repo || !monacoEditor) return;
    try {
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: currentFile,
        content: monacoEditor.getValue(),
      });
      writeLog("saved " + currentFile + "\n");
      await loadTree();
    } catch (e) {
      writeLog("save: " + errText(e) + "\n");
    }
  }

  async function newFile() {
    if (!repo) { writeLog("create a repo first\n"); return; }
    var name = prompt("Path (e.g. backend/api.py, public/js/x.js):", "backend/app.py");
    if (!name || !name.trim()) return;
    var path = name.trim().replace(/^\/+/, "");
    var ext = path.includes(".") ? "." + path.split(".").pop() : ".py";
    var body = "";
    if (ext === ".py") body = 'print("ok")\n';
    else if (ext === ".js") body = 'console.log("ok");\n';
    else if (ext === ".html") body = "<!DOCTYPE html>\n<html><body></body></html>\n";
    else if (ext === ".css") body = "body { margin: 0; }\n";
    try {
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: path, content: body,
      });
      currentFile = path;
      await loadTree();
      await openFile(path);
    } catch (e) {
      writeLog("file: " + errText(e) + "\n");
    }
  }

  async function newFolder() {
    if (!repo) return;
    var name = prompt("Folder path (e.g. backend/api, public/assets):", "backend/api");
    if (!name || !name.trim()) return;
    var path = name.trim().replace(/^\/+/, "");
    try {
      await api("/sandbox/fs/mkdir", "POST", { scope: scope, repo: repo, path: path });
      // placeholder so tree shows
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: path + "/.keep", content: "",
      });
      await loadTree();
      writeLog("mkdir " + path + "\n");
    } catch (e) {
      writeLog("mkdir: " + errText(e) + "\n");
    }
  }

  async function pushRepo() {
    if (!repo) return;
    await saveFile();
    try {
      var data = await api("/sandbox/repos/" + encodeURIComponent(repo) + "/push", "POST", {
        scope: scope, repo: repo, message: "codespace snapshot",
      });
      writeLog("push ok · " + (data.files || 0) + " files\n");
    } catch (e) {
      writeLog("push: " + errText(e) + "\n");
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
    if (lang === "html" || lang === "css" || lang === "markdown" || lang === "json") {
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
      writeLog("[exit " + data.exit_code + " · " + (data.backend || "?") + "]\n");
    } catch (e) {
      writeLog("run: " + errText(e) + "\n");
    }
  }

  async function onCommand(line) {
    line = (line || "").trim();
    if (!line) return;
    writeLog("$ " + line + "\n");
    var parts = line.split(/\s+/);
    var cmd = parts[0].toLowerCase();
    var arg = parts.slice(1).join(" ");

    if (cmd === "help") {
      writeLog("pwd  ls  cd  cat  run  clear  help  mkdir  touch\n");
      return;
    }
    if (cmd === "clear") {
      logLines = [];
      paintTerm();
      return;
    }
    if (cmd === "pwd") {
      writeLog("/" + (repo || "") + (cwd ? "/" + cwd : "") + "\n");
      return;
    }
    if (cmd === "ls") {
      try {
        var data = await api(
          "/sandbox/fs/list?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(cwd || "")
        );
        var names = (data.entries || []).map(function (e) {
          return e.type === "dir" ? e.name + "/" : e.name;
        });
        writeLog((names.join("  ") || "(empty)") + "\n");
      } catch (e) {
        writeLog(errText(e) + "\n");
      }
      return;
    }
    if (cmd === "cd") {
      if (!arg || arg === "/") cwd = "";
      else if (arg === "..") {
        var p = cwd.split("/").filter(Boolean);
        p.pop();
        cwd = p.join("/");
      } else {
        cwd = cwd ? cwd + "/" + arg.replace(/^\/+/, "") : arg.replace(/^\/+/, "");
      }
      writeLog("");
      return;
    }
    if (cmd === "cat" && arg) {
      var path = cwd ? cwd + "/" + arg : arg;
      try {
        var data = await api(
          "/sandbox/fs/read?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(path)
        );
        writeLog(data.content + (String(data.content).endsWith("\n") ? "" : "\n"));
      } catch (e) {
        writeLog(errText(e) + "\n");
      }
      return;
    }
    if (cmd === "run") {
      if (arg) {
        var rp = cwd ? cwd + "/" + arg : arg;
        await openFile(rp);
      }
      await runActive();
      return;
    }
    if (cmd === "mkdir" && arg) {
      var mp = cwd ? cwd + "/" + arg : arg;
      try {
        await api("/sandbox/fs/mkdir", "POST", { scope: scope, repo: repo, path: mp });
        await api("/sandbox/fs/write", "POST", { scope: scope, repo: repo, path: mp + "/.keep", content: "" });
        await loadTree();
        writeLog("mkdir " + mp + "\n");
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    if (cmd === "touch" && arg) {
      var tp = cwd ? cwd + "/" + arg : arg;
      try {
        await api("/sandbox/fs/write", "POST", { scope: scope, repo: repo, path: tp, content: "" });
        await loadTree();
        writeLog("touch " + tp + "\n");
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    writeLog("unknown: " + cmd + " (try help)\n");
  }

  function onTermKey(e) {
    if (!termFocused) return;
    if (e.key === "Enter") {
      e.preventDefault();
      var line = cmdBuf;
      cmdBuf = "";
      paintTerm();
      onCommand(line);
      return;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      cmdBuf = cmdBuf.slice(0, -1);
      paintTerm();
      return;
    }
    if (e.key === "Escape") {
      cmdBuf = "";
      paintTerm();
      return;
    }
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      cmdBuf += e.key;
      paintTerm();
    }
  }

  function goHome() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
    if (typeof window.acdGoHomeStrict === "function") window.acdGoHomeStrict();
  }

  async function showPanel() {
    var panel = $("codePanel");
    if (!panel) return;
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    setSidebar(true);
    setTermCollapsed(false);
    initMonaco();
    try {
      await ensureDefaultRepo();
    } catch (e) {
      writeLog("boot: " + errText(e) + "\n");
    }
    setTimeout(function () {
      if (monacoEditor) try { monacoEditor.layout(); } catch (e) {}
      focusTerm();
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

    wire("btnCodeBack", goHome);
    wire("btnCloseCode", goHome);
    wire("btnRunCode", runActive);
    wire("btnNewRepo", createRepo);
    wire("btnNewFile", newFile);
    wire("btnNewFolder", newFolder);
    wire("btnSaveFile", saveFile);
    wire("btnPushRepo", pushRepo);
    wire("btnToggleSidebar", function () { setSidebar(!sidebarOpen); });
    wire("btnCloseSidebar", function () { setSidebar(false); });
    wire("btnToggleTerm", function () { setTermCollapsed(!termCollapsed); });
    wire("btnHomeCode", showPanel);

    var sel = $("codeRepoSelect");
    if (sel) {
      sel.onchange = async function () {
        repo = sel.value || null;
        cwd = "";
        await loadTree();
        try { await openFile("backend/main.py"); } catch (e) {}
      };
    }

    var out = $("codeOutput");
    if (out) {
      out.addEventListener("click", focusTerm);
      out.addEventListener("focus", function () { termFocused = true; paintTerm(); });
      out.addEventListener("blur", function () { termFocused = false; paintTerm(); });
    }
    document.addEventListener("keydown", function (e) {
      var panel = $("codePanel");
      if (!panel || panel.style.display === "none") return;
      // don't steal keys from Monaco
      var ae = document.activeElement;
      if (ae && (ae.closest && ae.closest(".monaco-editor"))) return;
      if (ae && (ae.tagName === "INPUT" || ae.tagName === "TEXTAREA" || ae.tagName === "SELECT")) return;
      if (!termFocused && e.target !== out) return;
      onTermKey(e);
    });

    writeLog("Codespace ready · click terminal · type help\n");
    paintTerm();
  }

  

  // ACCD-GSP-SHOW
  async function showRepoGsp(name) {
    try {
      var g = await api("/sandbox/repos/" + encodeURIComponent(name) + "/gsp?scope=" + encodeURIComponent(scope));
      writeLog("GSP start_row=" + g.start_row + " root=" + g.root_key +
        " splits=" + (g.splits || []).map(function (s) { return "k" + s.k + "@(" + s.row + "," + s.col + ")"; }).join(" ") + "\n");
    } catch (e) {}
  }
  window.acdShowRepoGsp = showRepoGsp;

  window.openCodePanel = showPanel;
  window.closeCodePanel = goHome;
  window.hideCodeScreen = goHome;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();


// ============================================================
// ACCD-GSP-UID-EOF — start_row only; name + repo_uid for push/commit
// ============================================================
(function () {
  function patchCreate() {
    if (typeof window.createRepo === "function" || false) return;
  }
  // Wrap fetch-free: hook acdOnRepoCreated after any success path that sets window.__lastRepoCreate
  var _fetch = window.fetch;
  if (_fetch && !window.__acdGspFetchPatched) {
    window.__acdGspFetchPatched = true;
    window.fetch = async function (url, opts) {
      var res = await _fetch.apply(this, arguments);
      try {
        var u = String(url || "");
        if (u.indexOf("/sandbox/repos") >= 0 && (!opts || (opts.method || "GET").toUpperCase() === "POST") && u.indexOf("/push") < 0 && u.indexOf("/commit") < 0) {
          var clone = res.clone();
          clone.json().then(function (data) {
            if (data && data.repo_uid && typeof window.acdOnRepoCreated === "function") {
              window.acdOnRepoCreated(data);
            }
          }).catch(function () {});
        }
      } catch (e) {}
      return res;
    };
  }
})();
