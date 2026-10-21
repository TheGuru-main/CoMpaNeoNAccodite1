(function () {
  "use strict";
  var NET = /^(git|pip|pip3|npm|npx|yarn|curl|wget)\b/i;
  window.acdNetworkTermCommand = async function (cmd, parts, ctx) {
    var line = (ctx && ctx.line) || (parts || []).join(" ");
    var head = (cmd || "").toLowerCase();
    if (!NET.test(line) && head !== "clone") return false;
    if (head === "clone") line = "git clone " + (parts || []).slice(1).join(" ");
    var writeLog = (ctx && ctx.writeLog) || function () {};
    var errText = (ctx && ctx.errText) || String;
    var api = ctx && ctx.api;
    if (!api) { writeLog("no api\n"); return true; }
    writeLog("$ " + line + "  [net]\n");
    try {
      var data = await api("/sandbox/exec", "POST", {
        command: line,
        scope: (ctx && ctx.scope) || "user",
        repo: (ctx && ctx.repo) || null,
        network: true,
        timeout_s: 180
      });
      if (data.stdout) writeLog(data.stdout.replace(/\n?$/, "\n"));
      if (data.stderr) writeLog(data.stderr.replace(/\n?$/, "\n"));
      if (data.error) writeLog("ERROR: " + data.error + "\n");
      writeLog("[exit " + data.exit_code + "]\n");
      if (ctx && typeof ctx.refreshTree === "function") {
        try { await ctx.refreshTree(); } catch (e) {}
      }
    } catch (e) {
      writeLog("exec: " + errText(e) + "\n");
    }
    return true;
  };
})();
