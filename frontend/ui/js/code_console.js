/**
 * Accodite Codespace P4
 * - Terminal: tap surface → ghost input (mobile keyboard)
 * - ▶ Run = editor file · ▶ Term = terminal line or re-run file
 * - create path/repo silent · open path swaps Monaco instantly
 * - repos listed as folders in Explorer
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var logLines = [];
  var cmdBuf = "";
  var scope = "user";
  var repo = null;
  var cwd = "";
  var currentFile = "";
  var sidebarOpen = true;
  var termCollapsed = false;
  var termFocused = false;
  var lastRunPath = "";
  var termCtrlOn = false;
  var termAltOn = false;

  // ACCD-T1-TERM-STATUS — terminal status/sector/eof only (GSP start_row untouched)
  var currentSector = "CODING";
  try { currentSector = sessionStorage.getItem("acd_term_sector") || "CODING"; } catch (e) {}
  var eofMode = false;
  var eofLines = [];
  var eofTargetPath = "";


  var _repoUids = {};
  try { _repoUids = JSON.parse(sessionStorage.getItem("acd_repo_uids") || "{}"); } catch (e) {}

  function $(id) { return document.getElementById(id); }

  function saveRepoUid(name, uid) {
    if (!name || !uid) return;
    _repoUids[name] = uid;
    try { sessionStorage.setItem("acd_repo_uids", JSON.stringify(_repoUids)); } catch (e) {}
  }
  function getRepoUid(name) { return _repoUids[name] || ""; }

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

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function paintTerm() {
    var out = $("codeOutput");
    if (!out) return;
    var nearBottom = (out.scrollHeight - out.scrollTop - out.clientHeight) < 56;
    var caret = termFocused ? "█" : "▌";
    out.innerHTML =
      '<span class="term-log">' + escapeHtml(logLines.join("")) + "</span>" +
      '<span class="term-line"><span style="color:#22d3ee">$ </span>' +
      escapeHtml(cmdBuf) + '<span class="term-caret" style="color:#22d3ee">' + caret + '</span></span>';
    if (nearBottom) out.scrollTop = out.scrollHeight;
  }

  function writeLog(s) {
    logLines.push(s);
    if (logLines.length > 2000) logLines = logLines.slice(-1500);
    paintTerm();
  }

  function focusTerm() {
    termFocused = true;
    // ACCD-FOCUS-PAINT
    paintTerm();
    var ghost = $("termGhostInput");
    if (ghost) {
      try { ghost.focus({ preventScroll: true }); } catch (e) { try { ghost.focus(); } catch (e2) {} }
      setTimeout(function () {
        try { ghost.focus(); } catch (e) {}
      }, 50);
    }
    var out = $("codeOutput");
    if (out) out.classList.add("term-focused");
    paintTerm();
  }

  function blurTerm() {
    termFocused = false;
    var out = $("codeOutput");
    if (out) out.classList.remove("term-focused");
    paintTerm();
  }

  function ensureGhostInput() {
    var cons = $("codeConsole");
    if (!cons || $("termGhostInput")) return;
    var inp = document.createElement("input");
    inp.id = "termGhostInput";
    inp.type = "text";
    inp.autocomplete = "off";
    inp.autocapitalize = "off";
    inp.spellcheck = false;
    inp.setAttribute("inputmode", "text");
    inp.setAttribute("enterkeyhint", "go");
    inp.style.cssText = "position:absolute;left:0;right:0;bottom:0;height:36px;opacity:0.02;border:0;padding:0;margin:0;z-index:5;width:100%;background:transparent;color:transparent;caret-color:transparent;font-size:16px;";
    cons.style.position = "relative";
    cons.appendChild(inp);

    inp.addEventListener("focus", function () { termFocused = true; paintTerm(); });
    inp.addEventListener("blur", function () {
      setTimeout(function () {
        if (document.activeElement !== inp) blurTerm();
      }, 80);
    });
    inp.addEventListener("input", function () { cmdBuf = inp.value; paintTerm(); });
    inp.addEventListener("keydown", function (e) {
      // T1 hotkeys — do not alter repo_uid / start_row
      if (e.ctrlKey && e.shiftKey && (e.key === "S" || e.key === "s")) {
        e.preventDefault(); printStatus(); return;
      }
      if (e.ctrlKey && e.shiftKey && (e.key === "H" || e.key === "h")) {
        e.preventDefault(); printHelp(); return;
      }
      if (e.ctrlKey && e.altKey && (e.key === "T" || e.key === "t")) {
        e.preventDefault(); toggleSector(); return;
      }
      if (e.ctrlKey && e.shiftKey && (e.key === "C" || e.key === "c")) {
        e.preventDefault(); beginEofStream(""); return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        var line = cmdBuf;
        cmdBuf = "";
        inp.value = "";
        paintTerm();
        onCommand(line);
      } else if (e.key === "Escape") {
        if (eofMode) {
          eofMode = false; eofLines = []; eofTargetPath = "";
          writeLog("[eof] cancelled\n");
        }
        cmdBuf = "";
        inp.value = "";
        paintTerm();
      }
    });
  }

  function setSidebar(open) {
    sidebarOpen = open;
    var sb = $("codeSidebar");
    if (!sb) return;
    if (open) {
      sb.style.display = "block";
      sb.style.width = "180px";
      sb.style.flex = "0 0 180px";
    } else {
      sb.style.display = "none";
      sb.style.width = "0";
      sb.style.flex = "0 0 0";
    }
    layoutEditor();
  }

  function setTermCollapsed(c) {
    termCollapsed = c;
    var cons = $("codeConsole");
    var btn = $("btnToggleTerm");
    var out = $("codeOutput");
    var bar = $("termActionBar");
    if (!cons) return;
    if (c) {
      cons.style.flex = "0 0 32px";
      cons.style.minHeight = "32px";
      if (out) out.style.display = "none";
      if (bar) bar.style.display = "none";
      if (btn) btn.textContent = "Terminal ▸";
    } else {
      cons.style.flex = "0 0 30%";
      cons.style.minHeight = "120px";
      if (out) out.style.display = "block";
      if (bar) bar.style.display = "flex";
      if (btn) btn.textContent = "Terminal ▾";
    }
    layoutEditor();
  }

  function layoutEditor() {
    if (monacoEditor) setTimeout(function () {
      try { monacoEditor.layout(); } catch (e) {}
    }, 120);
  }

  function buildTree(entries) {
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
      row.style.cssText = "padding:3px 0 3px " + (depth * 10) + "px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
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
        if (meta.path === currentFile) {
          row.style.color = "#22d3ee";
          row.style.fontWeight = "600";
        }
        row.onclick = function (ev) {
          ev.stopPropagation();
          openFile(meta.path, { silent: true });
        };
        container.appendChild(row);
      }
    });
  }


  // ACCD-REPO-PATH-SCOPE
  // All FS paths are relative to active repo. Relative segments append to cwd.
  function requireRepo() {
    if (!repo) {
      writeLog("no active repo — create/open one in Explorer (each repo has its own tree)\n");
      return false;
    }
    return true;
  }

  function normalizeRel(path) {
    path = String(path || "").replace(/\\/g, "/").replace(/^\/+/, "");
    var parts = [];
    path.split("/").forEach(function (seg) {
      if (!seg || seg === ".") return;
      if (seg === "..") {
        if (parts.length) parts.pop();
        return;
      }
      parts.push(seg);
    });
    return parts.join("/");
  }

  /** Resolve user path against active repo + cwd. Never crosses repos. */
  function resolvePath(userPath) {
    userPath = String(userPath || "").trim();
    if (!userPath || userPath === ".") return cwd || "";
    // absolute-within-repo
    if (userPath.startsWith("/") || userPath.startsWith("\~/")) {
      return normalizeRel(userPath.replace(/^\~/, ""));
    }
    // relative → append under cwd
    var base = cwd || "";
    return normalizeRel(base ? base + "/" + userPath : userPath);
  }

  function setCwd(rel) {
    cwd = normalizeRel(rel || "");
  }

  async function loadTree() {
    var box = $("codeFileTree");
    if (!box) return;
    box.innerHTML = "";

    var repoWrap = document.createElement("div");
    var title = document.createElement("div");
    title.style.cssText = "opacity:0.55;margin-bottom:4px;font-size:11px;";
    title.textContent = "REPOS";
    repoWrap.appendChild(title);

    try {
      var data = await api("/sandbox/repos?scope=" + encodeURIComponent(scope));
      var repos = data.repos || [];
      if (!repos.length) {
        var empty = document.createElement("div");
        empty.style.opacity = "0.5";
        empty.textContent = "No repos — + Repo";
        repoWrap.appendChild(empty);
      }
      repos.forEach(function (r) {
        var row = document.createElement("div");
        row.style.cssText = "padding:4px 0;cursor:pointer;";
        var active = r.name === repo;
        row.innerHTML = (active ? "📂 " : "📁 ") +
          "<span style='" + (active ? "color:#22d3ee;font-weight:600" : "") + "'>" +
          escapeHtml(r.name) + "</span>" +
          (r.start_row != null ? " <span style='opacity:0.45;font-size:10px'>r" + r.start_row + "</span>" : "");
        row.onclick = async function () {
          if (repo === r.name) return;
          repo = r.name;
          cwd = "";
          currentFile = "";
          var sel = $("codeRepoSelect");
          if (sel) sel.value = repo;
          await loadTree();
          try { await openFile("backend/main.py", { silent: true }); }
          catch (e) { try { await openFile("main.py", { silent: true }); } catch (e2) {} }
        };
        repoWrap.appendChild(row);
      });
    } catch (e) {}
    box.appendChild(repoWrap);
    if (!repo) return;

    var filesTitle = document.createElement("div");
    filesTitle.style.cssText = "opacity:0.55;margin:8px 0 4px;font-size:11px;";
    filesTitle.textContent = "FILES · " + repo;
    box.appendChild(filesTitle);

    try {
      var all = [];
      async function walk(path) {
        var data = await api(
          "/sandbox/fs/list?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(path || "")
        );
        for (var i = 0; i < (data.entries || []).length; i++) {
          var e = data.entries[i];
          if (e.name === ".git" || (e.path && e.path.split("/")[0] === ".git")) continue;
          all.push(e);
          if (e.type === "dir") await walk(e.path);
        }
      }
      await walk("");
      var treeRoot = document.createElement("div");
      box.appendChild(treeRoot);
      renderNode(treeRoot, buildTree(all), 0);
    } catch (err) {}
  }

  function initMonaco() {
    var el = $("monacoContainer");
    if (!el) return;
    if (monacoEditor) { layoutEditor(); return; }
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

  async function openFile(path, opts) {
    opts = opts || {};
    if (!repo || !path) return;
    try {
      if (monacoEditor && currentFile && currentFile !== path) {
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
      lastRunPath = path;
      if (monacoEditor) {
        monacoEditor.setValue(data.content || "");
        try {
          monaco.editor.setModelLanguage(monacoEditor.getModel(), detectLang(path));
        } catch (e) {}
        layoutEditor();
      }
      var tab = $("codeActivePath");
      if (tab) tab.textContent = repo + " / " + path;
      await loadTree();
      if (!opts.silent) writeLog("opened " + path + "\n");
    } catch (err) {
      if (!opts.silent) writeLog("open: " + errText(err) + "\n");
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
      o.textContent = r.name + (r.start_row != null ? " · r" + r.start_row : "");
      sel.appendChild(o);
    });
    if (!repo || !repos.find(function (r) { return r.name === repo; })) repo = repos[0].name;
    sel.value = repo;
  }

  async function createRepo() {
    var name = prompt("Repo name:", "app");
    if (!name || !name.trim()) return;
    name = name.trim().replace(/\s+/g, "-");
    try {
      var created = await api("/sandbox/repos", "POST", { name: name, scope: scope });
      repo = name;
      if (created.repo_uid) {
        saveRepoUid(name, created.repo_uid);
        writeLog("repo_uid (save): " + created.repo_uid + " · start_row=" + created.start_row + "\n");
      }
      if (typeof window.acdOnRepoCreated === "function") window.acdOnRepoCreated(created);
      await refreshRepos();
      await loadTree();
      try { await openFile("backend/main.py", { silent: true }); }
      catch (e) { try { await openFile("main.py", { silent: true }); } catch (e2) {} }
    } catch (e) {
      writeLog("repo: " + errText(e) + "\n");
    }
  }

  async function saveFile() {
    if (!repo || !monacoEditor || !currentFile) return;
    try {
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: currentFile,
        content: monacoEditor.getValue(),
      });
    } catch (e) {
      writeLog("save: " + errText(e) + "\n");
    }
  }

  async function newFile() {
    if (!repo) { writeLog("select or create a repo first\n"); return; }
    var name = prompt("Path (e.g. backend/api.py):", "backend/app.py");
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
      await openFile(path, { silent: true });
    } catch (e) {
      writeLog("file: " + errText(e) + "\n");
    }
  }

  async function newFolder() {
    if (!repo) return;
    var name = prompt("Folder path (e.g. backend/api):", "backend/api");
    if (!name || !name.trim()) return;
    var path = name.trim().replace(/^\/+/, "");
    try {
      await api("/sandbox/fs/mkdir", "POST", { scope: scope, repo: repo, path: path });
      await api("/sandbox/fs/write", "POST", {
        scope: scope, repo: repo, path: path + "/.keep", content: "",
      });
      await loadTree();
    } catch (e) {
      writeLog("mkdir: " + errText(e) + "\n");
    }
  }

  async function pushRepo() {
    if (!repo) return;
    await saveFile();
    var key = getRepoUid(repo) || prompt("repo_uid for " + repo + ":", "");
    if (!key) { writeLog("push needs repo_uid\n"); return; }
    saveRepoUid(repo, key);
    var msg = prompt("Push message:", "codespace snapshot") || "push";
    try {
      var data = await api("/sandbox/repos/" + encodeURIComponent(repo) + "/push", "POST", {
        scope: scope, repo: repo, repo_uid: key, message: msg,
      });
      writeLog("push ok · start_row=" + (data.start_row || "?") + "\n");
    } catch (e) {
      writeLog("push: " + errText(e) + "\n");
    }
  }

  async function runEditor() {
    if (!monacoEditor) { writeLog("editor not ready\n"); return; }
    if (!currentFile) { writeLog("open a file first\n"); return; }
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
    lastRunPath = currentFile;
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

  async function runTerminal() {
    if (cmdBuf && cmdBuf.trim()) {
      var line = cmdBuf.trim();
      cmdBuf = "";
      var ghost = $("termGhostInput");
      if (ghost) ghost.value = "";
      paintTerm();
      await onCommand(line);
      return;
    }
    await runEditor();
  }


  function gspStartRowReadOnly() {
    // DISPLAY ONLY — does not recompute or rewrite repo_uid / start_row assignment.
    // Uses values already returned by backend / stored for this repo.
    var name = repo || "";
    var uid = getRepoUid(name) || "";
    return { repo: name, repo_uid: uid, note: "start_row from server on create; not recalculated here" };
  }

  function printStatus() {
    var g = gspStartRowReadOnly();
    writeLog("--- status ---\n");
    writeLog("sector   : " + currentSector + "\n");
    writeLog("scope    : " + scope + "\n");
    writeLog("repo     : " + (g.repo || "(none)") + "\n");
    writeLog("repo_uid : " + (g.repo_uid || "(none)") + "\n");
    writeLog("cwd      : /" + (repo || "") + (cwd ? "/" + cwd : "") + "\n");
    writeLog("file     : " + (currentFile || "(none)") + "\n");
    writeLog("note     : " + g.note + "\n");
  }

  function printHelp() {
    writeLog(
      "pwd ls cd cat run clear help mkdir touch status sector eof\n" +
      "key <uid>  push|commit [msg]\n" +
      "git|pip|npm|curl via network exec\n" +
      "hotkeys (term focus): Ctrl+Shift+S status · Ctrl+Shift+H help\n" +
      "  Ctrl+Alt+T sector · Ctrl+Shift+C eof stream\n" +
      "eof: type 'eof [path]' then lines, then EOF alone to write\n"
    );
  }

  function toggleSector() {
    var sectors = ["CODING", "LAW", "HEALTH"];
    var i = sectors.indexOf(currentSector);
    if (i < 0) i = 0;
    currentSector = sectors[(i + 1) % sectors.length];
    try { sessionStorage.setItem("acd_term_sector", currentSector); } catch (e) {}
    writeLog("[sector] " + currentSector + "\n");
  }

  async function finishEofStream() {
    var body = eofLines.join("\n");
    var path = eofTargetPath || (cwd ? cwd + "/COMMIT.txt" : "COMMIT.txt");
    eofMode = false;
    eofLines = [];
    eofTargetPath = "";
    if (!repo) {
      writeLog("eof: open/create a repo first (GSP uid unchanged)\n");
      return;
    }
    try {
      await api("/sandbox/fs/write", "POST", {
        scope: scope,
        repo: repo,
        path: path,
        content: body
      });
      writeLog("[eof] wrote " + path + " (" + body.length + " bytes) sector=" + currentSector + "\n");
      if (typeof loadTree === "function") try { await loadTree(); } catch (e) {}
      try { await openFile(path, { silent: true }); } catch (e) {}
    } catch (e) {
      writeLog("eof: " + errText(e) + "\n");
    }
  }

  function beginEofStream(arg) {
    eofMode = true;
    eofLines = [];
    eofTargetPath = (arg || "").trim();
    writeLog("[eof] enter payload; line with only EOF ends stream\n");
    if (eofTargetPath) writeLog("[eof] target path: " + eofTargetPath + "\n");
  }

  async function onCommand(line) {
    line = (line || "").trim();
    if (!line) return;
    writeLog("$ " + line + "\n");
    var parts = line.split(/\s+/);
    var cmd = parts[0].toLowerCase();
    var arg = parts.slice(1).join(" ");

    if (typeof window.acdGspTermCommand === "function") {
      var handled = await window.acdGspTermCommand(cmd, parts, {
        repo: repo, scope: scope, api: api, writeLog: writeLog, errText: errText, arg: arg
      });
      if (handled) return;
    }

    // T1 commands (no GSP/repo_uid mutation)
    if (eofMode) {
      if (line === "EOF" || line === "eof") {
        await finishEofStream();
      } else {
        eofLines.push(line);
        writeLog("| " + line + "\n");
      }
      return;
    }
    if (cmd === "help") {
      printHelp();
      return;
    }
    if (cmd === "status") {
      printStatus();
      return;
    }
    if (cmd === "sector") {
      if (arg) {
        var up = arg.trim().toUpperCase();
        if (["CODING", "LAW", "HEALTH"].indexOf(up) >= 0) {
          currentSector = up;
          try { sessionStorage.setItem("acd_term_sector", currentSector); } catch (e) {}
          writeLog("[sector] " + currentSector + "\n");
        } else {
          writeLog("sector: use CODING | LAW | HEALTH\n");
        }
      } else {
        toggleSector();
      }
      return;
    }
    if (cmd === "eof" || cmd === "commitstream") {
      beginEofStream(arg);
      return;
    }
    if (cmd === "clear") { logLines = []; paintTerm(); return; }
    if (cmd === "pwd") {
      if (!repo) { writeLog("no active repo\n"); return; }
      writeLog("/" + repo + (cwd ? "/" + cwd : "") + "\n");
      return;
    }
    if (cmd === "ls") {
      if (!requireRepo()) return;
      var listPath = arg ? resolvePath(arg) : (cwd || "");
      try {
        var data = await api(
          "/sandbox/fs/list?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(listPath)
        );
        var names = (data.entries || []).filter(function (e) {
          return e.name !== ".git";
        }).map(function (e) {
          return e.type === "dir" ? e.name + "/" : e.name;
        });
        writeLog((names.join("  ") || "(empty)") + "\n");
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    if (cmd === "cd") {
      if (!requireRepo()) return;
      if (!arg || arg === "/" || arg === "\~") {
        setCwd("");
        writeLog("/" + repo + "\n");
        return;
      }
      if (arg === "..") {
        var parts = (cwd || "").split("/").filter(Boolean);
        parts.pop();
        setCwd(parts.join("/"));
        writeLog("/" + repo + (cwd ? "/" + cwd : "") + "\n");
        return;
      }
      var target = resolvePath(arg);
      try {
        var st = await api(
          "/sandbox/fs/list?scope=" + encodeURIComponent(scope) +
          "&repo=" + encodeURIComponent(repo) +
          "&path=" + encodeURIComponent(target)
        );
        if (st.type === "file") {
          writeLog("not a directory: " + target + "\n");
          return;
        }
        setCwd(target);
        writeLog("/" + repo + (cwd ? "/" + cwd : "") + "\n");
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    
    
    if (cmd === "gitimport" || cmd === "pullgh") {
      if (!requireRepo()) return;
      var url = arg || "https://github.com/TheGuru-main/CoMpaNeoNAccodite1.git";
      var line = "git init && git remote remove origin 2>/dev/null; git remote add origin " + url +
        " && git fetch --depth 1 origin main && git checkout -f -B main FETCH_HEAD";
      writeLog("$ gitimport force checkout over scaffold\n");
      try {
        var data = await api("/sandbox/exec", "POST", {
          command: line, scope: scope, repo: repo, network: true, timeout_s: 300
        });
        if (data.stdout) writeLog(data.stdout.replace(/\n?$/, "\n"));
        if (data.stderr) writeLog(data.stderr.replace(/\n?$/, "\n"));
        writeLog("[exit " + data.exit_code + "]\n");
        cwd = "";
        await loadTree();
      } catch (e) { writeLog(errText(e) + "\n"); }
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
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    if (cmd === "run") {
      if (arg) {
        var rp = cwd ? cwd + "/" + arg : arg;
        await openFile(rp, { silent: true });
      }
      await runEditor();
      return;
    }
    if (cmd === "key" || cmd === "uid") {
      if (!repo) { writeLog("no repo\n"); return; }
      if (arg) { saveRepoUid(repo, arg.trim()); writeLog("uid set\n"); return; }
      writeLog(getRepoUid(repo) ? "uid in session\n" : "no uid\n");
      return;
    }
    if (cmd === "push" || cmd === "commit") {
      if (!repo) { writeLog("no repo\n"); return; }
      var key = getRepoUid(repo);
      var msg = arg || (cmd + " from codespace");
      if (parts[1] && /^[a-f0-9]{16,}$/i.test(parts[1])) {
        key = parts[1]; saveRepoUid(repo, key);
        msg = parts.slice(2).join(" ").trim() || msg;
      }
      if (!key) {
        key = prompt("repo_uid:", "") || "";
        if (!key) { writeLog("needs repo_uid\n"); return; }
        saveRepoUid(repo, key);
      }
      try {
        var data = await api("/sandbox/repos/" + encodeURIComponent(repo) + "/" + cmd, "POST", {
          scope: scope, repo: repo, repo_uid: key, message: msg,
        });
        writeLog(cmd + " ok · start_row=" + (data.start_row || "?") + "\n");
      } catch (e) { writeLog(cmd + ": " + errText(e) + "\n"); }
      return;
    }
    if (cmd === "mkdir" && arg) {
      if (!requireRepo()) return;
      var mp = resolvePath(arg);
      try {
        await api("/sandbox/fs/mkdir", "POST", { scope: scope, repo: repo, path: mp });
        await api("/sandbox/fs/write", "POST", { scope: scope, repo: repo, path: mp + "/.keep", content: "" });
        await loadTree();
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    if (cmd === "touch" && arg) {
      if (!requireRepo()) return;
      var tp = resolvePath(arg);
      try {
        await api("/sandbox/fs/write", "POST", { scope: scope, repo: repo, path: tp, content: "" });
        await openFile(tp, { silent: true });
      } catch (e) { writeLog(errText(e) + "\n"); }
      return;
    }
    if (typeof window.acdNetworkTermCommand === "function") {
      var _netHandled = await window.acdNetworkTermCommand(cmd, parts, {
        repo: repo, scope: scope, api: api, writeLog: writeLog, errText: errText,
        line: line, refreshTree: typeof loadTree === "function" ? loadTree : null
      });
      if (_netHandled) return;
    }
    writeLog("unknown: " + cmd + " (help)\n");
  }



  // ACCD-TOOLBAR-DELEGATE
  function bindToolbarDelegate() {
    var panel = $("codePanel");
    if (!panel || panel.dataset.acdToolbar === "1") return;
    panel.dataset.acdToolbar = "1";
    panel.addEventListener("click", function (ev) {
      var btn = ev.target && ev.target.closest && ev.target.closest("button");
      if (!btn || !panel.contains(btn)) return;
      var id = btn.id || "";
      if (!id) return;
      ev.preventDefault();
      ev.stopPropagation();
      try {
        if (id === "btnCodeBack" || id === "btnCloseCode") return goHome();
        if (id === "btnRunCode") return runEditor();
        if (id === "btnTermRun") return runTerminal();
        if (id === "btnNewRepo") return createRepo();
        if (id === "btnNewFile") return newFile();
        if (id === "btnNewFolder") return newFolder();
        if (id === "btnSaveFile") return saveFile();
        if (id === "btnPushRepo") return pushRepo();
        if (id === "btnToggleSidebar") return setSidebar(!sidebarOpen);
        if (id === "btnCloseSidebar") return setSidebar(false);
        if (id === "btnToggleTerm") return setTermCollapsed(!termCollapsed);
      } catch (err) {
        console.error("[codespace]", id, err);
        try { writeLog("ui:" + id + " " + (err && err.message) + "\\n"); } catch (e) {}
      }
    }, false);
  }

  function goHome() {
    document.body.classList.remove("codespace-active");
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
    if (typeof window.acdGoHomeStrict === "function") window.acdGoHomeStrict();
  }

  async function showPanel() {
    var panel = $("codePanel");
    if (!panel) return;
    panel.style.setProperty("display", "flex", "important");
    panel.style.flexDirection = "column";
    panel.style.zIndex = "9999";
    bindToolbar();
    ensureGhostInput();
    setSidebar(true);
    setTermCollapsed(false);
    initMonaco();
    try {
      await refreshRepos();
      await loadTree();
      if (repo) {
        try { await openFile("backend/main.py", { silent: true }); }
        catch (e) { try { await openFile("main.py", { silent: true }); } catch (e2) {} }
      }
    } catch (e) {
      writeLog("boot: " + errText(e) + "\n");
    }
    setTimeout(function () {
      layoutEditor();
      focusTerm();
    }, 200);
  }

  function wireBtn(id, fn) {
    var el = $(id);
    if (!el) return;
    el.onclick = function (e) {
      e.preventDefault();
      e.stopPropagation();
      try { fn(); } catch (err) { console.warn("[codespace]", id, err); }
    };
  }

  function bindToolbar() {
    wireBtn("btnCodeBack", goHome);
    wireBtn("btnCloseCode", goHome);
    wireBtn("btnRunCode", runEditor);
    wireBtn("btnTermRun", runTerminal);
    wireBtn("btnNewRepo", createRepo);
    wireBtn("btnNewFile", newFile);
    wireBtn("btnNewFolder", newFolder);
    wireBtn("btnSaveFile", saveFile);
    wireBtn("btnPushRepo", pushRepo);
    wireBtn("btnToggleSidebar", function () { setSidebar(!sidebarOpen); });
    wireBtn("btnCloseSidebar", function () { setSidebar(false); });
    wireBtn("btnToggleTerm", function () { setTermCollapsed(!termCollapsed); });
    // hub open is owned by app.js acdOpenCodespace — do not steal btnHomeCode here
  }

  function bind() {
    var panel = $("codePanel");
    if (panel) panel.style.setProperty("display", "none", "important");
    bindToolbarDelegate();
    ensureGhostInput();
    bindToolbar();

    var sel = $("codeRepoSelect");
    if (sel) {
      sel.onchange = async function () {
        repo = sel.value || null;
        cwd = "";
        currentFile = "";
        await loadTree();
        try { await openFile("backend/main.py", { silent: true }); } catch (e) {}
      };
    }

    var out = $("codeOutput");
    if (out) {
      out.addEventListener("click", function (e) {
        e.preventDefault();
        focusTerm();
      });
      out.addEventListener("touchend", function (e) {
        e.preventDefault();
        focusTerm();
      });
    }

    var mon = $("monacoContainer");
    if (mon) {
      mon.addEventListener("mousedown", function () { blurTerm(); });
      mon.addEventListener("touchstart", function () { blurTerm(); }, { passive: true });
    }

    writeLog("Codespace · tap terminal to type · help\n");
    paintTerm();
  }

  
  window.acdTermApi = {
    insert: function (s) {
      cmdBuf = (cmdBuf || "") + String(s || "");
      var g = $("termGhostInput"); if (g) g.value = cmdBuf;
      try { focusTerm(); } catch (e) {}
      paintTerm();
    },
    setLine: function (s) {
      cmdBuf = String(s || "");
      var g = $("termGhostInput"); if (g) g.value = cmdBuf;
      try { focusTerm(); } catch (e) {}
      paintTerm();
    },
    enter: function () {
      var line = cmdBuf || ""; cmdBuf = "";
      var g = $("termGhostInput"); if (g) g.value = "";
      paintTerm(); return onCommand(line);
    },
    home: function () {
      var g = $("termGhostInput"); if (!g) return;
      try { g.setSelectionRange(0, 0); } catch (e) {}
      focusTerm();
    },
    end: function () {
      var g = $("termGhostInput"); if (!g) return;
      var n = (g.value || "").length;
      try { g.setSelectionRange(n, n); } catch (e) {}
      focusTerm();
    },
    getMods: function () { return { ctrl: !!window.__termCtrl, alt: !!window.__termAlt }; },
    setCtrl: function (v) { window.__termCtrl = !!v; },
    setAlt: function (v) { window.__termAlt = !!v; }
  };

  window.openCodePanel = showPanel;
  window.closeCodePanel = goHome;
  window.hideCodeScreen = goHome;
  window.acdSaveRepoUid = saveRepoUid;
  window.acdGetRepoUid = getRepoUid;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();



// ACCD-TERM-KEYBAR
(function () {
  function A() { return window.acdTermApi; }
  function sync() {
    var m = A() && A().getMods ? A().getMods() : {};
    document.querySelectorAll("#termKeyBar [data-term-key=ctrl]").forEach(function (b) {
      b.classList.toggle("is-on", !!m.ctrl);
    });
    document.querySelectorAll("#termKeyBar [data-term-key=alt]").forEach(function (b) {
      b.classList.toggle("is-on", !!m.alt);
    });
  }
  function go(ev) {
    var btn = ev.target && ev.target.closest && ev.target.closest("#termKeyBar .term-key");
    if (!btn) return;
    ev.preventDefault();
    var api = A();
    if (!api) { console.warn("open Codespace first"); return; }
    var k = btn.getAttribute("data-term-key");
    var c = btn.getAttribute("data-term-cmd");
    if (c === "cd") { api.insert("cd "); return; }
    if (c) { api.setLine(c); api.enter(); return; }
    if (k === "ctrl") { api.setCtrl(!api.getMods().ctrl); sync(); return; }
    if (k === "alt") { api.setAlt(!api.getMods().alt); sync(); return; }
    if (k === "home") { api.home(); return; }
    if (k === "end") { api.end(); return; }
    if (k === "tilde") { api.insert("\~"); return; }
    if (k === "slash") { api.insert("/"); return; }
    if (k === "enter") { api.enter(); return; }
  }
  function bind() {
    var bar = document.getElementById("termKeyBar");
    if (!bar || bar.dataset.bound) return;
    bar.dataset.bound = "1";
    bar.addEventListener("click", go);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();

// ACCD-NETWORK-TERM
// ACCD-T2-NET
(function () {
  var NET = /^(git|pip|pip3|npm|npx|yarn|curl|wget)\b/i;
  if (typeof window === "undefined") return;

  /** Collapse \r progress spam into last segment per line (git/curl style). */
  function collapseProgress(text) {
    if (!text) return "";
    return String(text).split("\n").map(function (line) {
      if (line.indexOf("\r") === -1) return line;
      var parts = line.split("\r");
      return parts[parts.length - 1];
    }).join("\n");
  }

  /** Default shallow clone unless user already passed depth/mirror/file. */
  function normalizeNetLine(line, cmd, parts) {
    line = (line || "").trim();
    if ((cmd || "").toLowerCase() === "clone") {
      line = "git clone " + (parts || []).slice(1).join(" ");
    }
    var low = line.toLowerCase();
    if (/^git\s+clone\b/.test(low)) {
      if (!/\s--depth(\s|=)/.test(low) &&
          !/\s--mirror\b/.test(low) &&
          !/\s--bundle\b/.test(low) &&
          !/\s--file\b/.test(low)) {
        line = line.replace(/^git\s+clone\b/i, "git clone --depth 1");
      }
    }
    return line;
  }

  window.acdNetworkTermCommand = async function (cmd, parts, ctx) {
    var raw = (ctx && ctx.line) || (parts || []).join(" ");
    if (!NET.test(raw) && (cmd || "").toLowerCase() !== "clone") return false;

    var line = normalizeNetLine(raw, cmd, parts);
    if (/^git\s+clone\b/i.test(line) && !(ctx && ctx.repo)) {
      writeLog("clone: create/open a codespace repo first (Explorer) so files persist\n");
      return true;
    }
    var writeLog = (ctx && ctx.writeLog) || function () {};
    var errText = (ctx && ctx.errText) || String;
    var api = ctx && ctx.api;
    if (!api) { writeLog("no api\n"); return true; }

    writeLog("$ " + line + "  [net]\n");
    var hb = setInterval(function () {
      writeLog("[net] still working…\n");
    }, 15000);

    try {
      var data = await api("/sandbox/exec", "POST", {
        command: line,
        scope: (ctx && ctx.scope) || "user",
        repo: (ctx && ctx.repo) || null,
        network: true,
        timeout_s: 300,
        use_proxy_env: true
      });
      if (data.stdout) writeLog(collapseProgress(data.stdout).replace(/\n?$/, "\n"));
      if (data.stderr) writeLog(collapseProgress(data.stderr).replace(/\n?$/, "\n"));
      if (data.error) writeLog("ERROR: " + data.error + "\n");
      if (data.timed_out) writeLog("[timed out]\n");
      writeLog("[exit " + (data.exit_code != null ? data.exit_code : "?") +
               (data.duration_s != null ? (" · " + data.duration_s + "s") : "") + "]\n");
      if (ctx && typeof ctx.refreshTree === "function") {
        try { await ctx.refreshTree(); } catch (e) {}
      }
    } catch (e) {
      writeLog("exec: " + errText(e) + "\n");
    } finally {
      clearInterval(hb);
    }
    return true;
  };
})();


// ACCD-OPEN-CODE-RESCUE
(function () {
  var _open = window.openCodePanel;
  window.openCodePanel = function () {
    document.body.classList.add("codespace-active");
    var input = document.getElementById("inputArea");
    if (input) input.setAttribute("hidden", "");
    if (typeof _open === "function") { try { _open(); } catch (e) {} }
    var panel = document.getElementById("codePanel");
    if (panel) {
      panel.style.setProperty("display", "flex", "important");
      panel.style.flexDirection = "column";
      panel.classList.add("active");
    }
  };
})();

// ACCD-CODESPACE-INTERACTION — terminal focus and panel interaction only.
(function () {
  function wireInteraction() {
    var panel = document.getElementById("codePanel");
    if (!panel) return;

    panel.style.pointerEvents = "auto";
    panel.style.zIndex = "9999";

    var out = document.getElementById("codeOutput");
    if (out && out.dataset.acdFocusBound !== "1") {
      out.dataset.acdFocusBound = "1";
      out.addEventListener("click", function () {
        var input = document.getElementById("termGhostInput");
        if (input) {
          try { input.focus({ preventScroll: true }); }
          catch (e) { try { input.focus(); } catch (e2) {} }
        }
      });
    }

    var bar = document.getElementById("termKeyBar");
    if (bar) bar.style.pointerEvents = "auto";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireInteraction);
  } else {
    wireInteraction();
  }

  document.addEventListener("acd-codespace-open", wireInteraction);
})();
