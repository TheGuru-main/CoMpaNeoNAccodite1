/**
 * Accodite DocsShell — SheetS | DBase | CollabSheet | Presentations
 * Does NOT open/close team sidebar rooms (currentRoomId untouched).
 * parent_type: room (in team workspace) | repo (codespace) | org (home general)
 */
(function () {
  "use strict";

  var KIND_UI = {
    sheets: { label: "SheetS", icon: "fa-table-cells", api: "sheet", gridlines: true },
    dbase: { label: "DBase", icon: "fa-database", api: "xlsx", gridlines: true, configurable: true },
    collabsheet: { label: "CollabSheet", icon: "fa-people-arrows", api: "workspace", gridlines: true, place: true },
    presentations: { label: "Presentations", icon: "fa-display", api: "presentations", canvas: true },
  };

  // 70 linear gradients for Presentation book faces
  var GRADIENTS = (function () {
    var stops = [
      ["#0f172a", "#1e3a5f"], ["#1a0533", "#4c1d95"], ["#0c4a6e", "#06b6d4"],
      ["#14532d", "#22c55e"], ["#7c2d12", "#f97316"], ["#4a044e", "#e879f9"],
      ["#1e1b4b", "#6366f1"], ["#450a0a", "#ef4444"], ["#083344", "#14b8a6"],
      ["#422006", "#eab308"], ["#0f766e", "#99f6e4"], ["#3b0764", "#c084fc"],
      ["#111827", "#374151"], ["#1e3a8a", "#93c5fd"], ["#064e3b", "#6ee7b7"],
      ["#701a75", "#f0abfc"], ["#7f1d1d", "#fca5a5"], ["#713f12", "#fde68a"],
      ["#164e63", "#67e8f9"], ["#312e81", "#a5b4fc"], ["#134e4a", "#5eead4"],
      ["#4c0519", "#fb7185"], ["#1c1917", "#a8a29e"], ["#172554", "#60a5fa"],
      ["#365314", "#a3e635"], ["#581c87", "#d8b4fe"], ["#9a3412", "#fdba74"],
      ["#0e7490", "#a5f3fc"], ["#1e293b", "#64748b"], ["#831843", "#f9a8d4"],
      ["#3f6212", "#bef264"], ["#1e3a8a", "#1d4ed8"], ["#0f172a", "#f43f5e"],
      ["#022c22", "#10b981"], ["#2e1065", "#7c3aed"], ["#431407", "#c2410c"],
      ["#082f49", "#0ea5e9"], ["#1a2e05", "#65a30d"], ["#4c1d95", "#ddd6fe"],
      ["#881337", "#ffe4e6"], ["#0c4a6e", "#e0f2fe"], ["#365314", "#ecfccb"],
      ["#500724", "#fce7f3"], ["#1e1b4b", "#e0e7ff"], ["#713f12", "#fffbeb"],
      ["#134e4a", "#ccfbf1"], ["#7c2d12", "#ffedd5"], ["#312e81", "#eef2ff"],
      ["#14532d", "#dcfce7"], ["#9f1239", "#fff1f2"], ["#155e75", "#cffafe"],
      ["#3b0764", "#f5f3ff"], ["#78350f", "#fef3c7"], ["#0f766e", "#f0fdfa"],
      ["#1e3a5f", "#dbeafe"], ["#4a044e", "#faf5ff"], ["#7f1d1d", "#fef2f2"],
      ["#052e16", "#f0fdf4"], ["#1e293b", "#f8fafc"], ["#0c4a6e", "#f0f9ff"],
      ["#422006", "#fefce8"], ["#2e1065", "#faf5ff"], ["#881337", "#fdf2f8"],
      ["#164e63", "#ecfeff"], ["#365314", "#f7fee7"], ["#4c0519", "#fff1f2"],
      ["#083344", "#f0fdfa"], ["#1a0533", "#faf5ff"], ["#450a0a", "#fef2f2"],
      ["#0f172a", "#22d3ee"], ["#0f172a", "#a3e635"],
    ];
    return stops.map(function (s, i) {
      return {
        id: "g" + String(i).padStart(2, "0"),
        css: "linear-gradient(135deg, " + s[0] + " 0%, " + s[1] + " 100%)",
      };
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
    meta: null,
    nRows: 64,
    nCols: 54,
    // DBase GSP defaults (configurable)
    gsp: { L: 0, S: 0, c: 0, K: 5, D: 8, C: 26, R: 64 },
    slideIndex: 0,
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
    var u = KIND_UI[k] || KIND_UI.sheets;
    return u.api;
  }

  /** Scope: in team room → room; else codespace repo; else org/home */
  function resolveParent() {
    var roomId = window.currentRoomId || (typeof currentRoomId !== "undefined" ? currentRoomId : null);
    if (roomId && document.body.classList.contains("workspace-active") &&
        !document.body.classList.contains("codespace-active") &&
        !document.body.classList.contains("home-active")) {
      return { parentType: "room", parentId: String(roomId), parentRepo: "" };
    }
    var repo = "";
    try {
      if (window.acdTermApi && window.acdTermApi.getRepo) repo = window.acdTermApi.getRepo() || "";
    } catch (e) {}
    if (!repo) {
      try {
        repo = sessionStorage.getItem("acd_active_repo") || "";
      } catch (e) {}
    }
    if (repo) return { parentType: "repo", parentId: repo, parentRepo: repo };
    return { parentType: "repo", parentId: "HomeDocs", parentRepo: "HomeDocs" };
  }

  function ensurePanel() {
    var p = document.getElementById("gspDocsPanel");
    if (p) return p;
    p = document.createElement("div");
    p.id = "gspDocsPanel";
    p.style.cssText =
      "display:none;position:fixed;inset:0;z-index:12000;background:#070b14;color:#e2e8f0;" +
      "flex-direction:column;font-family:system-ui,sans-serif;";
    p.innerHTML =
      '<div style="display:flex;gap:6px;align-items:center;padding:8px 10px;border-bottom:1px solid #1e293b;flex-wrap:wrap;background:#0f172a">' +
      '<button type="button" id="gspDocBack" class="btn">← Back</button>' +
      '<strong id="gspDocTitle">Docs</strong>' +
      '<span id="gspKindSwitch" style="display:flex;gap:4px;flex-wrap:wrap"></span>' +
      '<span id="gspDocMeta" style="opacity:0.7;font-size:11px;flex:1;min-width:120px"></span>' +
      '<input id="gspDocNameInput" placeholder="DocName" maxlength="64" ' +
      'style="max-width:130px;padding:6px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#e2e8f0" />' +
      '<button type="button" id="gspDocCreate" class="btn">Create</button>' +
      '<button type="button" id="gspDocRefresh" class="btn">Refresh</button>' +
      "</div>" +
      '<div id="gspConfigBar" style="display:none;padding:6px 10px;border-bottom:1px solid #1e293b;font-size:12px;gap:8px;flex-wrap:wrap;align-items:center;background:#0b1220"></div>' +
      '<div style="display:flex;flex:1;min-height:0">' +
      '<aside id="gspDocList" style="width:200px;overflow:auto;border-right:1px solid #1e293b;padding:8px;font-size:13px;background:#0b1220"></aside>' +
      '<main id="gspDocGridWrap" style="flex:1;overflow:auto;padding:8px;background:#070b14"></main>' +
      "</div>" +
      '<div id="gspShellStatus" style="padding:6px 12px;font-size:11px;opacity:0.65;border-top:1px solid #1e293b"></div>';
    document.body.appendChild(p);

    document.getElementById("gspDocBack").onclick = function () {
      p.style.display = "none";
      // never clear currentRoomId
    };
    document.getElementById("gspDocCreate").onclick = function () {
      createDoc();
    };
    document.getElementById("gspDocRefresh").onclick = function () {
      refreshList();
    };

    var sw = document.getElementById("gspKindSwitch");
    Object.keys(KIND_UI).forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "btn";
      b.dataset.kind = k;
      b.innerHTML = '<i class="fa-solid ' + KIND_UI[k].icon + '"></i> ' + KIND_UI[k].label;
      b.onclick = function () {
        openKind(k);
      };
      sw.appendChild(b);
    });
    return p;
  }

  function setStatus(msg) {
    var el = document.getElementById("gspShellStatus");
    if (el) el.textContent = msg || "";
  }

  function openKind(kind) {
    kind = kind || "sheets";
    if (kind === "sheet" || kind === "excel" || kind === "xlsx" || kind === "workspace" || kind === "pptx") {
      kind = {
        sheet: "sheets",
        excel: "dbase",
        xlsx: "dbase",
        workspace: "collabsheet",
        pptx: "presentations",
      }[kind] || kind;
    }
    if (!KIND_UI[kind]) kind = "sheets";
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
    document.getElementById("gspDocTitle").textContent = KIND_UI[kind].label;
    document.getElementById("gspDocMeta").textContent =
      state.parentType + ":" + (state.parentId || "").slice(0, 24);

    var cfg = document.getElementById("gspConfigBar");
    if (kind === "dbase") {
      cfg.style.display = "flex";
      cfg.innerHTML =
        "DBase grid C×R " +
        '<input id="gspCfgC" type="number" min="2" max="200" value="' +
        state.gsp.C +
        '" style="width:56px;margin:0 4px" />×' +
        '<input id="gspCfgR" type="number" min="2" max="500" value="' +
        state.gsp.R +
        '" style="width:56px;margin:0 4px" />' +
        " K<input id=\"gspCfgK\" type=\"number\" min=\"1\" value=\"" +
        state.gsp.K +
        '" style="width:48px;margin:0 4px" />' +
        " D<input id=\"gspCfgD\" type=\"number\" min=\"1\" value=\"" +
        state.gsp.D +
        '" style="width:48px;margin:0 4px" />' +
        " c<input id=\"gspCfgc\" type=\"number\" min=\"0\" value=\"" +
        state.gsp.c +
        '" style="width:48px;margin:0 4px" />' +
        '<button type="button" class="btn" id="gspCfgApply">Apply</button>';
      document.getElementById("gspCfgApply").onclick = function () {
        state.gsp.C = +document.getElementById("gspCfgC").value || 26;
        state.gsp.R = +document.getElementById("gspCfgR").value || 64;
        state.gsp.K = +document.getElementById("gspCfgK").value || 5;
        state.gsp.D = +document.getElementById("gspCfgD").value || 8;
        state.gsp.c = +document.getElementById("gspCfgc").value || 0;
        state.nCols = state.gsp.C;
        state.nRows = state.gsp.R;
        setStatus("DBase config C=" + state.gsp.C + " R=" + state.gsp.R + " K=" + state.gsp.K + " D=" + state.gsp.D);
        if (state.data) renderStage();
      };
    } else {
      cfg.style.display = "none";
      cfg.innerHTML = "";
    }

    setStatus(
      KIND_UI[kind].label +
        (KIND_UI[kind].canvas
          ? " · blank canvas · 70 gradients"
          : " · " + state.nCols + "×" + state.nRows) +
        " · parent " +
        state.parentType
    );
    refreshList();
  }

  async function createDoc() {
    var name = (document.getElementById("gspDocNameInput").value || "").trim();
    if (!/^[A-Za-z][A-Za-z0-9_-]{0,62}$/.test(name)) {
      alert("Doc name must start with a letter (A–Z); no leading symbols");
      return;
    }
    var par = resolveParent();
    state.parentType = par.parentType;
    state.parentId = par.parentId;
    state.parentRepo = par.parentRepo || par.parentId;
    try {
      if (window.acdFetchGspChain) {
        try {
          var ch = await window.acdFetchGspChain(name, "en");
          state.gsp.L = ch.L || (name.length);
          state.gsp.S = ch.S || 0;
          if (ch.start_row) state.gsp.start_row = ch.start_row;
        } catch (e) {
          state.gsp.L = name.length;
        }
      } else {
        state.gsp.L = name.length;
      }
      var body = {
        scope: "user",
        parent_type: state.parentType === "room" ? "room" : "repo",
        parent_repo: state.parentRepo || state.parentId,
        parent_id: state.parentId,
        doc_name: name,
        kind: apiKind(state.kind),
        n_rows: state.nRows,
        n_cols: state.nCols,
      };
      var res = await api("/sandbox/docs", "POST", body);
      state.docName = name;
      state.docUid = res.doc_uid || "";
      state.meta = res;
      if (state.kind === "presentations") {
        state.data = {
          slides: [{ id: "s0", title: name, body: "", gradient: "g00", blocks: [] }],
        };
      } else {
        state.data = { cells: {}, n_rows: state.nRows, n_cols: state.nCols, gsp: state.gsp };
      }
      setStatus("created " + name + " uid=" + (state.docUid || "").slice(0, 16));
      await refreshList();
      renderStage();
    } catch (e) {
      alert("Create failed: " + e.message);
    }
  }

  async function refreshList() {
    var list = document.getElementById("gspDocList");
    if (!list) return;
    list.innerHTML = "<div style='opacity:0.6'>Loading…</div>";
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
      var docs = data.docs || data.documents || data || [];
      if (!Array.isArray(docs)) docs = [];
      var want = apiKind(state.kind);
      list.innerHTML = "";
      var title = document.createElement("div");
      title.style.cssText = "font-size:11px;opacity:0.6;margin-bottom:6px";
      title.textContent = "DOCS · " + KIND_UI[state.kind].label;
      list.appendChild(title);
      docs.forEach(function (d) {
        var k = d.kind || d.doc_kind || "";
        if (k && k !== want && !(want === "presentations" && k === "pptx")) {
          /* show all for collabsheet host */
          if (state.kind !== "collabsheet") return;
        }
        var row = document.createElement("button");
        row.type = "button";
        row.className = "btn";
        row.style.cssText = "display:block;width:100%;text-align:left;margin:2px 0;font-size:12px";
        row.textContent = (d.doc_name || d.name || "?") + (k ? " · " + k : "");
        row.onclick = function () {
          openDoc(d.doc_name || d.name, d);
        };
        list.appendChild(row);
      });
      if (!list.querySelectorAll("button").length) {
        list.innerHTML += "<div style='opacity:0.5;font-size:12px'>No docs yet — Create</div>";
      }
    } catch (e) {
      list.innerHTML = "<div style='color:#f87171;font-size:12px'>" + e.message + "</div>";
    }
  }

  async function openDoc(name, meta) {
    state.docName = name;
    state.meta = meta || {};
    state.docUid = (meta && (meta.doc_uid || meta.uid)) || "";
    try {
      var data = await api(
        "/sandbox/docs/get?parent_repo=" +
          encodeURIComponent(state.parentRepo || state.parentId) +
          "&parent_type=" +
          encodeURIComponent(state.parentType === "room" ? "room" : "repo") +
          "&parent_id=" +
          encodeURIComponent(state.parentId) +
          "&doc_name=" +
          encodeURIComponent(name) +
          "&scope=user"
      );
      state.data = (data && data.data) || data || { cells: {} };
      if (state.kind === "presentations" && !state.data.slides) {
        state.data.slides = [{ id: "s0", title: name, body: "", gradient: "g00", blocks: [] }];
      }
      renderStage();
    } catch (e) {
      // local-only render if API missing get
      state.data = state.data || { cells: {}, slides: [{ id: "s0", title: name, body: "", gradient: "g00", blocks: [] }] };
      renderStage();
      setStatus("open offline/partial: " + e.message);
    }
  }

  function gspFragments() {
    var C = state.gsp.C || state.nCols || 26;
    var R = state.gsp.R || state.nRows || 64;
    var K = state.gsp.K || 5;
    var D = state.gsp.D || 8;
    var c0 = state.gsp.c || 0;
    var L = state.gsp.L || (state.docName || "").length || 1;
    var S = state.gsp.S || 1;
    var start = ((L + S - 1) % R) + 1;
    var fr = [];
    for (var k = 0; k < K; k++) {
      fr.push({
        k: k,
        row: ((start - 1 + k * D) % R) + 1,
        col: (c0 + k) % C,
      });
    }
    return { start_row: start, fragments: fr };
  }

  function renderStage() {
    var wrap = document.getElementById("gspDocGridWrap");
    if (!wrap) return;
    if (state.kind === "presentations") {
      renderPresentation(wrap);
      return;
    }
    renderGrid(wrap);
  }

  function activeCells() {
    if (state.kind === "dbase" && state.data && state.data.sheets) {
      var sn = state.data.active_sheet || "Sheet1";
      state.data.sheets[sn] = state.data.sheets[sn] || { cells: {} };
      return state.data.sheets[sn].cells;
    }
    state.data = state.data || { cells: {} };
    state.data.cells = state.data.cells || {};
    return state.data.cells;
  }

  function renderGrid(wrap) {
    var rows = state.nRows || 64;
    var cols = state.nCols || 54;
    if (state.kind === "dbase" && state.data && !state.data.sheets) {
      state.data.sheets = { Sheet1: { cells: state.data.cells || {} } };
      state.data.active_sheet = "Sheet1";
    }
    var cells = activeCells();
    var fr = state.kind === "dbase" ? gspFragments() : null;
    var placeSet = {};
    if (fr) {
      fr.fragments.forEach(function (f) {
        placeSet[f.row + ":" + f.col] = f.k;
      });
    }

    var sheetTabs = "";
    if (state.kind === "dbase") {
      var sheets = (state.data && state.data.sheets) || { Sheet1: { cells: {} } };
      var active = (state.data && state.data.active_sheet) || "Sheet1";
      sheetTabs = '<div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">';
      Object.keys(sheets).forEach(function (sn) {
        sheetTabs +=
          '<button type="button" class="btn" data-sheet="' +
          sn +
          '" style="font-size:11px;' +
          (sn === active ? "border-color:#22d3ee" : "") +
          '">' +
          sn +
          "</button>";
      });
      sheetTabs +=
        '<button type="button" class="btn" id="gspAddSheet" style="font-size:11px">+ Sheet</button></div>';
      sheetTabs +=
        '<div style="display:flex;gap:6px;margin-bottom:8px;align-items:center">' +
        '<span id="gspCellRef" style="min-width:48px;font-size:12px;color:#22d3ee">A1</span>' +
        '<input id="gspFormulaBar" placeholder="value or =formula" style="flex:1;padding:6px 8px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#e2e8f0" />' +
        '<button type="button" class="btn" id="gspFormulaApply">Apply</button></div>';
    }
    var html =
      '<div style="margin-bottom:8px;font-size:12px;opacity:0.8">' +
      (state.docName || "(new)") +
      (fr ? " · start_row=" + fr.start_row + " · K=" + fr.fragments.length : "") +
      "</div>" +
      sheetTabs;
    html +=
      '<div style="overflow:auto;max-height:calc(100vh - 160px)">' +
      '<table style="border-collapse:collapse;font-size:11px">';
    html += "<tr><th></th>";
    for (var c = 0; c < Math.min(cols, 54); c++) {
      html +=
        '<th style="padding:2px 4px;border:1px solid #1e293b;color:#64748b">' + c + "</th>";
    }
    html += "</tr>";
    for (var r = 1; r <= Math.min(rows, 64); r++) {
      html +=
        '<tr><th style="padding:2px 4px;border:1px solid #1e293b;color:#64748b">' + r + "</th>";
      for (var c2 = 0; c2 < Math.min(cols, 54); c2++) {
        var key = r + ":" + c2;
        var val = (cells[key] && (cells[key].value || cells[key])) || "";
        if (typeof val === "object") val = val.value || "";
        var bg = placeSet[key] != null ? "background:#14532d33;" : "";
        html +=
          '<td data-r="' +
          r +
          '" data-c="' +
          c2 +
          '" style="min-width:28px;height:22px;border:1px solid #1e293b;padding:2px;' +
          bg +
          'cursor:pointer" title="' +
          key +
          '">' +
          escapeHtml(String(val).slice(0, 12)) +
          "</td>";
      }
      html += "</tr>";
    }
    html += "</table></div>";
    wrap.innerHTML = html;
    wrap.querySelectorAll("td[data-r]").forEach(function (td) {
      td.onclick = function () {
        var r = +td.getAttribute("data-r");
        var c = +td.getAttribute("data-c");
        var cur = cells[r + ":" + c];
        var prev = (cur && (cur.value || cur)) || "";
        var v = prompt("Cell " + r + ":" + c, typeof prev === "string" ? prev : "");
        if (v == null) return;
        writeCell(r, c, v, state.kind === "collabsheet");
      };
    });
  }

  async function writeCell(row, col, value, place) {
    if (!state.docName) {
      alert("Create or open a doc first");
      return;
    }
    var cells = activeCells();
    cells[row + ":" + col] = { value: value, row: row, col: col, placed: !!place };
    if (state.kind === "dbase") {
      var sn = state.data.active_sheet || "Sheet1";
      state.data.sheets = state.data.sheets || {};
      state.data.sheets[sn] = state.data.sheets[sn] || { cells: {} };
      state.data.sheets[sn].cells = cells;
    } else {
      state.data.cells = cells;
    }
    renderStage();
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
        place: !!place,
      });
      setStatus("saved " + row + ":" + col);
    } catch (e) {
      setStatus("local only: " + e.message);
    }
  }

  function renderPresentation(wrap) {
    var slides = (state.data && state.data.slides) || [
      { id: "s0", title: state.docName || "Slide", body: "", gradient: "g00", blocks: [] },
    ];
    if (state.slideIndex >= slides.length) state.slideIndex = 0;
    var s = slides[state.slideIndex];
    var g = GRADIENTS.find(function (x) {
      return x.id === s.gradient;
    }) || GRADIENTS[0];

    var html =
      '<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;align-items:center">' +
      '<button type="button" class="btn" id="gspSlidePrev">←</button>' +
      "<span>Face " +
      (state.slideIndex + 1) +
      "/" +
      slides.length +
      "</span>" +
      '<button type="button" class="btn" id="gspSlideNext">→</button>' +
      '<button type="button" class="btn" id="gspSlideAdd">+ Face</button>' +
      '<label style="font-size:12px">Gradient ' +
      '<select id="gspGradSel"></select></label>' +
      "</div>";
    html +=
      '<div id="gspFace" style="min-height:320px;border-radius:12px;padding:28px;background:' +
      g.css +
      ';color:#f8fafc;box-shadow:0 8px 30px #0006">' +
      '<div contenteditable="true" id="gspFaceTitle" style="font-size:1.6rem;font-weight:700;outline:none;margin-bottom:12px">' +
      escapeHtml(s.title || "") +
      "</div>" +
      '<div contenteditable="true" id="gspFaceBody" style="font-size:1rem;line-height:1.5;outline:none;min-height:120px">' +
      escapeHtml(s.body || "Tap to write…") +
      "</div></div>";
    html +=
      '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap" id="gspGradStrip"></div>';
    wrap.innerHTML = html;

    var sel = document.getElementById("gspGradSel");
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
      renderPresentation(wrap);
    };

    var strip = document.getElementById("gspGradStrip");
    GRADIENTS.slice(0, 24).forEach(function (gg) {
      var b = document.createElement("button");
      b.type = "button";
      b.title = gg.id;
      b.style.cssText =
        "width:28px;height:28px;border-radius:6px;border:2px solid " +
        (gg.id === s.gradient ? "#22d3ee" : "#334155") +
        ";background:" +
        gg.css +
        ";cursor:pointer";
      b.onclick = function () {
        s.gradient = gg.id;
        persistSlides(slides);
        renderPresentation(wrap);
      };
      strip.appendChild(b);
    });

    document.getElementById("gspSlidePrev").onclick = function () {
      state.slideIndex = (state.slideIndex - 1 + slides.length) % slides.length;
      renderPresentation(wrap);
    };
    document.getElementById("gspSlideNext").onclick = function () {
      state.slideIndex = (state.slideIndex + 1) % slides.length;
      renderPresentation(wrap);
    };
    document.getElementById("gspSlideAdd").onclick = function () {
      slides.push({
        id: "s" + slides.length,
        title: "Face " + (slides.length + 1),
        body: "",
        gradient: "g00",
        blocks: [],
      });
      state.slideIndex = slides.length - 1;
      persistSlides(slides);
      renderPresentation(wrap);
    };
    document.getElementById("gspFaceTitle").onblur = function () {
      s.title = this.innerText;
      persistSlides(slides);
    };
    document.getElementById("gspFaceBody").onblur = function () {
      s.body = this.innerText;
      persistSlides(slides);
    };
  }

  function persistSlides(slides) {
    state.data = state.data || {};
    state.data.slides = slides;
    setStatus("Presentation faces=" + slides.length + " · gradient=" + (slides[state.slideIndex] || {}).gradient);
    snapshotSave();
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Public API — names locked
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
  // aliases
  window.acdOpenSheet = window.acdOpenSheetS;
  window.acdOpenExcel = window.acdOpenDBase;
  window.acdOpenWorkspaceGrid = window.acdOpenCollabSheet;
  window.acdGspDocs = {
    openKind: openKind,
    kinds: KIND_UI,
    gradients: GRADIENTS,
  };

  function injectButtons() {
    var specs = [
      { id: "btnSheetS", label: "SheetS", icon: "fa-table-cells", fn: "acdOpenSheetS" },
      { id: "btnDBase", label: "DBase", icon: "fa-database", fn: "acdOpenDBase" },
      { id: "btnCollabSheet", label: "CollabSheet", icon: "fa-people-arrows", fn: "acdOpenCollabSheet" },
      { id: "btnPresentations", label: "Presentations", icon: "fa-display", fn: "acdOpenPresentations" },
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
        b.innerHTML = '<i class="fa-solid ' + s.icon + '"></i> ' + s.label;
        b.style.margin = "0 4px";
        b.onclick = function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          if (window[s.fn]) window[s.fn]();
        };
        parent.appendChild(b);
      });
    }
    addTo(document.getElementById("homeActions") || document.getElementById("homeHub"), "home");
    addTo(document.querySelector("#mainScreen .top-nav") || document.getElementById("mainNav"), "ws");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", injectButtons);
  else injectButtons();
  setTimeout(injectButtons, 600);
  setTimeout(injectButtons, 1500);
  console.log("[acd] DocsShell SheetS|DBase|CollabSheet|Presentations");
})();
