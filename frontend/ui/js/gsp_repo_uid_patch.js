/**
 * ACCD GSP repo_uid client — start_row only, no K/D
 */
(function () {
  "use strict";
  var map = {};
  try { map = JSON.parse(sessionStorage.getItem("acd_repo_uids") || "{}"); } catch (e) {}

  function saveRepoUid(name, uid) {
    if (!name || !uid) return;
    map[name] = uid;
    try { sessionStorage.setItem("acd_repo_uids", JSON.stringify(map)); } catch (e) {}
  }
  function getRepoUid(name) { return map[name] || ""; }

  window.acdSaveRepoUid = saveRepoUid;
  window.acdGetRepoUid = getRepoUid;

  window.acdOnRepoCreated = function (data) {
    if (!data || !data.name) return;
    if (data.repo_uid) {
      saveRepoUid(data.name, data.repo_uid);
      if (typeof writeLog === "function") {
        writeLog("SECRET repo_uid (save it): " + data.repo_uid + "\n");
        writeLog("GSP start_row=" + data.start_row + " root=" + data.root_key + "\n");
        writeLog("push/commit need: repo name + this uid\n");
      }
    }
  };

  window.acdGspTermCommand = async function (cmd, parts, ctx) {
    var repo = ctx.repo, scope = ctx.scope || "user";
    var api = ctx.api, writeLog = ctx.writeLog || function () {};
    var errText = ctx.errText || function (e) { return (e && e.message) || String(e); };
    var arg = ctx.arg || "";

    if (cmd === "key" || cmd === "uid") {
      if (!repo) { writeLog("no repo\n"); return true; }
      if (arg) { saveRepoUid(repo, arg.trim()); writeLog("repo_uid set for " + repo + "\n"); return true; }
      writeLog(getRepoUid(repo) ? "repo_uid in session\n" : "no uid — key <repo_uid>\n");
      return true;
    }
    if (cmd === "push" || cmd === "commit") {
      if (!repo) { writeLog("no repo\n"); return true; }
      var key = getRepoUid(repo);
      var msg = parts.slice(1).join(" ").trim() || (cmd + " from codespace");
      if (parts[1] && /^[a-f0-9]{16,}$/i.test(parts[1])) {
        key = parts[1]; saveRepoUid(repo, key);
        msg = parts.slice(2).join(" ").trim() || msg;
      }
      if (!key) {
        key = prompt("repo_uid for " + repo + ":", "") || "";
        if (!key) { writeLog(cmd + " needs repo_uid\n"); return true; }
        saveRepoUid(repo, key);
      }
      try {
        var data = await api("/sandbox/repos/" + encodeURIComponent(repo) + "/" + cmd, "POST", {
          scope: scope, repo: repo, repo_uid: key, message: msg
        });
        writeLog(cmd + " ok · start_row=" + (data.start_row || "?") + " · " + (data.note || "") + "\n");
      } catch (e) {
        writeLog(cmd + ": " + errText(e) + "\n");
      }
      return true;
    }
    return false;
  };
})();
