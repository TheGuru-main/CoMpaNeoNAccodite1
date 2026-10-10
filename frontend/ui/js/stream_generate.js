/**
 * Accodite SSE client — POST /generate/stream
 * Grid-rooted context is applied server-side before tokens stream.
 */
async function streamGenerate(prompt, onToken, onDone, onError, options) {
  options = options || {};
  const body = {
    prompt: prompt,
    max_len: options.max_len != null ? options.max_len : 256,
    temperature: options.temperature != null ? options.temperature : 0.8,
    conversation_history: options.conversation_history || "",
    workspace_name: options.workspace_name || "",
    temperament: options.temperament || "sanguine",
  };

  let res;
  try {
    res = await fetch("/generate/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (onError) onError(String(err && err.message ? err.message : err));
    return;
  }

  if (!res.ok) {
    let errText = "";
    try {
      errText = await res.text();
    } catch (_) {}
    if (onError) onError(errText || ("HTTP " + res.status));
    return;
  }

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let finished = false;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";

    for (const chunk of parts) {
      const line = chunk.split("\n").find(function (l) {
        return l.indexOf("data: ") === 0;
      });
      if (!line) continue;

      let ev;
      try {
        ev = JSON.parse(line.slice(6));
      } catch (_) {
        continue;
      }

      if (ev.event === "error") {
        if (onError) onError(ev.error || "stream error");
        finished = true;
        return;
      }
      if (ev.text != null && onToken) {
        onToken(ev.text, ev.stream_text || "");
      }
      if (ev.event === "done" || ev.done) {
        if (onDone) onDone(ev.stream_text || "");
        finished = true;
        return;
      }
    }
  }

  if (!finished && onDone) onDone();
}

// Optional: bind to a simple chat form if elements exist
function bindStreamChat(opts) {
  opts = opts || {};
  const input = document.querySelector(opts.inputSelector || "#prompt, #chat-input, textarea[name=prompt]");
  const out = document.querySelector(opts.outputSelector || "#response, #chat-output, #assistant");
  const btn = document.querySelector(opts.buttonSelector || "#send, button[type=submit]");
  if (!input || !out) return;

  async function run() {
    const prompt = (input.value || "").trim();
    if (!prompt) return;
    out.textContent = "";
    await streamGenerate(
      prompt,
      function (token, full) {
        out.textContent = full || (out.textContent + token);
      },
      function (full) {
        if (full) out.textContent = full;
      },
      function (err) {
        out.textContent = "[stream error] " + err;
      },
      opts
    );
  }

  if (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      run();
    });
  }
}

if (typeof window !== "undefined") {
  window.streamGenerate = streamGenerate;
  window.bindStreamChat = bindStreamChat;
}
