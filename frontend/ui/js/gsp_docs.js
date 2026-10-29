/**
 * GSP docs: Excel (configurable), Sheet (row 1..64, col 0..53), Workspace placement.
 * doc_uid / repo_uid = letter-chain of name (A=0, digits exact, _-. → 26+; no strip leading 0).
 */
(function () {
  // Chain source of truth = backend tokenizer (multilingual + digit markers).
  // Do not invent a parallel a-z map in the browser.
  var _chainCache = {};
  async function fetchChain(name, lang) {
    name = String(name || "");
    lang = lang || "en";
    var key = lang + ":" + name;
    if (_chainCache[key]) return _chainCache[key];
    var data = await api(
      "/sandbox/gsp/chain?name=" + encodeURIComponent(name) + "&lang=" + encodeURIComponent(lang)
    );
    _chainCache[key] = data;
    return data;
  }
  function uidFromNameSync(name) {
    // cache only; prefer fetchChain
    var hit = _chainCache["en:" + name];
    return hit ? hit.uid_str || hit.uid_compact : "";
  }
  window.acdFetchGspChain = fetchChain;
  window.acdUidFromName = function (name) {
    return uidFromNameSync(name);
  };
  window.acdLetterChain = function (name) {
    var hit = _chainCache["en:" + name];
    return hit && hit.chain ? hit.chain : [];
  };
  window.acdStartRowForName = function (name) {
    var hit = _chainCache["en:" + name];
    return hit ? hit.start_row : null;
  };

  var state = {
    kind: "sheet",
    parentRepo: "",
    docName: "",
    docUid: "",
    data: null,
    meta: null,
    // excel config
    nRows: 100,
    nCols: 26,
  };

  function token() {
    try {
      return localStorage.getItem("coMpaNeoN_token") || "";
    } catch (e) {
      return "";
    }
  }

  async function api(path, method, body) {
    var h = { Accept: "application/json" };
    var t = token();
    if (t) h.Authorization = "Bearer " + t;
    if (body != null) h["Content-Type"] = "application/json";
    var res = await fetch(path, {
      method: method || "GET",
      headers: h,
      body: body != null ? JSON.stringify(body) : undefined,
    });
    var text = await res.text();
    var data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = { raw: text };
    }
    if (!res.ok) throw new Error((data && (data.detail || data.error)) || text || res.status);
    return data;
  }

  function activeRepo() {
    try {
      if (window.acdGetActiveRepo) return window.acdGetActiveRepo();
    } catch (e) {}
    var sel = document.getElementById("codeRepoSelect");
    if (sel && sel.value) return sel.value;
    return state.parentRepo || "";
  }

  function ensurePanel() {
    var p = document.getElementById("gspDocPanel");
    if (p) return p;
    p = document.createElement("div");
    p.id = "gspDocPanel";
    p.style.cssText =
      "display:none;position:fixed;inset:0;z-index:10050;background:#0b1220;color:#e2e8f0;flex-direction:column;";
    p.innerHTML =
      '<div class="gsp-shell-header" style="display:flex;gap:8px;align-items:center;padding:10px 12px;border-bottom:1px solid #1e293b;flex-wrap:wrap;background:#0f172a">' +
      '<button type="button" id="gspDocBack" class="btn">← Back</button>' +
      '<strong id="gspDocTitle">Docs</strong>' +
      '<select id="gspParentType" style="padding:6px;border-radius:8px;background:#0b1220;color:#e2e8f0;border:1px solid #334155">' +
      '<option value="repo">Parent: repo</option><option value="room">Parent: room</option></select>' +
      '<input id="gspParentId" placeholder="repo name or room id" style="max-width:160px;padding:6px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#e2e8f0" />' +
      '<span id="gspDocMeta" style="opacity:0.7;font-size:12px;flex:1"></span>' +
      '<input id="gspDocNameInput" placeholder="DocName" style="max-width:140px;padding:6px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#e2e8f0" />' +
      '<button type="button" id="gspDocCreate" class="btn">Create</button>' +
      '<button type="button" id="gspDocRefresh" class="btn">Refresh</button>' +
      "</div>" +
      '<div style="display:flex;flex:1;min-height:0">' +
      '<aside id="gspDocList" style="width:220px;overflow:auto;border-right:1px solid #1e293b;padding:8px;font-size:13px;background:#0b1220"></aside>' +
      '<main id="gspDocGridWrap" style="flex:1;overflow:auto;padding:8px;background:#070b14"></main>' +
      "</div>" +
      '<div id="gspShellStatus" style="padding:6px 12px;font-size:11px;opacity:0.65;border-top:1px solid #1e293b">Sheet 54×64 · rows 1–64 · cols 0–53 · names start with a letter · Neon+B2 when configured</div>';
    document.body.appendChild(p);
    document.getElementById("gspDocBack").onclick = function () {
      p.style.display = "none";
      document.body.classList.remove("gsp-doc-open");
    };
    document.getElementById("gspDocCreate").onclick = function () {
      createDoc();
    };
    document.getElementById("gspDocRefresh").onclick = function () {
      refreshList();
    };
    var pt = document.getElementById("gspParentType");
    var pid = document.getElementById("gspParentId");
    if (pt) {
      pt.value = state.parentType || "repo";
      pt.onchange = function () {
        state.parentType = pt.value;
      };
    }
    if (pid) {
      pid.value = state.parentId || state.parentRepo || "";
      pid.onchange = function () {
        state.parentId = pid.value.trim();
        if (state.parentType === "repo") state.parentRepo = state.parentId;
      };
    }
    return p;
  }

  function openKind(kind) {
    state.kind = kind || "sheet";
    state.parentRepo = activeRepo();
    state.parentType = state.parentType || "repo";
    state.parentId = state.parentId || state.parentRepo;
    var p = ensurePanel();
    p.style.display = "flex";
    document.body.classList.add("gsp-doc-open");
    document.getElementById("gspDocTitle").textContent =
      kind === "xlsx" ? "Excel" : kind === "workspace" ? "Workspace grid" : "Spreadsheet";
    document.getElementById("gspDocMeta").textContent = state.parentRepo
      ? "parent repo: " + state.parentRepo
      : "open a codespace repo first (parent)";
    refreshList();
  }

  function saneName(name, what) {
    name = String(name || "").trim();
    if (!/^[A-Za-z][A-Za-z0-9_-]{0,62}$/.test(name)) {
      alert((what || "Name") + " must start with a letter; only letters, digits, _ or - after that (no leading ._-+@#/?)");
      return null;
    }
    return name;
  }
  async function createDoc() {
    var name = saneName(document.getElementById("gspDocNameInput").value, "Doc name");
    if (!name) return;
    var parentId = (document.getElementById("gspParentId") && document.getElementById("gspParentId").value.trim()) || state.parentId || state.parentRepo;
    var parentType = (document.getElementById("gspParentType") && document.getElementById("gspParentType").value) || state.parentType || "repo";
    state.parentType = parentType;
    state.parentId = parentId;
    if (parentType === "repo") state.parentRepo = parentId;
    if (!parentId) {
      alert(parentType === "room" ? "Enter room id as parent" : "Open a codespace repo or enter parent repo name");
      return;
    }
    var body = {
      scope: "user",
      parent_type: state.parentType || "repo",
      parent_repo: state.parentRepo,
      parent_id: state.parentId || state.parentRepo,
      doc_name: name,
      kind: state.kind === "xlsx" ? "xlsx" : state.kind === "workspace" ? "workspace" : "sheet",
      n_rows: state.nRows,
      n_cols: state.nCols,
    };
    try {
      try { await fetchChain(name); } catch (e) {}
      var res = await api("/sandbox/docs", "POST", body);
      state.docName = res.doc_name;
      state.docUid = res.doc_uid;
      await refreshList();
      await openDoc(res.doc_name);
    } catch (e) {
      alert(String(e.message || e));
    }
  }

  async function refreshList() {
    var box = document.getElementById("gspDocList");
    if (!box) return;
    box.innerHTML = "";
    if (!state.parentRepo) {
      box.textContent = "No parent repo";
      return;
    }
    try {
      var data = await api(
        "/sandbox/docs?parent_repo=" + encodeURIComponent(state.parentId || state.parentRepo) +
        "&parent_type=" + encodeURIComponent(state.parentType || "repo") +
        "&parent_id=" + encodeURIComponent(state.parentId || state.parentRepo) +
        "&scope=user"
      );
      (data.docs || []).forEach(function (d) {
        if (state.kind === "xlsx" && d.kind !== "xlsx") return;
        if (state.kind === "sheet" && d.kind !== "sheet") return;
        if (state.kind === "workspace" && d.kind !== "workspace") return;
        var row = document.createElement("div");
        row.style.cssText = "padding:6px 4px;cursor:pointer;border-radius:6px";
        row.textContent = d.doc_name + " · r" + (d.start_row || "?");
        row.onclick = function () {
          openDoc(d.doc_name);
        };
        box.appendChild(row);
      });
    } catch (e) {
      box.textContent = String(e.message || e);
    }
  }

  async function openDoc(docName) {
    state.docName = docName;
    try {
      var data = await api(
        "/sandbox/docs/" +
          encodeURIComponent(docName) +
          "?parent_repo=" +
          encodeURIComponent(state.parentRepo) +
          "&scope=user"
      );
      state.meta = data.meta || {};
      state.data = data.data || { cells: {} };
      state.docUid = state.meta.doc_uid || uidFromName(docName);
      document.getElementById("gspDocMeta").textContent =
        state.parentRepo +
        " / " +
        docName +
        " · uid " +
        state.docUid +
        " · start_row " +
        (state.meta.start_row || startRowForName(docName));
      renderGrid();
    } catch (e) {
      alert(String(e.message || e));
    }
  }

  function cellKey(r, c) {
    return r + ":" + c;
  }

  function renderGrid() {
    var wrap = document.getElementById("gspDocGridWrap");
    if (!wrap) return;
    wrap.innerHTML = "";
    var cells = (state.data && state.data.cells) || {};
    var isExcel = state.kind === "xlsx" || (state.meta && state.meta.kind === "xlsx");
    var r0, r1, c0, c1;
    if (isExcel) {
      r0 = 0;
      c0 = 0;
      r1 = Math.min((state.data && state.data.n_rows) || state.nRows, 40) - 1;
      c1 = Math.min((state.data && state.data.n_cols) || state.nCols, 20) - 1;
      if (state.meta && state.meta.kind === "xlsx") {
        var cfg = document.createElement("div");
        cfg.style.marginBottom = "8px";
        cfg.innerHTML =
          'Rows <input id="gspExcelRows" type="number" min="1" max="5000" value="' +
          ((state.data && state.data.n_rows) || state.nRows) +
          '" style="width:64px" /> Cols <input id="gspExcelCols" type="number" min="1" max="512" value="' +
          ((state.data && state.data.n_cols) || state.nCols) +
          '" style="width:64px" /> <span style="opacity:0.6;font-size:12px">config stored on create; view capped for UI</span>';
        wrap.appendChild(cfg);
      }
    } else {
      r0 = 1;
      r1 = 64;
      c0 = 0;
      c1 = 53;
    }
    var table = document.createElement("table");
    table.style.cssText = "border-collapse:collapse;font-size:11px;user-select:none";
    var head = document.createElement("tr");
    head.appendChild(document.createElement("th"));
    for (var c = c0; c <= c1; c++) {
      var th = document.createElement("th");
      th.textContent = c;
      th.style.cssText = "padding:2px 4px;opacity:0.5;position:sticky;top:0;background:#0b1220";
      head.appendChild(th);
    }
    table.appendChild(head);
    var maxR = isExcel ? r1 : Math.min(r1, 24); // UI window; full range still editable via prompt for far cells
    for (var r = r0; r <= maxR; r++) {
      var tr = document.createElement("tr");
      var rh = document.createElement("th");
      rh.textContent = r;
      rh.style.cssText = "padding:2px 6px;opacity:0.5";
      tr.appendChild(rh);
      for (var col = c0; col <= c1; col++) {
        (function (row, col) {
          var td = document.createElement("td");
          var key = cellKey(row, col);
          var entry = cells[key];
          td.textContent = entry && entry.value != null ? String(entry.value).slice(0, 12) : "";
          td.title = "r" + row + " c" + col + (entry && entry.placement ? " placed" : "");
          td.style.cssText =
            "border:1px solid #1e293b;min-width:28px;height:22px;text-align:center;cursor:pointer;" +
            (entry && entry.placed ? "background:#134e4a;" : "");
          td.onclick = function () {
            onCellTap(row, col, entry);
          };
          tr.appendChild(td);
        })(r, col);
      }
      table.appendChild(tr);
    }
    wrap.appendChild(table);
    if (!isExcel && maxR < 64) {
      var note = document.createElement("div");
      note.style.cssText = "margin-top:8px;opacity:0.6;font-size:12px";
      note.textContent = "Showing rows 1.." + maxR + " of 1..64, cols 0..53 — tap any visible cell to edit/place.";
      wrap.appendChild(note);
    }
  }

  async function onCellTap(row, col, entry) {
    var placeMode = state.kind === "workspace" || (state.meta && state.meta.kind === "workspace");
    var cur = entry && entry.value != null ? String(entry.value) : "";
    var msg =
      "Cell row=" +
      row +
      " col=" +
      col +
      "\nstart_row=" +
      (state.meta && state.meta.start_row) +
      " doc_uid=" +
      state.docUid +
      (entry && entry.placement ? "\n(placed)" : "") +
      "\n\nValue:";
    var val = prompt(msg, cur);
    if (val == null) return;
    try {
      var res = await api("/sandbox/docs/cell", "POST", {
        scope: "user",
        parent_type: state.parentType || "repo",
        parent_repo: state.parentRepo || state.parentId,
        parent_id: state.parentId || state.parentRepo,
        doc_name: state.docName,
        doc_uid: state.docUid,
        row: row,
        col: col,
        value: val,
        place: placeMode,
      });
      if (!state.data) state.data = { cells: {} };
      if (!state.data.cells) state.data.cells = {};
      state.data.cells[cellKey(row, col)] = res.entry;
      renderGrid();
    } catch (e) {
      alert(String(e.message || e));
    }
  }

  window.acdOpenExcel = function () {
    openKind("xlsx");
  };
  window.acdOpenSheet = function () {
    openKind("sheet");
  };
  window.acdOpenWorkspaceGrid = function () {
    openKind("workspace");
  };
  window.acdGspDocs = { openKind: openKind, uidFromName: uidFromName, letterChain: letterChain };

  function injectButtons() {
    var specs = [
      { id: "btnGspExcel", label: "Excel", fn: "acdOpenExcel" },
      { id: "btnGspSheet", label: "Sheet", fn: "acdOpenSheet" },
      { id: "btnGspWorkspace", label: "Workspace", fn: "acdOpenWorkspaceGrid" },
    ];
    function addTo(parent, prefix) {
      if (!parent) return;
      specs.forEach(function (s) {
        var id = prefix + s.id;
        if (document.getElementById(id)) return;
        var b = document.createElement("button");
        b.type = "button";
        b.id = id;
        b.className = "btn";
        b.textContent = s.label;
        b.style.margin = "0 4px";
        b.onclick = function (ev) {
          ev.preventDefault();
          if (window[s.fn]) window[s.fn]();
        };
        parent.appendChild(b);
      });
    }
    // Home hub actions
    addTo(document.getElementById("homeActions") || document.getElementById("homeHub"), "home");
    // Workspace / main top bar
    addTo(document.querySelector("#mainScreen .top-nav") || document.querySelector(".top-nav"), "ws");
    // Codespace toolbar
    addTo(document.getElementById("codeToolbar") || document.querySelector("#codePanel .code-toolbar"), "cs");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectButtons);
  } else {
    injectButtons();
  }
  setTimeout(injectButtons, 800);
  console.log("[acd] gsp_docs ready");
})();
