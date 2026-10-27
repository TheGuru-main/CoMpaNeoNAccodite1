/** Accodite SSE client: robust framing, completion, status, and abort support. */
async function streamGenerate(prompt, onToken, onDone, onError, options) {
  options = options || {};
  const body = {
    prompt: prompt,
    max_len: options.max_len != null ? options.max_len : 256,
    temperature: options.temperature != null ? options.temperature : 0.8,
    conversation_history: options.conversation_history || "",
    workspace_name: options.workspace_name || "",
    temperament: options.temperament || "sanguine"
  };
  let res;
  try {
    res = await fetch("/generate/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
      body: JSON.stringify(body), signal: options.signal, cache: "no-store"
    });
  } catch (err) {
    if (onError) onError(String(err && err.message ? err.message : err));
    return;
  }
  if (!res.ok) {
    let msg = ""; try { msg = await res.text(); } catch (_) {}
    if (onError) onError(msg || ("HTTP " + res.status));
    return;
  }
  if (!res.body || !res.body.getReader) {
    if (onError) onError("Streaming response body is unavailable in this browser.");
    return;
  }
  const reader = res.body.getReader(), decoder = new TextDecoder();
  let buffer = "", finished = false, latestText = "";
  function dispatch(frame) {
    if (!frame || finished) return;
    const data = frame.split(/\r?\n/).filter(l => l.indexOf("data:") === 0)
      .map(l => l.slice(5).replace(/^ /, ""));
    if (!data.length) return;
    let ev;
    try { ev = JSON.parse(data.join("\n")); }
    catch (_) { if (options.onProtocolError) options.onProtocolError("Invalid JSON SSE frame"); return; }
    if (ev.event === "error") {
      finished = true; if (onError) onError(ev.error || "stream error");
      try { reader.cancel(); } catch (_) {} return;
    }
    if ((ev.event === "status" || ev.event === "activity" || ev.stage) && options.onStatus) options.onStatus(ev);
    if (ev.stream_text != null) latestText = String(ev.stream_text);
    if (ev.event === "complete" || ev.event === "done" || ev.done === true) {
      finished = true;
      if (onDone) onDone(ev.stream_text != null ? String(ev.stream_text) : (ev.text != null ? String(ev.text) : latestText));
      try { reader.cancel(); } catch (_) {} return;
    }
    if (ev.event === "cancelled") {
      finished = true;
      if (options.onCancelled) options.onCancelled(ev); else if (onDone) onDone(latestText);
      try { reader.cancel(); } catch (_) {} return;
    }
    if (ev.text != null && onToken) onToken(String(ev.text), latestText, ev);
  }
  try {
    while (!finished) {
      const item = await reader.read();
      if (item.done) break;
      buffer += decoder.decode(item.value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/); buffer = frames.pop() || "";
      for (const frame of frames) { dispatch(frame); if (finished) break; }
    }
    buffer += decoder.decode();
    if (!finished && buffer.trim()) dispatch(buffer);
    if (!finished && onDone) onDone(latestText);
  } catch (err) {
    if (!finished && onError) onError(String(err && err.message ? err.message : err));
  } finally { try { reader.releaseLock(); } catch (_) {} }
}
function bindStreamChat(opts) {
  opts = opts || {};
  const input = document.querySelector(opts.inputSelector || "#prompt, #chat-input, textarea[name=prompt]");
  const out = document.querySelector(opts.outputSelector || "#response, #chat-output, #assistant");
  const btn = document.querySelector(opts.buttonSelector || "#send, button[type=submit]");
  if (!input || !out) return;
  let controller = null;
  async function run() {
    const prompt = (input.value || "").trim(); if (!prompt) return;
    if (controller) controller.abort();
    controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    out.textContent = ""; if (btn) btn.disabled = true;
    try {
      await streamGenerate(prompt, (token, full) => { out.textContent = full || (out.textContent + token); },
        full => { if (full != null) out.textContent = full; },
        err => { out.textContent = "[stream error] " + err; },
        Object.assign({}, opts, controller ? { signal: controller.signal } : {}));
    } finally { if (btn) btn.disabled = false; controller = null; }
  }
  if (btn) btn.addEventListener("click", e => { e.preventDefault(); run(); });
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey && input.tagName !== "TEXTAREA") { e.preventDefault(); run(); }
  });
}
if (typeof window !== "undefined") { window.streamGenerate = streamGenerate; window.bindStreamChat = bindStreamChat; }
