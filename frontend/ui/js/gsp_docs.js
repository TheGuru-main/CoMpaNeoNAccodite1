/**
 * Accodite Docs — SheetS | DBase | CollabSheet | Presentations
 * Home strip ≠ room strip. Codespace never inherits docs chrome.
 * DBase: collapsible path sidebar + full-bleed grid + name/desc + lookup.
 */
(function () {
  "use strict";

  var KINDS = {
    sheets: { label: "SheetS", icon: "fa-table-cells", api: "sheet", blurb: "54×64 GSP sheet" },
    dbase: { label: "DBase", icon: "fa-database", api: "xlsx", blurb: "Records · meta place · lexicon lookup" },
    collabsheet: { label: "CollabSheet", icon: "fa-people-arrows", api: "workspace", blurb: "Team collab host" },
    presentations: { label: "Presentations", icon: "fa-display", api: "pptx", blurb: "Slide faces" },
  };

  var GRADIENTS = (function () {
    var pairs = [
      ["#0f172a", "#1e3a5f"], ["#1a0533", "#4c1d95"], ["#0c4a6e", "#06b6d4"], ["#14532d", "#22c55e"],
      ["#7c2d12", "#f97316"], ["#4a044e", "#e879f9"], ["#1e1b4b", "#6366f1"], ["#450a0a", "#ef4444"],
      ["#083344", "#14b8a6"], ["#422006", "#eab308"], ["#0f766e", "#99f6e4"], ["#3b0764", "#c084fc"],
      ["#111827", "#374151"], ["#1e3a8a", "#93c5fd"], ["#064e3b", "#6ee7b7"], ["#701a75", "#f0abfc"],
      ["#7f1d1d", "#fca5a5"], ["#713f12", "#fde68a"], ["#164e63", "#67e8f9"], ["#312e81", "#a5b4fc"],
    ];
    return pairs.map(function (p, i) {
      return { id: "g" + String(i).padStart(2, "0"), css: "linear-gradient(135deg," + p[0] + "," + p[1] + ")" };
    });
  })();

  var state = {
    kind: "dbase",
    parentType: "repo",
    parentId: "",
    parentRepo: "",
    docName: "",
    docUid: "",
    data: null,
    nRows: 64,
    nCols: 26,
    gsp: { C: 26, R: 64 },
    slideIndex: 0,
    selected: null,
    sideOpen: true,
    lookup: "",
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
    var roomId = window.currentRoomId || null;
    var inRoom =
      !!roomId &&
      document.body.classList.contains("workspace-active") &&
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
      "/* visibility by body mode */" +
      "body.home-active #homeDocsStrip{display:flex!important}" +
      "body:not(.home-active) #homeDocsStrip{display:none!important}" +
      "body.workspace-active:not(.codespace-active) #roomDocsStrip{display:flex!important}" +
      "body:not(.workspace-active) #roomDocsStrip,body.codespace-active #roomDocsStrip{display:none!important}" +
      "body.codespace-active #gspDocsPanel{display:none!important}" +
      "#homeDocsStrip,#roomDocsStrip{flex-wrap:wrap;gap:6px;align-items:center}" +
      "#gspDocsPanel{font-family:Inter,system-ui,sans-serif!important;display:none;position:fixed;inset:0;z-index:11000;background:#020617;color:#e2e8f0;flex-direction:column}" +
      "#gspDocsPanel.acd-open{display:flex!important}" +
      ".acd-top{display:flex;align-items:center;gap:8px;padding:10px 12px;background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap}" +
      ".acd-btn{border:1px solid #334155;background:#1e293b;color:#e2e8f0;border-radius:10px;padding:8px 12px;font-size:13px;cursor:pointer}" +
      ".acd-btn:hover{border-color:#22d3ee}" +
      ".acd-btn.primary{background:#0e7490;border-color:#06b6d4}" +
      ".acd-btn.active{border-color:#22d3ee;box-shadow:0 0 0 1px #22d3ee}" +
      ".acd-inp{padding:8px 10px;border-radius:10px;border:1px solid #334155;background:#0b1220;color:#fff;font-size:13px}" +
      ".acd-body{display:flex;flex:1;min-height:0}" +
      ".acd-side{width:240px;min-width:240px;background:#0b1220;border-right:1px solid #1e293b;overflow:auto;transition:width .2s,min-width .2s,padding .2s}" +
      ".acd-side.collapsed{width:0;min-width:0;padding:0;border:none;overflow:hidden}" +
      ".acd-side-inner{padding:12px;width:240px}" +
      ".acd-main{flex:1;min-width:0;display:flex;flex-direction:column;overflow:hidden;background:#020617}" +
      ".acd-entry{padding:12px;border-bottom:1px solid #1e293b;background:#0f172a;display:grid;grid-template-columns:1fr 1fr auto;gap:8px;align-items:end}" +
      ".acd-entry label{display:block;font-size:11px;color:#94a3b8;margin-bottom:4px}" +
      ".acd-lookup{padding:8px 12px;border-bottom:1px solid #1e293b;display:flex;gap:8px;align-items:center}" +
      ".acd-grid-wrap{flex:1;overflow:auto;padding:8px}" +
      ".acd-sheet-table{border-collapse:collapse;width:max-content;font-size:12px}" +
      ".acd-sheet-table th{background:#1e293b;color:#94a3b8;padding:6px 8px;border:1px solid #334155;position:sticky;top:0;z-index:1}" +
      ".acd-sheet-table td{min-width:88px;height:30px;border:1px solid #1e293b;padding:4px 6px;color:#e2e8f0;cursor:pointer;background:#0b1220;vertical-align:top}" +
      ".acd-sheet-table td:hover{background:#1e293b}" +
      ".acd-sheet-table td.on{outline:2px solid #22d3ee}" +
      ".acd-sheet-table td.hit{background:#14532d66}" +
      ".acd-meta{font-size:10px;color:#64748b;display:block}" +
      ".acd-doc-item{display:block;width:100%;text-align:left;margin:0 0 6px;padding:10px 12px;border-radius:12px;border:1px solid #1e293b;background:#111827;color:#e2e8f0;cursor:pointer}" +
      ".acd-doc-item:hover,.acd-doc-item.on{border-color:#22d3ee}" +
      ".acd-face{min-height:360px;border-radius:18px;padding:32px;color:#fff;margin:12px}" +
      ".acd-empty{text-align:center;padding:48px 20px;color:#94a3b8}";
    document.head.appendChild(s);
  }

  function ensurePanel() {
    ensureCss();
    var p = document.getElementById("gspDocsPanel");
    if (p) return p;
    p = document.createElement("div");
    p.id = "gspDocsPanel";
    p.innerHTML =
      '<div class="acd-top">' +
      '<button type="button" class="acd-btn" id="gspDocBack">← Back</button>' +
      '<button type="button" class="acd-btn" id="gspSideToggle" title="Paths">☰</button>' +
      '<strong id="gspDocTitle">DBase</strong>' +
      '<span id="gspDocScope" style="color:#94a3b8;font-size:12px"></span>' +
      '<span style="flex:1"></span>' +
      '<input class="acd-inp" id="gspDocNameInput" placeholder="Object / doc name" maxlength="64" style="width:140px" />' +
      '<button type="button" class="acd-btn primary" id="gspDocCreate">Create</button>' +
      "</div>" +
      '<div class="acd-top" id="gspKindBar" style="background:#0b1220"></div>' +
      '<div class="acd-body">' +
      '<aside class="acd-side" id="gspSide"><div class="acd-side-inner" id="gspDocList"></div></aside>' +
      '<main class="acd-main" id="gspDocStage"></main>' +
      "</div>";
    document.body.appendChild(p);

    document.getElementById("gspDocBack").onclick = function () {
      closeDocs();
    };
    document.getElementById("gspSideToggle").onclick = function () {
      state.sideOpen = !state.sideOpen;
      var side = document.getElementById("gspSide");
      if (side) side.classList.toggle("collapsed", !state.sideOpen);
    };
    document.getElementById("gspDocCreate").onclick = function () {
      createDoc();
    };

    var bar = document.getElementById("gspKindBar");
    Object.keys(KINDS).forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "acd-btn";
      b.dataset.kind = k;
      b.innerHTML = '<i class="fa-solid ' + KINDS[k].icon + '"></i> ' + KINDS[k].label;
      b.onclick = function () {
        openKind(k);
      };
      bar.appendChild(b);
    });
    return p;
  }

  function closeDocs() {
    var p = document.getElementById("gspDocsPanel");
    if (p) {
      p.classList.remove("acd-open");
      p.style.display = "none";
    }
  }

  function openKind(kind) {
    if (document.body.classList.contains("codespace-active")) {
      // never under codespace
      document.body.classList.remove("codespace-active");
      var cp = document.getElementById("codePanel");
      if (cp) cp.style.setProperty("display", "none", "important");
    }
    if (kind === "sheet" || kind === "xlsx" || kind === "workspace" || kind === "pptx" || kind === "excel") {
      kind = { sheet: "sheets", xlsx: "dbase", excel: "dbase", workspace: "collabsheet", pptx: "presentations" }[kind] || kind;
    }
    if (!KINDS[kind]) kind = "dbase";
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
    panel.classList.add("acd-open");
    panel.style.display = "flex";
    document.getElementById("gspDocTitle").textContent = KINDS[kind].label;
    document.getElementById("gspDocScope").textContent =
      (state.parentType === "room" ? "Room" : "Home") + " · " + String(state.parentId).slice(0, 24);
    document.querySelectorAll("#gspKindBar .acd-btn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.kind === kind);
    });
    var side = document.getElementById("gspSide");
    if (side) side.classList.toggle("collapsed", !state.sideOpen);
    state.docName = "";
    state.data = null;
    state.selected = null;
    paintEmpty();
    refreshList();
  }

  function paintEmpty() {
    var stage = document.getElementById("gspDocStage");
    if (!stage) return;
    var k = KINDS[state.kind];
    stage.innerHTML =
      '<div class="acd-empty"><div style="font-size:40px;margin-bottom:10px"><i class="fa-solid ' +
      k.icon +
      '"></i></div><h2 style="color:#e2e8f0;margin:0 0 8px">' +
      k.label +
      "</h2><p>" +
      k.blurb +
      "</p><p>Create an object name above, or open a path from the sidebar.</p></div>";
  }

  async function createDoc() {
    var name = (document.getElementById("gspDocNameInput").value || "").trim();
    if (!/^[A-Za-z][A-Za-z0-9_-]{0,62}$/.test(name)) {
      alert("Name must start with a letter (A–Z)");
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
        state.data = { slides: [{ id: "s0", title: name, body: "", gradient: "g00" }] };
      } else if (state.kind === "dbase") {
        state.data = {
          sheets: { Sheet1: { cells: {} } },
          active_sheet: "Sheet1",
          object_name: name,
          object_desc: "",
          cells: {},
        };
      } else {
        state.data = { cells: {}, object_name: name, object_desc: "" };
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
    list.innerHTML = '<div style="color:#94a3b8;font-size:12px;margin-bottom:8px">Paths / objects</div>';
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
        if (state.kind !== "collabsheet" && k && k !== want) return;
        n++;
        var b = document.createElement("button");
        b.type = "button";
        b.className = "acd-doc-item" + ((d.doc_name || d.name) === state.docName ? " on" : "");
        b.innerHTML =
          "<strong>" +
          escapeHtml(d.doc_name || d.name || "?") +
          '</strong><span class="acd-meta">' +
          escapeHtml(k || state.kind) +
          "</span>";
        b.onclick = function () {
          openDoc(d.doc_name || d.name);
        };
        list.appendChild(b);
      });
      if (!n) {
        list.innerHTML += '<div style="color:#64748b;font-size:12px">No objects yet</div>';
      }
    } catch (e) {
      list.innerHTML += '<div style="color:#f87171;font-size:12px">' + escapeHtml(e.message) + "</div>";
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
    refreshList();
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
      '<div style="padding:20px">' +
      "<h3>CollabSheet</h3><p style='color:#94a3b8'>Open a linked surface for this room/home scope.</p>" +
      '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">' +
      '<button type="button" class="acd-btn primary" id="hubDBase">DBase</button>' +
      '<button type="button" class="acd-btn" id="hubSheetS">SheetS</button>' +
      '<button type="button" class="acd-btn" id="hubPres">Presentations</button></div></div>';
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

  function cellText(v) {
    if (v == null) return "";
    if (typeof v === "object") return String(v.value || v.text || "");
    return String(v);
  }

  function cellMeta(v) {
    if (v && typeof v === "object") return v.meta || v.label || "";
    return "";
  }

  function renderSheet() {
    var stage = document.getElementById("gspDocStage");
    var rows = Math.min(state.nRows || 64, 64);
    var cols = Math.min(state.nCols || 54, state.kind === "dbase" ? 40 : 54);
    var cells = activeCells();
    state.data = state.data || {};
    var objName = state.data.object_name || state.docName || "";
    var objDesc = state.data.object_desc || "";

    var html =
      '<div class="acd-entry">' +
      '<div><label>Object name</label><input class="acd-inp" id="objName" style="width:100%" value="' +
      escapeHtml(objName) +
      '" /></div>' +
      '<div><label>Description</label><input class="acd-inp" id="objDesc" style="width:100%" value="' +
      escapeHtml(objDesc) +
      '" placeholder="What this base holds" /></div>' +
      '<button type="button" class="acd-btn primary" id="objSave">Save meta</button></div>';

    html +=
      '<div class="acd-lookup">' +
      '<input class="acd-inp" id="gridLookup" style="flex:1" placeholder="Lookup — lexicon / token / cell text" value="' +
      escapeHtml(state.lookup || "") +
      '" />' +
      '<button type="button" class="acd-btn" id="gridLookupGo">Search</button>' +
      '<span id="lookupHits" style="color:#94a3b8;font-size:12px"></span></div>';

    if (state.kind === "dbase" && state.data.sheets) {
      html += '<div style="padding:8px 12px;display:flex;gap:6px;flex-wrap:wrap">';
      Object.keys(state.data.sheets).forEach(function (sn) {
        var on = sn === (state.data.active_sheet || "Sheet1");
        html +=
          '<button type="button" class="acd-btn' +
          (on ? " active" : "") +
          '" data-sheet="' +
          escapeHtml(sn) +
          '">' +
          escapeHtml(sn) +
          "</button>";
      });
      html += '<button type="button" class="acd-btn" id="addSheet">+ Sheet</button></div>';
    }

    html += '<div class="acd-grid-wrap"><table class="acd-sheet-table"><thead><tr><th></th>';
    for (var c = 0; c < cols; c++) html += "<th>" + c + "</th>";
    html += "</tr></thead><tbody>";
    var q = (state.lookup || "").toLowerCase().trim();
    var hits = 0;
    for (var r = 1; r <= rows; r++) {
      html += "<tr><th>" + r + "</th>";
      for (var c2 = 0; c2 < cols; c2++) {
        var key = r + ":" + c2;
        var raw = cells[key];
        var val = cellText(raw);
        var meta = cellMeta(raw);
        var hit = q && (val.toLowerCase().indexOf(q) >= 0 || String(meta).toLowerCase().indexOf(q) >= 0);
        if (hit) hits++;
        html +=
          '<td data-r="' +
          r +
          '" data-c="' +
          c2 +
          '" class="' +
          (hit ? "hit" : "") +
          '">' +
          escapeHtml(val.slice(0, 40)) +
          (meta ? '<span class="acd-meta">' + escapeHtml(String(meta).slice(0, 28)) + "</span>" : "") +
          "</td>";
      }
      html += "</tr>";
    }
    html += "</tbody></table></div>";
    stage.innerHTML = html;
    var lh = document.getElementById("lookupHits");
    if (lh) lh.textContent = q ? hits + " hits" : "";

    document.getElementById("objSave").onclick = function () {
      state.data.object_name = document.getElementById("objName").value;
      state.data.object_desc = document.getElementById("objDesc").value;
      snapshotSave();
    };
    document.getElementById("gridLookupGo").onclick = function () {
      state.lookup = document.getElementById("gridLookup").value || "";
      renderSheet();
    };
    document.getElementById("gridLookup").onkeydown = function (ev) {
      if (ev.key === "Enter") {
        state.lookup = this.value || "";
        renderSheet();
      }
    };

    stage.querySelectorAll("td[data-r]").forEach(function (td) {
      td.onclick = function () {
        stage.querySelectorAll("td.on").forEach(function (x) {
          x.classList.remove("on");
        });
        td.classList.add("on");
        var r = +td.getAttribute("data-r");
        var c = +td.getAttribute("data-c");
        state.selected = { r: r, c: c };
        var cur = cells[r + ":" + c];
        var val = cellText(cur);
        var meta = cellMeta(cur) || "";
        var next = prompt("Cell " + r + ":" + c + " — value", val);
        if (next == null) return;
        var nextMeta = prompt("Meta / label (optional)", meta);
        if (nextMeta == null) nextMeta = meta;
        writeCell(r, c, next, nextMeta);
      };
    });

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

  async function writeCell(row, col, value, meta) {
    if (!state.docName) return;
    var cells = activeCells();
    cells[row + ":" + col] = {
      value: value,
      meta: meta || "",
      row: row,
      col: col,
      placed: true,
    };
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
        meta: meta || "",
        place: true,
      });
    } catch (e) {
      snapshotSave();
    }
  }

  function renderPresentation() {
    var stage = document.getElementById("gspDocStage");
    var slides = (state.data && state.data.slides) || [{ id: "s0", title: state.docName || "Slide", body: "", gradient: "g00" }];
    state.data = state.data || {};
    state.data.slides = slides;
    if (state.slideIndex >= slides.length) state.slideIndex = 0;
    var s = slides[state.slideIndex];
    var g = GRADIENTS.find(function (x) {
      return x.id === s.gradient;
    }) || GRADIENTS[0];
    stage.innerHTML =
      '<div style="padding:12px;display:flex;gap:8px;align-items:center">' +
      '<button type="button" class="acd-btn" id="prevFace">←</button><strong>Face ' +
      (state.slideIndex + 1) +
      "/" +
      slides.length +
      '</strong><button type="button" class="acd-btn" id="nextFace">→</button>' +
      '<button type="button" class="acd-btn primary" id="addFace">+ Face</button></div>' +
      '<div class="acd-face" style="background:' +
      g.css +
      '"><div contenteditable="true" id="faceTitle" style="font-size:28px;font-weight:800">' +
      escapeHtml(s.title || "") +
      '</div><div contenteditable="true" id="faceBody" style="margin-top:12px;min-height:120px">' +
      escapeHtml(s.body || "") +
      "</div></div>";
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
      snapshotSave();
      renderPresentation();
    };
    document.getElementById("faceTitle").onblur = function () {
      s.title = this.innerText;
      snapshotSave();
    };
    document.getElementById("faceBody").onblur = function () {
      s.body = this.innerText;
      snapshotSave();
    };
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
  window.acdCloseDocs = closeDocs;

  function mkBtn(s, prefix) {
    var id = prefix + s.id;
    var existing = document.getElementById(id);
    if (existing) return existing;
    var b = document.createElement("button");
    b.type = "button";
    b.id = id;
    b.className = "acd-btn";
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

    // HOME only under homeHub
    var hub = document.getElementById("homeHub") || document.getElementById("homeActions");
    var homeHost = document.getElementById("homeDocsStrip");
    if (!homeHost && hub) {
      homeHost = document.createElement("div");
      homeHost.id = "homeDocsStrip";
      homeHost.style.cssText = "margin-top:10px;width:100%";
      hub.appendChild(homeHost);
    }
    // strip any docs buttons wrongly left in header/nav
    document.querySelectorAll("#mainNav [id$=btnDBase], #mainNav [id$=btnSheetS], .top-nav [id^=homebtn], .top-nav [id^=wsbtn]").forEach(function (n) {
      try {
        n.remove();
      } catch (e) {}
    });
    if (homeHost) {
      specs.forEach(function (s) {
        if (!document.getElementById("home" + s.id)) homeHost.appendChild(mkBtn(s, "home"));
      });
    }

    // ROOM only — dedicated strip under mainScreen header
    var main = document.getElementById("mainScreen");
    var roomHost = document.getElementById("roomDocsStrip");
    if (!roomHost && main) {
      roomHost = document.createElement("div");
      roomHost.id = "roomDocsStrip";
      roomHost.style.cssText = "padding:6px 10px;background:#0f172a;border-bottom:1px solid #1e293b";
      var header = main.querySelector(".top-bar") || main.querySelector("header");
      if (header && header.parentNode) header.parentNode.insertBefore(roomHost, header.nextSibling);
      else main.insertBefore(roomHost, main.firstChild);
    }
    if (roomHost) {
      specs.forEach(function (s) {
        if (!document.getElementById("ws" + s.id)) roomHost.appendChild(mkBtn(s, "ws"));
      });
    }
  }

  function hardenCodespace() {
    var prev = window.openCodePanel;
    if (typeof prev !== "function" || prev._acdDocsSafe2) return;
    window.openCodePanel = function () {
      closeDocs();
      document.body.classList.add("codespace-active");
      document.body.classList.remove("home-active");
      var panel = document.getElementById("codePanel");
      if (panel) {
        panel.style.setProperty("display", "flex", "important");
        panel.style.setProperty("flex-direction", "column", "important");
        panel.style.setProperty("z-index", "9999", "important");
      }
      return prev.apply(this, arguments);
    };
    window.openCodePanel._acdDocsSafe2 = true;

    window.acdOpenCodespace = function (ev) {
      if (ev && ev.preventDefault) {
        ev.preventDefault();
        ev.stopPropagation();
      }
      closeDocs();
      document.body.classList.add("codespace-active");
      document.body.classList.remove("home-active");
      if (typeof window.openCodePanel === "function") window.openCodePanel();
      var panel = document.getElementById("codePanel");
      if (panel) panel.style.setProperty("display", "flex", "important");
      return false;
    };

    // back from codespace → restore classes via updateInputVisibility
    document.addEventListener(
      "click",
      function (ev) {
        var t = ev.target && ev.target.closest && ev.target.closest("#codeBack, #btnCodeBack, [data-code-back]");
        if (!t) return;
        document.body.classList.remove("codespace-active");
        var panel = document.getElementById("codePanel");
        if (panel) panel.style.setProperty("display", "none", "important");
        if (typeof window.updateInputVisibility === "function") window.updateInputVisibility();
      },
      true
    );
  }

  function boot() {
    injectButtons();
    hardenCodespace();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 600);
  setTimeout(boot, 1600);
  console.log("[acd] docs v3 — sidebar paths, full grid, home/room/codespace isolation");
})();
