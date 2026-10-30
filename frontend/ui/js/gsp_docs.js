/**
 * Accodite Docs — real app screens (not a console).
 * SheetS | DBase | CollabSheet | Presentations
 * Home buttons stay on home; room buttons only when workspace-active.
 * Never touches codespace / openRoom.
 */
(function () {
  "use strict";

  var KINDS = {
    sheets: { label: "SheetS", icon: "fa-table-cells", api: "sheet", blurb: "54×64 GSP sheet with gridlines" },
    dbase: { label: "DBase", icon: "fa-database", api: "xlsx", blurb: "Record table · configurable grid · analysis" },
    collabsheet: { label: "CollabSheet", icon: "fa-people-arrows", api: "workspace", blurb: "Team collab surface · host for SheetS & DBase" },
    presentations: { label: "Presentations", icon: "fa-display", api: "pptx", blurb: "Slide faces · gradients · no sheet gridlines" },
  };

  var GRADIENTS = (function () {
    var pairs = [
      ["#0f172a", "#1e3a5f"], ["#1a0533", "#4c1d95"], ["#0c4a6e", "#06b6d4"], ["#14532d", "#22c55e"],
      ["#7c2d12", "#f97316"], ["#4a044e", "#e879f9"], ["#1e1b4b", "#6366f1"], ["#450a0a", "#ef4444"],
      ["#083344", "#14b8a6"], ["#422006", "#eab308"], ["#0f766e", "#99f6e4"], ["#3b0764", "#c084fc"],
      ["#111827", "#374151"], ["#1e3a8a", "#93c5fd"], ["#064e3b", "#6ee7b7"], ["#701a75", "#f0abfc"],
      ["#7f1d1d", "#fca5a5"], ["#713f12", "#fde68a"], ["#164e63", "#67e8f9"], ["#312e81", "#a5b4fc"],
      ["#134e4a", "#5eead4"], ["#4c0519", "#fb7185"], ["#1c1917", "#a8a29e"], ["#172554", "#60a5fa"],
      ["#365314", "#a3e635"], ["#581c87", "#d8b4fe"], ["#9a3412", "#fdba74"], ["#0e7490", "#a5f3fc"],
      ["#1e293b", "#64748b"], ["#831843", "#f9a8d4"], ["#3f6212", "#bef264"], ["#1e3a8a", "#1d4ed8"],
      ["#0f172a", "#f43f5e"], ["#022c22", "#10b981"], ["#2e1065", "#7c3aed"], ["#431407", "#c2410c"],
      ["#082f49", "#0ea5e9"], ["#1a2e05", "#65a30d"], ["#4c1d95", "#ddd6fe"], ["#881337", "#ffe4e6"],
      ["#0c4a6e", "#e0f2fe"], ["#365314", "#ecfccb"], ["#500724", "#fce7f3"], ["#1e1b4b", "#e0e7ff"],
      ["#713f12", "#fffbeb"], ["#134e4a", "#ccfbf1"], ["#7c2d12", "#ffedd5"], ["#312e81", "#eef2ff"],
      ["#14532d", "#dcfce7"], ["#9f1239", "#fff1f2"], ["#155e75", "#cffafe"], ["#3b0764", "#f5f3ff"],
      ["#78350f", "#fef3c7"], ["#0f766e", "#f0fdfa"], ["#1e3a5f", "#dbeafe"], ["#4a044e", "#faf5ff"],
      ["#7f1d1d", "#fef2f2"], ["#052e16", "#f0fdf4"], ["#1e293b", "#f8fafc"], ["#0c4a6e", "#f0f9ff"],
      ["#422006", "#fefce8"], ["#2e1065", "#faf5ff"], ["#881337", "#fdf2f8"], ["#164e63", "#ecfeff"],
      ["#365314", "#f7fee7"], ["#4c0519", "#fff1f2"], ["#083344", "#f0fdfa"], ["#1a0533", "#faf5ff"],
      ["#450a0a", "#fef2f2"], ["#0f172a", "#22d3ee"],
    ];
    return pairs.map(function (p, i) {
      return { id: "g" + String(i).padStart(2, "0"), css: "linear-gradient(135deg," + p[0] + "," + p[1] + ")" };
    });
  })();

  var state = {
    kind: "sheets",
    parentType: "repo",
    parentId: "",
    parentRepo: "",
    docName: "",
    docUid: "",
    data: null,
    nRows: 64,
    nCols: 54,
    gsp: { C: 26, R: 64, mode: "standard" },
    slideIndex: 0,
    selected: null,
  };

  function token() {
    try {
      return localStorage.getItem("coMpaNeoN_token") || localStorage.getItem("token") || "";
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

  function apiKind(k) {
    return (KINDS[k] || KINDS.sheets).api;
  }

  function resolveParent() {
    var roomId = window.currentRoomId || (typeof currentRoomId !== "undefined" ? currentRoomId : null);
    var inRoom =
      !!roomId &&
      document.body.classList.contains("workspace-active") &&
      !document.body.classList.contains("home-active") &&
      !document.body.classList.contains("codespace-active");
    if (inRoom) return { parentType: "room", parentId: String(roomId), parentRepo: "" };
    var repo = "";
    try {
      if (window.acdTermApi && window.acdTermApi.getRepo) repo = window.acdTermApi.getRepo() || "";
    } catch (e) {}
    if (repo) return { parentType: "repo", parentId: repo, parentRepo: repo };
    return { parentType: "repo", parentId: "HomeDocs", parentRepo: "HomeDocs" };
  }

  function ensureCss() {
    if (document.getElementById("acdDocsCss")) return;
    var s = document.createElement("style");
    s.id = "acdDocsCss";
    s.textContent =
      "#gspDocsPanel{font-family:Inter,system-ui,sans-serif!important}" +
      "#gspDocsPanel *{box-sizing:border-box}" +
      ".acd-docs-top{display:flex;align-items:center;gap:8px;padding:10px 12px;background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap}" +
      ".acd-docs-top .acd-brand{font-weight:700;font-size:15px;color:#f8fafc}" +
      ".acd-docs-top .acd-sub{font-size:12px;color:#94a3b8}" +
      ".acd-docs-btn{border:1px solid #334155;background:#1e293b;color:#e2e8f0;border-radius:10px;padding:8px 12px;font-size:13px;cursor:pointer}" +
      ".acd-docs-btn:hover{border-color:#22d3ee;color:#fff}" +
      ".acd-docs-btn.primary{background:#0e7490;border-color:#06b6d4}" +
      ".acd-docs-btn.active{border-color:#22d3ee;box-shadow:0 0 0 1px #22d3ee}" +
      ".acd-docs-body{display:flex;flex:1;min-height:0;background:#020617}" +
      ".acd-docs-side{width:220px;background:#0b1220;border-right:1px solid #1e293b;padding:12px;overflow:auto}" +
      ".acd-docs-main{flex:1;overflow:auto;padding:16px;background:#020617}" +
      ".acd-docs-card{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px;margin-bottom:12px}" +
      ".acd-docs-card h3{margin:0 0 6px;color:#f8fafc;font-size:16px}" +
      ".acd-docs-card p{margin:0;color:#94a3b8;font-size:13px}" +
      ".acd-sheet-wrap{overflow:auto;border-radius:12px;border:1px solid #1e293b;background:#0b1220}" +
      ".acd-sheet-table{border-collapse:collapse;width:max-content;font-size:12px;font-family:system-ui,sans-serif}" +
      ".acd-sheet-table th{background:#1e293b;color:#94a3b8;padding:6px 8px;border:1px solid #334155;position:sticky;top:0}" +
      ".acd-sheet-table td{min-width:72px;height:28px;border:1px solid #1e293b;padding:4px 6px;color:#e2e8f0;cursor:pointer;background:#0b1220}" +
      ".acd-sheet-table td:hover{background:#1e293b}" +
      ".acd-sheet-table td.on{outline:2px solid #22d3ee}" +
      ".acd-sheet-table td.frag{background:#14532d44}" +
      ".acd-formula{display:flex;gap:8px;align-items:center;margin:10px 0}" +
      ".acd-formula input{flex:1;padding:10px 12px;border-radius:10px;border:1px solid #334155;background:#0b1220;color:#f8fafc;font-size:14px}" +
      ".acd-face{min-height:360px;border-radius:18px;padding:32px;color:#fff;box-shadow:0 20px 50px #0008}" +
      ".acd-face [contenteditable]{outline:none}" +
      ".acd-face-title{font-size:28px;font-weight:800;margin-bottom:12px}" +
      ".acd-face-body{font-size:16px;line-height:1.55;min-height:140px;opacity:.95}" +
      ".acd-empty{text-align:center;padding:48px 20px;color:#94a3b8}" +
      ".acd-empty h2{color:#e2e8f0;margin:0 0 8px}" +
      ".acd-doc-item{display:block;width:100%;text-align:left;margin:0 0 6px;padding:10px 12px;border-radius:12px;border:1px solid #1e293b;background:#111827;color:#e2e8f0;cursor:pointer}" +
      ".acd-doc-item:hover{border-color:#22d3ee}" +
      ".acd-home-docs,.acd-room-docs{display:flex;gap:6px;flex-wrap:wrap;align-items:center}" +
      "body.home-active .acd-room-docs{display:none!important}" +
      "body.workspace-active .acd-home-docs{display:none!important}" +
      "body.codespace-active #gspDocsPanel{display:none!important}";
    document.head.appendChild(s);
  }

  function ensurePanel() {
    ensureCss();
    var p = document.getElementById("gspDocsPanel");
    if (p) return p;
    p = document.createElement("div");
    p.id = "gspDocsPanel";
    p.style.cssText =
      "display:none;position:fixed;inset:0;z-index:11000;background:#020617;color:#e2e8f0;flex-direction:column";
    p.innerHTML =
      '<div class="acd-docs-top">' +
      '<button type="button" class="acd-docs-btn" id="gspDocBack">← Back</button>' +
      '<span class="acd-brand" id="gspDocTitle">Docs</span>' +
      '<span class="acd-sub" id="gspDocScope"></span>' +
      '<span style="flex:1"></span>' +
      '<input id="gspDocNameInput" placeholder="Document name" maxlength="64" ' +
      'style="width:150px;padding:8px 10px;border-radius:10px;border:1px solid #334155;background:#0b1220;color:#fff" />' +
      '<button type="button" class="acd-docs-btn primary" id="gspDocCreate">Create</button>' +
      "</div>" +
      '<div class="acd-docs-top" id="gspKindBar" style="background:#0b1220"></div>' +
      '<div class="acd-docs-top" id="gspToolBar" style="display:none;background:#020617"></div>' +
      '<div class="acd-docs-body">' +
      '<aside class="acd-docs-side" id="gspDocList"></aside>' +
      '<main class="acd-docs-main" id="gspDocStage"></main>' +
      "</div>";
    document.body.appendChild(p);

    document.getElementById("gspDocBack").onclick = function () {
      p.style.display = "none";
    };
    document.getElementById("gspDocCreate").onclick = function () {
      createDoc();
    };

    var bar = document.getElementById("gspKindBar");
    Object.keys(KINDS).forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "acd-docs-btn";
      b.dataset.kind = k;
      b.innerHTML = '<i class="fa-solid ' + KINDS[k].icon + '"></i> ' + KINDS[k].label;
      b.onclick = function () {
        openKind(k);
      };
      bar.appendChild(b);
    });
    return p;
  }

  function openKind(kind) {
    if (kind === "sheet" || kind === "xlsx" || kind === "workspace" || kind === "pptx" || kind === "excel") {
      kind = { sheet: "sheets", xlsx: "dbase", excel: "dbase", workspace: "collabsheet", pptx: "presentations" }[kind] || kind;
    }
    if (!KINDS[kind]) kind = "sheets";
    state.kind = kind;
    var par = resolveParent();
    state.parentType = par.parentType;
    state.parentId = par.parentId;
    state.parentRepo = par.parentRepo || par.parentId;
    if (kind === "sheets" || kind === "collabsheet") {
      state.nRows = 64;
      state.nCols = 54;
    } else if (kind === "dbase") {
      state.nRows = state.gsp.R || 64;
      state.nCols = state.gsp.C || 26;
    }
    var panel = ensurePanel();
    panel.style.display = "flex";
    document.getElementById("gspDocTitle").textContent = KINDS[kind].label;
    document.getElementById("gspDocScope").textContent =
      (state.parentType === "room" ? "Room" : "Home/Repo") + " · " + String(state.parentId).slice(0, 20);
    document.querySelectorAll("#gspKindBar .acd-docs-btn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.kind === kind);
    });
    state.docName = "";
    state.data = null;
    paintEmpty();
    refreshList();
    paintToolbar();
  }

  function paintToolbar() {
    var tb = document.getElementById("gspToolBar");
    if (!tb) return;
    if (state.kind === "dbase") {
      tb.style.display = "flex";
      tb.innerHTML =
        '<span class="acd-sub">Grid</span>' +
        '<input id="gspCfgC" type="number" min="2" max="120" value="' +
        (state.gsp.C || 26) +
        '" style="width:56px;padding:6px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#fff" />' +
        "<span>×</span>" +
        '<input id="gspCfgR" type="number" min="2" max="200" value="' +
        (state.gsp.R || 64) +
        '" style="width:56px;padding:6px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#fff" />' +
        '<button type="button" class="acd-docs-btn" id="gspCfgApply">Resize</button>';
      document.getElementById("gspCfgApply").onclick = function () {
        state.gsp.C = +document.getElementById("gspCfgC").value || 26;
        state.gsp.R = +document.getElementById("gspCfgR").value || 64;
        state.nCols = state.gsp.C;
        state.nRows = state.gsp.R;
        if (state.data) renderStage();
      };
    } else {
      tb.style.display = "none";
      tb.innerHTML = "";
    }
  }

  function paintEmpty() {
    var stage = document.getElementById("gspDocStage");
    if (!stage) return;
    var k = KINDS[state.kind];
    stage.innerHTML =
      '<div class="acd-empty">' +
      '<div style="font-size:42px;margin-bottom:12px"><i class="fa-solid ' +
      k.icon +
      '"></i></div>' +
      "<h2>" +
      k.label +
      "</h2>" +
      "<p>" +
      k.blurb +
      "</p>" +
      '<p style="margin-top:14px">Create a document on the right, or open one from the list.</p>' +
      "</div>";
  }

  async function createDoc() {
    var name = (document.getElementById("gspDocNameInput").value || "").trim();
    if (!/^[A-Za-z][A-Za-z0-9_-]{0,62}$/.test(name)) {
      alert("Name must start with a letter");
      return;
    }
    var par = resolveParent();
    state.parentType = par.parentType;
    state.parentId = par.parentId;
    state.parentRepo = par.parentRepo || par.parentId;
    try {
      var res = await api("/sandbox/docs", "POST", {
        scope: "user",
        parent_type: state.parentType === "room" ? "room" : "repo",
        parent_repo: state.parentRepo || state.parentId,
        parent_id: state.parentId,
        doc_name: name,
        kind: apiKind(state.kind),
        n_rows: state.nRows,
        n_cols: state.nCols,
      });
      state.docName = name;
      state.docUid = res.doc_uid || "";
      if (state.kind === "presentations") {
        state.data = { slides: [{ id: "s0", title: name, body: "Start writing…", gradient: "g00" }] };
      } else if (state.kind === "dbase") {
        state.data = { sheets: { Sheet1: { cells: {} } }, active_sheet: "Sheet1", cells: {} };
      } else {
        state.data = { cells: {} };
      }
      await refreshList();
      renderStage();
    } catch (e) {
      alert("Create failed: " + e.message);
    }
  }

  async function refreshList() {
    var list = document.getElementById("gspDocList");
    if (!list) return;
    list.innerHTML = '<div class="acd-sub">Documents</div>';
    try {
      var q =
        "/sandbox/docs?parent_repo=" +
        encodeURIComponent(state.parentRepo || state.parentId || "") +
        "&parent_type=" +
        encodeURIComponent(state.parentType === "room" ? "room" : "repo") +
        "&parent_id=" +
        encodeURIComponent(state.parentId || "") +
        "&scope=user";
      var data = await api(q);
      var docs = data.docs || [];
      var want = apiKind(state.kind);
      var n = 0;
      docs.forEach(function (d) {
        var k = d.kind || "";
        if (state.kind !== "collabsheet" && k && k !== want && !(want === "pptx" && k === "presentations")) return;
        n++;
        var b = document.createElement("button");
        b.type = "button";
        b.className = "acd-doc-item";
        b.innerHTML = "<strong>" + escapeHtml(d.doc_name || d.name || "?") + "</strong>";
        b.onclick = function () {
          openDoc(d.doc_name || d.name);
        };
        list.appendChild(b);
      });
      if (!n) {
        var empty = document.createElement("div");
        empty.className = "acd-sub";
        empty.style.marginTop = "10px";
        empty.textContent = "No documents yet";
        list.appendChild(empty);
      }
    } catch (e) {
      list.innerHTML += '<div style="color:#f87171;font-size:12px;margin-top:8px">' + escapeHtml(e.message) + "</div>";
    }
  }

  async function openDoc(name) {
    state.docName = name;
    try {
      var data = await api(
        "/sandbox/docs/get?parent_repo=" +
          encodeURIComponent(state.parentRepo || state.parentId) +
          "&parent_id=" +
          encodeURIComponent(state.parentId) +
          "&parent_type=" +
          encodeURIComponent(state.parentType === "room" ? "room" : "repo") +
          "&doc_name=" +
          encodeURIComponent(name) +
          "&scope=user"
      );
      state.data = (data && data.data) || { cells: {} };
      state.docUid = (data.meta && data.meta.doc_uid) || state.docUid;
    } catch (e) {
      state.data = state.data || { cells: {} };
    }
    if (state.kind === "presentations" && !(state.data && state.data.slides)) {
      state.data = { slides: [{ id: "s0", title: name, body: "", gradient: "g00" }] };
    }
    renderStage();
  }

  function activeCells() {
    state.data = state.data || { cells: {} };
    if (state.kind === "dbase") {
      state.data.sheets = state.data.sheets || { Sheet1: { cells: state.data.cells || {} } };
      var sn = state.data.active_sheet || "Sheet1";
      state.data.sheets[sn] = state.data.sheets[sn] || { cells: {} };
      return state.data.sheets[sn].cells;
    }
    state.data.cells = state.data.cells || {};
    return state.data.cells;
  }

  function renderStage() {
    if (state.kind === "presentations") return renderPresentation();
    if (state.kind === "collabsheet" && !state.docName) return renderCollabHub();
    return renderSheet();
  }

  function renderCollabHub() {
    var stage = document.getElementById("gspDocStage");
    stage.innerHTML =
      '<div class="acd-docs-card"><h3>CollabSheet</h3><p>Team collaborative surface for this scope. Open a linked tool:</p></div>' +
      '<div style="display:flex;gap:10px;flex-wrap:wrap">' +
      '<button type="button" class="acd-docs-btn primary" id="hubDBase"><i class="fa-solid fa-database"></i> DBase</button>' +
      '<button type="button" class="acd-docs-btn" id="hubSheetS"><i class="fa-solid fa-table-cells"></i> SheetS</button>' +
      '<button type="button" class="acd-docs-btn" id="hubPres"><i class="fa-solid fa-display"></i> Presentations</button>' +
      "</div>" +
      '<div class="acd-docs-card" style="margin-top:16px"><p>Or create a CollabSheet document above to edit the shared grid.</p></div>';
    document.getElementById("hubDBase").onclick = function () {
      openKind("dbase");
    };
    document.getElementById("hubSheetS").onclick = function () {
      openKind("sheets");
    };
    document.getElementById("hubPres").onclick = function () {
      openKind("presentations");
    };
  }

  function renderSheet() {
    var stage = document.getElementById("gspDocStage");
    var rows = Math.min(state.nRows || 64, 64);
    var cols = Math.min(state.nCols || 54, 54);
    var cells = activeCells();
    var html = '<div class="acd-docs-card"><h3>' + escapeHtml(state.docName || "Untitled") + "</h3>";
    html += "<p>" + KINDS[state.kind].label + " · " + cols + "×" + rows + "</p></div>";

    if (state.kind === "dbase" && state.data.sheets) {
      html += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">';
      Object.keys(state.data.sheets).forEach(function (sn) {
        var on = sn === (state.data.active_sheet || "Sheet1");
        html +=
          '<button type="button" class="acd-docs-btn' +
          (on ? " active" : "") +
          '" data-sheet="' +
          escapeHtml(sn) +
          '">' +
          escapeHtml(sn) +
          "</button>";
      });
      html += '<button type="button" class="acd-docs-btn" id="addSheet">+ Sheet</button></div>';
    }

    html +=
      '<div class="acd-formula"><span id="cellRef" style="min-width:40px;color:#22d3ee;font-weight:700">—</span>' +
      '<input id="formulaBar" placeholder="Edit cell value" /><button type="button" class="acd-docs-btn primary" id="formulaApply">Apply</button></div>';

    html += '<div class="acd-sheet-wrap"><table class="acd-sheet-table"><thead><tr><th></th>';
    for (var c = 0; c < cols; c++) html += "<th>" + c + "</th>";
    html += "</tr></thead><tbody>";
    for (var r = 1; r <= rows; r++) {
      html += "<tr><th>" + r + "</th>";
      for (var c2 = 0; c2 < cols; c2++) {
        var key = r + ":" + c2;
        var val = cells[key];
        if (val && typeof val === "object") val = val.value || "";
        html +=
          '<td data-r="' +
          r +
          '" data-c="' +
          c2 +
          '">' +
          escapeHtml(String(val || "").slice(0, 24)) +
          "</td>";
      }
      html += "</tr>";
    }
    html += "</tbody></table></div>";
    stage.innerHTML = html;

    stage.querySelectorAll("td[data-r]").forEach(function (td) {
      td.onclick = function () {
        stage.querySelectorAll("td.on").forEach(function (x) {
          x.classList.remove("on");
        });
        td.classList.add("on");
        var r = +td.getAttribute("data-r");
        var c = +td.getAttribute("data-c");
        state.selected = { r: r, c: c };
        document.getElementById("cellRef").textContent = r + ":" + c;
        var cur = cells[r + ":" + c];
        document.getElementById("formulaBar").value =
          cur && typeof cur === "object" ? cur.value || "" : cur || "";
        document.getElementById("formulaBar").focus();
      };
    });
    var apply = function () {
      if (!state.selected) return;
      writeCell(state.selected.r, state.selected.c, document.getElementById("formulaBar").value);
    };
    document.getElementById("formulaApply").onclick = apply;
    document.getElementById("formulaBar").onkeydown = function (ev) {
      if (ev.key === "Enter") apply();
    };
    stage.querySelectorAll("[data-sheet]").forEach(function (b) {
      b.onclick = function () {
        state.data.active_sheet = b.getAttribute("data-sheet");
        renderSheet();
        snapshotSave();
      };
    });
    var add = document.getElementById("addSheet");
    if (add) {
      add.onclick = function () {
        var n = "Sheet" + (Object.keys(state.data.sheets).length + 1);
        state.data.sheets[n] = { cells: {} };
        state.data.active_sheet = n;
        renderSheet();
        snapshotSave();
      };
    }
  }

  async function writeCell(row, col, value) {
    if (!state.docName) return;
    var cells = activeCells();
    cells[row + ":" + col] = { value: value, row: row, col: col };
    renderSheet();
    try {
      await api("/sandbox/docs/cell", "POST", {
        scope: "user",
        parent_type: state.parentType === "room" ? "room" : "repo",
        parent_repo: state.parentRepo || state.parentId,
        parent_id: state.parentId,
        doc_name: state.docName,
        doc_uid: state.docUid,
        row: row,
        col: col,
        value: value,
        place: state.kind === "collabsheet",
      });
    } catch (e) {
      snapshotSave();
    }
  }

  function renderPresentation() {
    var stage = document.getElementById("gspDocStage");
    var slides = (state.data && state.data.slides) || [
      { id: "s0", title: state.docName || "Slide", body: "", gradient: "g00" },
    ];
    state.data = state.data || {};
    state.data.slides = slides;
    if (state.slideIndex >= slides.length) state.slideIndex = 0;
    var s = slides[state.slideIndex];
    var g = GRADIENTS.find(function (x) {
      return x.id === s.gradient;
    }) || GRADIENTS[0];

    var html =
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center">' +
      '<button type="button" class="acd-docs-btn" id="prevFace">←</button>' +
      "<strong>Face " +
      (state.slideIndex + 1) +
      " / " +
      slides.length +
      "</strong>" +
      '<button type="button" class="acd-docs-btn" id="nextFace">→</button>' +
      '<button type="button" class="acd-docs-btn primary" id="addFace">+ Face</button>' +
      '<select id="gradSel" class="acd-docs-btn"></select></div>';
    html +=
      '<div class="acd-face" style="background:' +
      g.css +
      '">' +
      '<div class="acd-face-title" contenteditable="true" id="faceTitle">' +
      escapeHtml(s.title || "") +
      "</div>" +
      '<div class="acd-face-body" contenteditable="true" id="faceBody">' +
      escapeHtml(s.body || "") +
      "</div></div>";
    html += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px" id="gradStrip"></div>';
    stage.innerHTML = html;

    var sel = document.getElementById("gradSel");
    GRADIENTS.forEach(function (gg) {
      var o = document.createElement("option");
      o.value = gg.id;
      o.textContent = gg.id;
      if (gg.id === s.gradient) o.selected = true;
      sel.appendChild(o);
    });
    sel.onchange = function () {
      s.gradient = sel.value;
      persistSlides(slides);
      renderPresentation();
    };
    var strip = document.getElementById("gradStrip");
    GRADIENTS.slice(0, 20).forEach(function (gg) {
      var b = document.createElement("button");
      b.type = "button";
      b.title = gg.id;
      b.style.cssText =
        "width:28px;height:28px;border-radius:8px;border:2px solid " +
        (gg.id === s.gradient ? "#22d3ee" : "#334155") +
        ";background:" +
        gg.css;
      b.onclick = function () {
        s.gradient = gg.id;
        persistSlides(slides);
        renderPresentation();
      };
      strip.appendChild(b);
    });
    document.getElementById("prevFace").onclick = function () {
      state.slideIndex = (state.slideIndex - 1 + slides.length) % slides.length;
      renderPresentation();
    };
    document.getElementById("nextFace").onclick = function () {
      state.slideIndex = (state.slideIndex + 1) % slides.length;
      renderPresentation();
    };
    document.getElementById("addFace").onclick = function () {
      slides.push({ id: "s" + slides.length, title: "Face " + (slides.length + 1), body: "", gradient: "g00" });
      state.slideIndex = slides.length - 1;
      persistSlides(slides);
      renderPresentation();
    };
    document.getElementById("faceTitle").onblur = function () {
      s.title = this.innerText;
      persistSlides(slides);
    };
    document.getElementById("faceBody").onblur = function () {
      s.body = this.innerText;
      persistSlides(slides);
    };
  }

  function persistSlides(slides) {
    state.data = state.data || {};
    state.data.slides = slides;
    snapshotSave();
  }

  async function snapshotSave() {
    if (!state.docName || !state.data) return;
    try {
      await api("/sandbox/docs/snapshot", "POST", {
        scope: "user",
        parent_type: state.parentType === "room" ? "room" : "repo",
        parent_repo: state.parentRepo || state.parentId,
        parent_id: state.parentId,
        doc_name: state.docName,
        doc_uid: state.docUid,
        data: state.data,
      });
    } catch (e) {}
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  window.acdOpenSheetS = function () {
    openKind("sheets");
  };
  window.acdOpenDBase = function () {
    openKind("dbase");
  };
  window.acdOpenCollabSheet = function () {
    openKind("collabsheet");
  };
  window.acdOpenPresentations = function () {
    openKind("presentations");
  };
  window.acdOpenSheet = window.acdOpenSheetS;
  window.acdOpenExcel = window.acdOpenDBase;
  window.acdOpenWorkspaceGrid = window.acdOpenCollabSheet;

  function mkBtn(s, prefix) {
    var id = prefix + s.id;
    if (document.getElementById(id)) return document.getElementById(id);
    var b = document.createElement("button");
    b.type = "button";
    b.id = id;
    b.className = "acd-docs-btn";
    b.innerHTML = '<i class="fa-solid ' + s.icon + '"></i> ' + s.label;
    b.onclick = function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      if (window[s.fn]) window[s.fn]();
    };
    return b;
  }

  function injectButtons() {
    ensureCss();
    var specs = [
      { id: "btnSheetS", label: "SheetS", icon: "fa-table-cells", fn: "acdOpenSheetS" },
      { id: "btnDBase", label: "DBase", icon: "fa-database", fn: "acdOpenDBase" },
      { id: "btnCollabSheet", label: "CollabSheet", icon: "fa-people-arrows", fn: "acdOpenCollabSheet" },
      { id: "btnPresentations", label: "Presentations", icon: "fa-display", fn: "acdOpenPresentations" },
    ];

    // HOME only — dedicated strip under home hub
    var homeHost = document.getElementById("homeDocsStrip");
    if (!homeHost) {
      var hub = document.getElementById("homeHub") || document.getElementById("homeActions");
      if (hub) {
        homeHost = document.createElement("div");
        homeHost.id = "homeDocsStrip";
        homeHost.className = "acd-home-docs";
        homeHost.style.cssText = "margin-top:10px;padding:8px 0";
        hub.appendChild(homeHost);
      }
    }
    if (homeHost) {
      specs.forEach(function (s) {
        if (!document.getElementById("home" + s.id)) homeHost.appendChild(mkBtn(s, "home"));
      });
    }

    // ROOM only — dedicated strip, not dumping into random top-nav
    var roomHost = document.getElementById("roomDocsStrip");
    if (!roomHost) {
      var main = document.getElementById("mainScreen");
      if (main) {
        roomHost = document.createElement("div");
        roomHost.id = "roomDocsStrip";
        roomHost.className = "acd-room-docs";
        roomHost.style.cssText =
          "padding:6px 10px;gap:6px;background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap";
        var header = main.querySelector(".top-bar") || main.querySelector("header") || main.firstElementChild;
        if (header && header.parentNode) header.parentNode.insertBefore(roomHost, header.nextSibling);
        else main.insertBefore(roomHost, main.firstChild);
      }
    }
    if (roomHost) {
      specs.forEach(function (s) {
        if (!document.getElementById("ws" + s.id)) roomHost.appendChild(mkBtn(s, "ws"));
      });
    }
  }

  // Codespace open hardening (display:flex !important)
  function hardenCodespace() {
    var prev = window.openCodePanel;
    if (typeof prev !== "function") return;
    if (prev._acdDocsSafe) return;
    window.openCodePanel = function () {
      var panel = document.getElementById("codePanel");
      if (panel) {
        panel.style.setProperty("display", "flex", "important");
        panel.style.setProperty("flex-direction", "column", "important");
        panel.style.setProperty("z-index", "9999", "important");
      }
      document.body.classList.add("codespace-active");
      document.body.classList.remove("home-active");
      var docs = document.getElementById("gspDocsPanel");
      if (docs) docs.style.display = "none";
      return prev.apply(this, arguments);
    };
    window.openCodePanel._acdDocsSafe = true;
    if (typeof window.acdOpenCodespace !== "function") {
      window.acdOpenCodespace = function (ev) {
        if (ev && ev.preventDefault) ev.preventDefault();
        if (window.openCodePanel) window.openCodePanel();
        return false;
      };
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      injectButtons();
      hardenCodespace();
    });
  } else {
    injectButtons();
    hardenCodespace();
  }
  setTimeout(injectButtons, 500);
  setTimeout(hardenCodespace, 500);
  setTimeout(injectButtons, 1500);
  setTimeout(hardenCodespace, 1500);
  console.log("[acd] Docs UI: real screens · home/room strips separated");
})();
