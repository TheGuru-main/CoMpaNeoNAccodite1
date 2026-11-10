/**
 * Accodite Docs — SheetS | DBase | CollabSheet | Presentations
 * Home strip ≠ room strip. Codespace never inherits docs chrome.
 * DBase: collapsible path sidebar + full-bleed grid + name/desc + lookup.
 */
(function () {
  "use strict";

  var KIND_THEME = {
    sheets: {
      bar: "linear-gradient(105deg, #6b7280 0%, #9ca3af 35%, #bae6fd 70%, #7dd3fc 100%)",
      accent: "#38bdf8",
      side: "linear-gradient(180deg, #374151 0%, #1f2937 55%, #0c4a6e 100%)",
      cell: "linear-gradient(180deg, #4b5563 0%, #64748b 100%)",
    },
    dbase: {
      bar: "linear-gradient(105deg, #4b5563 0%, #6b7280 30%, #e0f2fe 65%, #7dd3fc 100%)",
      accent: "#0ea5e9",
      side: "linear-gradient(180deg, #1f2937 0%, #334155 50%, #0369a1 100%)",
      cell: "linear-gradient(180deg, #475569 0%, #38bdf8 100%)",
    },
    collabsheet: {
      bar: "linear-gradient(105deg, #94a3b8 0%, #cbd5e1 40%, #bae6fd 75%, #38bdf8 100%)",
      accent: "#0284c7",
      side: "linear-gradient(180deg, #64748b 0%, #475569 45%, #0ea5e9 100%)",
      cell: "linear-gradient(180deg, #94a3b8 0%, #7dd3fc 100%)",
    },
    presentations: {
      bar: "linear-gradient(105deg, #64748b 0%, #94a3b8 40%, #e0f2fe 100%)",
      accent: "#38bdf8",
      side: "linear-gradient(180deg, #334155 0%, #1e293b 100%)",
      cell: "linear-gradient(180deg, #475569 0%, #94a3b8 100%)",
    },
  };

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
    pendingMedia: null,
  };

  function token() {
    try {
      return localStorage.getItem("coMpaNeoN_token") || localStorage.getItem("token") || "";
    } catch (e) {
      return "";
    }
  }

  async function api(path, method, body) {
    var h = { "Content-Type": "application/json" };
    var tok = token();
    if (tok) h.Authorization = "Bearer " + tok;
    var opt = { method: method || "GET", headers: h };
    if (body != null && method && method !== "GET") opt.body = JSON.stringify(body);
    var res = await fetch(path, opt);
    var text = await res.text();
    var data;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = { raw: text }; }
    if (!res.ok) throw new Error((data && (data.detail || data.error || data.message)) || text || ("HTTP " + res.status));
    return data;
  }

  async function apiUpload(path, formData) {
    var h = {};
    var tok = token();
    if (tok) h.Authorization = "Bearer " + tok;
    // do NOT set Content-Type — browser sets multipart boundary
    var res = await fetch(path, { method: "POST", headers: h, body: formData });
    var text = await res.text();
    var data;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = { raw: text }; }
    if (!res.ok) throw new Error((data && (data.detail || data.error || data.message)) || text || ("HTTP " + res.status));
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
      "#homeDocsStrip,#roomDocsStrip{flex-wrap:wrap;gap:6px;align-items:center}#homebtnSheetS,.homebtnSheetS,button#homebtnSheetS{background:linear-gradient(105deg,#6b7280 0%,#bae6fd 100%)!important;border:none;color:#0f172a}#homebtnDBase,button#homebtnDBase{background:linear-gradient(105deg,#4b5563 0%,#7dd3fc 100%)!important;border:none;color:#0f172a}#homebtnCollabSheet,button#homebtnCollabSheet{background:linear-gradient(105deg,#94a3b8 0%,#38bdf8 100%)!important;border:none;color:#0f172a}" +
      "#gspDocsPanel{font-family:Inter,system-ui,sans-serif!important;display:none;position:fixed;inset:0;z-index:11000;background:#020617;color:#e2e8f0;flex-direction:column}" +
      "#gspDocsPanel.acd-open{display:flex!important}" +
      ".acd-top{display:flex;align-items:center;gap:8px;padding:10px 12px;background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap}" +
      ".acd-btn{border:1px solid #334155;background:#1e293b;color:#e2e8f0;border-radius:10px;padding:8px 12px;font-size:13px;cursor:pointer}" +
      ".acd-btn:hover{border-color:#22d3ee}" +
      ".acd-btn.primary{background:#0e7490;border-color:#06b6d4}" +
      ".acd-btn.active{border-color:#e0f2fe;box-shadow:0 0 0 1px var(--acd-accent,#38bdf8)}" +
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
      ".acd-sheet-table td{min-width:88px;height:30px;border:1px solid #334155;padding:4px 6px;color:#f8fafc;cursor:pointer;background:var(--acd-cell-grad,#4b5563);vertical-align:top}" +
      ".acd-sheet-table td:hover{background:#1e293b}" +
      ".acd-sheet-table td.on{outline:2px solid #22d3ee}" +
      ".acd-sheet-table td.hit{background:#14532d66}" +
      ".acd-meta{font-size:10px;color:#64748b;display:block}" +
      ".acd-doc-item{display:block;width:100%;text-align:left;margin:0 0 6px;padding:10px 12px;border-radius:12px;border:1px solid #1e293b;background:#111827;color:#e2e8f0;cursor:pointer}" +
      ".acd-doc-item:hover,.acd-doc-item.on{border-color:#22d3ee}" +
      ".acd-face{min-height:360px;border-radius:18px;padding:32px;color:#fff;margin:12px}" +
      ".acd-empty{text-align:center;padding:48px 20px;color:#94a3b8}" +
      ".acd-cell.placed{outline:2px solid #22d3ee;box-shadow:0 0 0 1px #22d3ee inset}" +
      ".acd-grid-wrap{overflow:auto;max-height:calc(100vh - 220px);-webkit-overflow-scrolling:touch}" +
      ".acd-grid{display:grid;gap:1px;background:#1e293b;min-width:100%}";
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
      '<input class="acd-inp" id="gspDocNameInput" placeholder="Object name (letter start)" maxlength="64" style="width:130px" />' +
      '<input class="acd-inp" id="gspDocDescInput" placeholder="Description / about" maxlength="240" style="flex:1;min-width:120px" />' +
      '<button type="button" class="acd-btn primary" id="gspDocCreate">Place</button>' +
      "</div>" +
      '<div class="acd-top" id="gspMediaBar" style="background:#0a0f1a;flex-wrap:wrap;gap:6px">' +
      '<span style="color:#94a3b8;font-size:12px">Attach</span>' +
      '<button type="button" class="acd-btn" id="gspPickImage">Image</button>' +
      '<button type="button" class="acd-btn" id="gspPickVoice">Voice</button>' +
      '<button type="button" class="acd-btn" id="gspPickDoc">Doc</button>' +
      '<button type="button" class="acd-btn" id="gspPickVideo">Video</button>' +
      '<button type="button" class="acd-btn primary" id="gspImportOffice">Excel/CSV</button>' +
      '<button type="button" class="acd-btn" id="gspImportUrl">URL</button>' +
      '<input type="file" id="gspFileInput" style="display:none" />' +
      '<span id="gspMediaChip" style="color:#7dd3fc;font-size:12px"></span>' +
      '</div>' +
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

    function setPendingMedia(file, mediaType) {
      if (!file) return;
      // Keep real File for multipart upload — not only bytecode/b64
      state.pendingMedia = {
        media_type: mediaType,
        filename: file.name || "file",
        mime: file.type || "",
        size: file.size || 0,
        payload_b64: "",
        payload_ref: "",
        _file: file,
        preview_url: "",
      };
      var chip = document.getElementById("gspMediaChip");
      if (chip) {
        chip.textContent = mediaType + ": " + (file.name || "") + " (" + Math.round((file.size || 0) / 1024) + " KB) — Place to store file + GSP cell";
      }
      // Optional small preview for images only
      if (mediaType === "image" && file.size < 400000) {
        var reader = new FileReader();
        reader.onload = function () {
          var dataUrl = String(reader.result || "");
          if (state.pendingMedia) {
            state.pendingMedia.preview_url = dataUrl;
            state.pendingMedia.payload_b64 = dataUrl.indexOf(",") >= 0 ? dataUrl.split(",")[1] : "";
          }
        };
        reader.readAsDataURL(file);
      }
    }
    var fin = document.getElementById("gspFileInput");
    function pick(accept, mediaType) {
      if (!fin) return;
      fin.accept = accept;
      fin.onchange = function () {
        var f = fin.files && fin.files[0];
        setPendingMedia(f, mediaType);
        fin.value = "";
      };
      fin.click();
    }
    var bi = document.getElementById("gspPickImage");
    if (bi) bi.onclick = function () { pick("image/*", "image"); };
    var bv = document.getElementById("gspPickVoice");
    if (bv) bv.onclick = function () { pick("audio/*", "voice"); };
    var bd = document.getElementById("gspPickDoc");
    if (bd) bd.onclick = function () { pick(".pdf,.doc,.docx,.txt,.md,application/pdf,text/*", "doc"); };
    var bvid = document.getElementById("gspPickVideo");
    if (bvid) bvid.onclick = function () { pick("video/*", "video"); };

    var bo = document.getElementById("gspImportOffice");
    if (bo) bo.onclick = function () {
      if (!fin) return;
      fin.accept = ".xlsx,.xlsm,.csv,.txt,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";
      fin.onchange = function () {
        var f = fin.files && fin.files[0];
        if (!f) return;
        var reader = new FileReader();
        reader.onload = async function () {
          var dataUrl = String(reader.result || "");
          var b64 = dataUrl.indexOf(",") >= 0 ? dataUrl.split(",")[1] : "";
          var name = (document.getElementById("gspDocNameInput").value || "").trim();
          if (!name) {
            name = (f.name || "Import").replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]/g, "");
            if (!/^[A-Za-z]/.test(name)) name = "S" + name;
            var ni = document.getElementById("gspDocNameInput");
            if (ni) ni.value = name.slice(0, 62);
          }
          var desc = (document.getElementById("gspDocDescInput") && document.getElementById("gspDocDescInput").value) || "";
          try {
            var res = await api("/sandbox/docs/import_office", "POST", {
              doc_name: name,
              description: desc,
              filename: f.name,
              payload_b64: b64,
              kind: state.kind === "dbase" ? "dbase" : "sheets",
              parent_type: state.parentType === "room" ? "room" : "repo",
              parent_id: state.parentId,
              parent_repo: state.parentRepo || state.parentId,
            });
            alert("Imported " + ((res.parsed && res.parsed.format) || "") + " · cells " + ((res.parsed && res.parsed.cell_count) || 0));
            state.docName = name;
            await refreshList();
            renderStage();
          } catch (e) {
            alert("Import failed: " + (e.message || e));
          }
        };
        reader.readAsDataURL(f);
        fin.value = "";
      };
      fin.click();
    };
    var bu = document.getElementById("gspImportUrl");
    if (bu) bu.onclick = async function () {
      var url = prompt("Spreadsheet URL (http/https .xlsx or .csv)");
      if (!url) return;
      var name = (document.getElementById("gspDocNameInput").value || "").trim() || "ImportedSheet";
      var ni = document.getElementById("gspDocNameInput");
      if (ni && !ni.value) ni.value = name;
      var desc = (document.getElementById("gspDocDescInput") && document.getElementById("gspDocDescInput").value) || "";
      try {
        var res = await api("/sandbox/docs/import_office", "POST", {
          doc_name: name,
          description: desc,
          url: url,
          filename: url.split("/").pop() || "download.csv",
          kind: state.kind === "dbase" ? "dbase" : "sheets",
          parent_type: state.parentType === "room" ? "room" : "repo",
          parent_id: state.parentId,
          parent_repo: state.parentRepo || state.parentId,
        });
        alert("Imported from URL · cells " + ((res.parsed && res.parsed.cell_count) || 0));
        await refreshList();
      } catch (e) {
        alert("URL import failed: " + (e.message || e));
      }
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


  function applyKindTheme(kind) {
    var th = KIND_THEME[kind] || KIND_THEME.dbase;
    var panel = document.getElementById("gspDocsPanel");
    if (!panel) return;
    panel.setAttribute("data-kind", kind);
    var top = panel.querySelector(".acd-top");
    var bar = document.getElementById("gspKindBar");
    var side = document.getElementById("gspSide");
    if (top) top.style.background = th.bar;
    if (bar) bar.style.background = th.bar;
    if (side) side.style.background = th.side;
    panel.style.setProperty("--acd-accent", th.accent);
    panel.style.setProperty("--acd-cell-grad", th.cell);
    document.querySelectorAll("#gspKindBar .acd-btn").forEach(function (b) {
      var on = b.dataset.kind === kind;
      b.classList.toggle("active", on);
      if (on) {
        b.style.background = th.accent;
        b.style.borderColor = "#e0f2fe";
        b.style.color = "#0f172a";
      } else {
        b.style.background = "rgba(15,23,42,0.45)";
        b.style.borderColor = "rgba(226,232,240,0.35)";
        b.style.color = "#f8fafc";
      }
    });
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
    applyKindTheme(kind);
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
    // Always show a working grid shell — never a dead welcome-only stage
    try {
      if (!state.data) {
        state.data = {
          cells: {},
          sheets: { Sheet1: { cells: {} } },
          active_sheet: "Sheet1",
          n_rows: state.nRows || 64,
          n_cols: state.nCols || 54,
          slides: state.kind === "presentations" ? [{ id: "s0", title: "", body: "", gradient: "g00" }] : undefined,
        };
      }
      renderSheet();
    } catch (e) {
      console.warn("paintEmpty grid", e);
      var stage = document.getElementById("gspDocStage");
      if (!stage) return;
      var k = KINDS[state.kind] || { label: "Grid", icon: "fa-table", blurb: "" };
      stage.innerHTML =
        '<div class="acd-empty"><h2 style="color:#e2e8f0">' + k.label +
        "</h2><p>" + (k.blurb || "") + "</p><p>Grid ready — enter an object name to place.</p></div>";
    }
  }

  function readNameDesc() {
    var topName = document.getElementById("gspDocNameInput");
    var topDesc = document.getElementById("gspDocDescInput");
    var objName = document.getElementById("objName");
    var objDesc = document.getElementById("objDesc");
    var name = ((objName && objName.value) || (topName && topName.value) || "").trim();
    var desc = ((objDesc && objDesc.value) || (topDesc && topDesc.value) || "").trim();
    return { name: name, desc: desc };
  }

  async function uploadPendingMedia(objectName, description) {
    var pm = state.pendingMedia;
    if (!pm || !pm._file) {
      // only b64 pending
      return pm || null;
    }
    var fd = new FormData();
    fd.append("ns", ({ dbase: "dbase", sheets: "sheets", collabsheet: "collabsheet", presentations: "pres" }[state.kind] || "dbase"));
    fd.append("object_name", objectName);
    fd.append("description", description || "");
    if (state.parentType === "room" && state.parentId) fd.append("workspace_id", state.parentId);
    if (typeof activeOrgId !== "undefined" && activeOrgId) fd.append("org_id", activeOrgId);
    fd.append("file", pm._file, pm.filename || "upload.bin");
    try {
      var up = await apiUpload("/grid/ns/upload", fd);
      pm.payload_ref = (up && (up.payload_ref || (up.result && up.result.payload_ref))) || pm.payload_ref || "";
      pm.payload_b64 = ""; // stored as real blob on server
      pm.uploaded = true;
      var chip = document.getElementById("gspMediaChip");
      if (chip) chip.textContent = (pm.media_type || "file") + " stored · " + (pm.filename || "") + (pm.payload_ref ? " · ref ok" : "");
      return pm;
    } catch (e) {
      console.warn("upload media", e);
      // fallback small b64 if present
      return pm;
    }
  }

  async function createDoc() {
    var nd = readNameDesc();
    var name = nd.name;
    var desc = nd.desc;
    if (!name) {
      alert("Enter an object name (must start with a letter).");
      return;
    }
    if (!/^[A-Za-z\u00C0-\u024F\u0400-\u04FF\u0600-\u06FF]/.test(name[0])) {
      alert("Name must start with a letter. GSP start_row/col are computed from this name.");
      return;
    }
    // keep ascii-safe for sandbox resource names when possible
    var safeName = name;
    if (!/^[A-Za-z][A-Za-z0-9_-]{0,62}$/.test(name)) {
      // allow unicode for display but API may require latin — strip for path
      safeName = name.replace(/[^\w\-]/g, "_");
      if (!/^[A-Za-z]/.test(safeName)) safeName = "Obj_" + safeName;
      safeName = safeName.slice(0, 63);
    }
    var par = resolveParent();
    state.parentType = par.parentType;
    state.parentId = par.parentId;
    state.parentRepo = par.parentRepo || par.parentId;
    if (typeof currentRoomId !== "undefined" && currentRoomId) {
      state.parentType = "room";
      state.parentId = currentRoomId;
    }
    try {
      var res = await api("/sandbox/docs", "POST", {
        scope: "user",
        parent_type: state.parentType === "room" ? "room" : "repo",
        parent_repo: state.parentRepo || state.parentId || "HomeDocs",
        parent_id: state.parentId || "HomeDocs",
        doc_name: safeName,
        kind: apiKind(state.kind),
        n_rows: state.kind === "dbase" ? (state.nRows || 64) : 64,
        n_cols: state.kind === "dbase" ? (state.nCols || 26) : 54,
        description: desc,
      });
      state.docName = safeName;
      state.docUid = res.doc_uid || res.uid || "";
      var placeMeta = res.placement || res.gsp || res || {};
      state.placement = {
        start_row: placeMeta.start_row || res.start_row || null,
        start_col: placeMeta.start_col != null ? placeMeta.start_col : (placeMeta.c != null ? placeMeta.c : res.start_col),
        target_cell: placeMeta.target_cell || res.target_cell || null,
        doc_uid: state.docUid,
        owner_uid: res.owner_uid || placeMeta.owner_uid || null,
        L: placeMeta.L || res.L,
        S: placeMeta.S || res.S,
        c: placeMeta.c != null ? placeMeta.c : placeMeta.start_col,
        C: placeMeta.C || res.C,
        lang: placeMeta.lang || res.lang,
      };
      var sr = state.placement.start_row || 1;
      var sc = state.placement.start_col != null ? state.placement.start_col : 0;
      var cellKey = sr + ":" + sc;
      var seed = {
        value: name,
        meta: desc || ("placed " + cellKey),
        row: sr,
        col: sc,
        placed: true,
        doc_uid: state.docUid,
        payload_ref: "",
        media_type: "",
        filename: "",
      };

      // Upload real media file if pending
      if (state.pendingMedia) {
        var media = await uploadPendingMedia(safeName, desc);
        if (media) {
          seed.payload_ref = media.payload_ref || "";
          seed.media_type = media.media_type || "";
          seed.filename = media.filename || "";
          seed.mime = media.mime || "";
          if (media.payload_b64 && !seed.payload_ref) seed.preview_b64 = media.payload_b64.slice(0, 64);
        }
      }

      if (state.kind === "presentations") {
        state.data = { slides: [{ id: "s0", title: name, body: desc || "", gradient: "g00" }] };
      } else if (state.kind === "dbase") {
        state.data = {
          sheets: { Sheet1: { cells: {} } },
          active_sheet: "Sheet1",
          object_name: name,
          object_desc: desc,
          cells: {},
          n_rows: state.nRows || 64,
          n_cols: state.nCols || 26,
        };
        state.data.sheets.Sheet1.cells[cellKey] = seed;
        state.data.cells[cellKey] = seed;
      } else {
        state.data = {
          cells: {},
          object_name: name,
          object_desc: desc,
          n_rows: 64,
          n_cols: 54,
        };
        state.data.cells[cellKey] = seed;
      }

      // MemoryGrid ns stamp (best-effort)
      try {
        var nsMap = { dbase: "dbase", sheets: "sheets", collabsheet: "collabsheet", presentations: "pres" };
        if (typeof window.accdPlaceNs === "function") {
          await window.accdPlaceNs(nsMap[state.kind] || "dbase", safeName, desc, desc || name, {
            media_type: (state.pendingMedia && state.pendingMedia.media_type) || "",
            filename: (state.pendingMedia && state.pendingMedia.filename) || "",
            mime: (state.pendingMedia && state.pendingMedia.mime) || "",
            payload_ref: seed.payload_ref || "",
            payload_b64: (!seed.payload_ref && state.pendingMedia && state.pendingMedia.payload_b64) || "",
          });
        }
      } catch (e2) {
        console.warn("ns place", e2);
      }

      // Persist cell + snapshot
      try {
        await writeCell(sr, sc, seed.value, seed.meta);
      } catch (e3) {
        console.warn("writeCell after place", e3);
      }
      await snapshotSave();

      // Sync top inputs
      var ti = document.getElementById("gspDocNameInput");
      if (ti) ti.value = name;
      var td = document.getElementById("gspDocDescInput");
      if (td) td.value = desc;

      state.pendingMedia = null;
      renderSheet();
      refreshList();
      alert(
        "Placed " +
          name +
          " at " +
          (state.placement.target_cell || cellKey) +
          " · row " +
          sr +
          " col " +
          sc +
          (state.placement.lang ? " · lang " + state.placement.lang : "")
      );
    } catch (e) {
      console.error("Place failed", e);
      alert("Place failed: " + (e.message || e));
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


  function bindCfgApply() {
    var btn = document.getElementById("cfgApply");
    if (!btn) return;
    btn.onclick = function (ev) {
      if (ev) { ev.preventDefault(); ev.stopPropagation(); }
      var rowsEl = document.getElementById("cfgRows");
      var colsEl = document.getElementById("cfgCols");
      var nr = rowsEl ? parseInt(rowsEl.value, 10) : state.nRows;
      var nc = colsEl ? parseInt(colsEl.value, 10) : state.nCols;
      if (!(nr >= 1 && nr <= 128)) { alert("Rows must be 1–128"); return; }
      if (!(nc >= 1 && nc <= 54)) { alert("Cols must be 1–54"); return; }
      if (state.kind === "sheets" || state.kind === "collabsheet") {
        nr = 64; nc = 54;
        alert("SheetS / CollabSheet stay on GSP 54×64");
      }
      state.nRows = nr;
      state.nCols = nc;
      try { saveGridConfig(state.kind); } catch (e) {}
      if (!state.data) state.data = { cells: {}, sheets: { Sheet1: { cells: {} } }, active_sheet: "Sheet1" };
      state.data.n_rows = nr;
      state.data.n_cols = nc;
      renderSheet();
    };
  }
  function renderSheet() {
    var stage = document.getElementById("gspDocStage");
    var rows = Math.max(1, Math.min(state.nRows || 64, state.kind === "dbase" ? 128 : 64));
    var cols = Math.max(1, Math.min(state.nCols || (state.kind === "dbase" ? 26 : 54), state.kind === "dbase" ? 54 : 54));
    var cells = activeCells();
    state.data = state.data || {};
    var objName = state.data.object_name || state.docName || "";
    var objDesc = state.data.object_desc || "";

    var place = state.placement || {};
    var html = "";
    if (state.kind === "dbase") {
      html +=
        '<div class="acd-entry" style="align-items:center">' +
        '<div><label>Grid rows</label><input class="acd-inp" id="cfgRows" type="number" min="8" max="128" value="' +
        rows +
        '" style="width:72px" /></div>' +
        '<div><label>Grid cols</label><input class="acd-inp" id="cfgCols" type="number" min="8" max="54" value="' +
        cols +
        '" style="width:72px" /></div>' +
        '<button type="button" class="acd-btn primary" id="cfgApply">Apply grid size</button>' +
        '<span style="color:#94a3b8;font-size:12px">DBase size is configurable · SheetS stays 54×64</span></div>';
    }
    html +=
      '<div class="acd-entry">' +
      '<div><label>Object name</label><input class="acd-inp" id="objName" style="width:100%" value="' +
      escapeHtml(objName) +
      '" /></div>' +
      '<div><label>Description</label><input class="acd-inp" id="objDesc" style="width:100%" value="' +
      escapeHtml(objDesc) +
      '" placeholder="What this base holds" /></div>' +
      '<button type="button" class="acd-btn primary" id="objSave">Save meta</button>' +
      (place.start_row
        ? '<span style="color:#7dd3fc;font-size:12px">GSP row ' +
          place.start_row +
          (place.start_col != null ? " · col " + place.start_col : "") +
          (place.doc_uid ? " · uid " + String(place.doc_uid).slice(0, 20) : "") +
          "</span>"
        : "") +
      "</div>";

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

    document.getElementById("objSave").onclick = async function () {
      var nd = readNameDesc();
      if (!state.data) state.data = { cells: {}, sheets: { Sheet1: { cells: {} } }, active_sheet: "Sheet1" };
      state.data.object_name = nd.name;
      state.data.object_desc = nd.desc;
      var topN = document.getElementById("gspDocNameInput");
      var topD = document.getElementById("gspDocDescInput");
      if (topN) topN.value = nd.name;
      if (topD) topD.value = nd.desc;
      if (!state.docName || !state.placement || !state.placement.start_row) {
        // No placement yet — Place computes GSP start_row/col
        await createDoc();
        return;
      }
      var sr = state.placement.start_row;
      var sc = state.placement.start_col != null ? state.placement.start_col : 0;
      try {
        await writeCell(sr, sc, nd.name || state.docName, nd.desc || "");
        await snapshotSave();
        alert("Meta saved at r" + sr + ":c" + sc);
      } catch (e) {
        alert("Save meta failed: " + (e.message || e));
      }
      renderSheet();
    };
    document.getElementById("gridLookupGo").onclick = async function () {
      state.lookup = document.getElementById("gridLookup").value || "";
      // Client grid filter
      renderSheet();
      // Also search server list by name when possible
      try {
        await refreshList();
        var q = (state.lookup || "").toLowerCase();
        if (q) {
          var list = document.getElementById("gspDocList");
          if (list) {
            list.querySelectorAll(".acd-doc-item").forEach(function (el) {
              var show = (el.textContent || "").toLowerCase().indexOf(q) >= 0;
              el.style.display = show ? "" : "none";
            });
          }
        }
      } catch (e) {}
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

    try { bindCfgApply(); } catch (e) {}
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
    document.querySelectorAll("button").forEach(function (n) {
      try {
        if (n.closest("#homeDocsStrip") || n.closest("#roomDocsStrip") || n.closest("#gspDocsPanel")) return;
        var lab = ((n.textContent || "") + " " + (n.id || "")).toLowerCase();
        if (!/sheets|dbase|collab|presentation|excel/.test(lab)) return;
        if (n.closest("header") || n.closest(".top-bar") || n.closest("#mainNav") || n.closest(".app-header") || n.parentElement && n.parentElement.id === "homeActions") {
          // keep only if inside homeDocsStrip
          if (!n.closest("#homeDocsStrip")) n.remove();
        }
      } catch (e) {}
    });
    var hub = document.getElementById("homeHub") || document.getElementById("homeActions") || document.getElementById("homeBody");
    var homeHost = document.getElementById("homeDocsStrip");
    if (!homeHost && hub) {
      homeHost = document.createElement("div");
      homeHost.id = "homeDocsStrip";
      homeHost.style.cssText = "margin-top:10px;width:100%;display:flex;flex-wrap:wrap;gap:6px;visibility:visible";
      hub.appendChild(homeHost);
    }
    if (homeHost) {
      homeHost.style.display = "flex";
      homeHost.style.visibility = "visible";
      specs.forEach(function (s) {
        var id = "home" + s.id;
        var el = document.getElementById(id);
        if (!el) homeHost.appendChild(mkBtn(s, "home"));
        else if (!el.onclick) {
          el.onclick = function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            if (window[s.fn]) window[s.fn]();
          };
        }
      });
    }
    var roomBar =
      document.getElementById("activeRoomBar") ||
      document.getElementById("roomHeader") ||
      document.getElementById("workspaceHeader") ||
      document.querySelector(".room-top, .workspace-top, #chatHeader");
    var roomHost = document.getElementById("roomDocsStrip");
    if (!roomHost && roomBar) {
      roomHost = document.createElement("div");
      roomHost.id = "roomDocsStrip";
      roomHost.className = "acd-room-docs";
      roomHost.style.cssText = "flex-wrap:wrap;gap:6px;padding:6px 8px;width:100%";
      roomBar.appendChild(roomHost);
    }
    if (roomHost) {
      specs.forEach(function (s) {
        var id = "ws" + s.id;
        var el = document.getElementById(id);
        if (!el) roomHost.appendChild(mkBtn(s, "ws"));
        else if (!el.onclick) {
          el.onclick = function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            if (window[s.fn]) window[s.fn]();
          };
        }
      });
    }
  }

  // Public re-inject for room/home transitions (strips must not stay deleted)
  window.acdInjectDocsButtons = injectButtons;

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

    /* Phase 0: do not redefine acdOpenCodespace — app.js owns open */
    document.addEventListener(
      "click",
      function (ev) {
        var t = ev.target && ev.target.closest && ev.target.closest("#codeBack, #btnCodeBack, #btnCloseCode, [data-code-back]");
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
    setTimeout(injectButtons, 600);
    setTimeout(injectButtons, 1800);
    document.addEventListener("acd-room-open", function () { try { injectButtons(); } catch (e) {} });
    document.addEventListener("acd-home", function () { try { injectButtons(); } catch (e) {} });
    hardenCodespace();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 600);
  setTimeout(boot, 1600);
  console.log("[acd] docs: home + workspace strips; place name+desc → uid/grid");
})();


// ACCD-MARATHON: place DBase/sheet object onto owner MemoryGrid namespace
window.accdPlaceNs = async function (ns, objectName, description, text, media) {
  try {
    var api = (typeof window.api === "function") ? window.api : null;
    if (!api) return { ok: false, error: "no api" };
    media = media || {};
    return await api("/grid/ns/place", "POST", {
      ns: ns || "dbase",
      object_name: objectName,
      description: description || "",
      text: text || description || objectName,
      media_type: media.media_type || "",
      filename: media.filename || "",
      mime: media.mime || "",
      payload_ref: media.payload_ref || "",
      payload_b64: media.payload_b64 || "",
      org_id: (typeof activeOrgId !== "undefined" ? activeOrgId : null),
      workspace_id: (typeof currentRoomId !== "undefined" ? currentRoomId : null),
    });
  } catch (e) {
    return { ok: false, error: String(e && e.message ? e.message : e) };
  }
};

window.accdListNs = async function (ns) {
  try {
    var q = "/grid/ns/list?ns=" + encodeURIComponent(ns || "dbase");
    if (typeof activeOrgId !== "undefined" && activeOrgId) q += "&org_id=" + encodeURIComponent(activeOrgId);
    var api = (typeof window.api === "function") ? window.api : null;
    if (!api) return { ok: false, items: [] };
    return await api(q, "GET");
  } catch (e) {
    return { ok: false, items: [], error: String(e && e.message ? e.message : e) };
  }
};
