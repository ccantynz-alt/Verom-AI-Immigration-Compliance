// Voxlen voice dictation widget for Verom.
//
// Usage:
//   <div data-voxlen="case-notes" data-template="case_note"></div>
//   <script src="/static/js/voxlen.js" defer></script>
//
// The widget uses the browser's Web Speech API (SpeechRecognition) for free,
// on-device streaming STT. Final transcripts are POSTed to /api/voxlen so
// voice commands, style polish, and session history flow through the backend.
// Deepgram can be swapped in later by changing data-stt="deepgram" — the
// backend handles provider selection.

(function () {
  "use strict";

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const API = (path, opts = {}) => {
    const token = localStorage.getItem("verom_token") || "";
    return fetch(path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(opts.headers || {}),
      },
    });
  };

  class VoxlenWidget {
    constructor(root) {
      this.root = root;
      this.template = root.dataset.template || null;
      this.style = root.dataset.style || "legal_formal";
      this.language = root.dataset.language || "en-US";
      this.sttProvider = root.dataset.stt || "web_speech";
      this.session = null;
      this.recognizer = null;
      this.recording = false;
      this.t0 = 0;
      this._render();
    }

    _render() {
      this.root.classList.add("voxlen-widget");
      this.root.innerHTML = `
        <div class="voxlen-header">
          <span class="voxlen-title">Voxlen Dictation</span>
          <span class="voxlen-status" data-role="status">idle</span>
        </div>
        <div class="voxlen-controls">
          <button type="button" data-role="start">Start dictation</button>
          <button type="button" data-role="stop" disabled>Stop</button>
          <button type="button" data-role="polish" disabled>Polish grammar</button>
          <select data-role="style" aria-label="Writing style">
            <option value="legal_formal">Legal (formal)</option>
            <option value="client_friendly">Client-friendly</option>
            <option value="professional">Professional</option>
            <option value="academic">Academic</option>
            <option value="technical">Technical</option>
            <option value="casual">Casual</option>
            <option value="creative">Creative</option>
          </select>
          <select data-role="export" aria-label="Export format">
            <option value="">Export…</option>
            <option value="txt">TXT</option>
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
            <option value="srt">SRT</option>
          </select>
        </div>
        <textarea data-role="transcript" rows="10" aria-label="Live transcript"></textarea>
        <div class="voxlen-commands" data-role="commands"></div>
        <p class="voxlen-hint">
          Voice commands: <em>new paragraph, period, comma, delete that,
          capitalize that, insert exhibit, cite regulation, cite statute</em>.
        </p>
      `;
      this.$ = {
        status: this.root.querySelector("[data-role=status]"),
        start: this.root.querySelector("[data-role=start]"),
        stop: this.root.querySelector("[data-role=stop]"),
        polish: this.root.querySelector("[data-role=polish]"),
        style: this.root.querySelector("[data-role=style]"),
        export: this.root.querySelector("[data-role=export]"),
        transcript: this.root.querySelector("[data-role=transcript]"),
        commands: this.root.querySelector("[data-role=commands]"),
      };
      this.$.style.value = this.style;
      this.$.start.addEventListener("click", () => this.start());
      this.$.stop.addEventListener("click", () => this.stop());
      this.$.polish.addEventListener("click", () => this.polish());
      this.$.style.addEventListener("change", (e) => {
        this.style = e.target.value;
      });
      this.$.export.addEventListener("change", (e) => {
        const fmt = e.target.value;
        if (fmt) this.export(fmt);
        e.target.value = "";
      });
      if (!SR) {
        this.$.status.textContent = "unsupported browser";
        this.$.start.disabled = true;
      }
    }

    async _ensureSession() {
      if (this.session) return this.session;
      const res = await API("/api/voxlen/sessions", {
        method: "POST",
        body: JSON.stringify({
          language: this.language,
          style: this.style,
          template_key: this.template,
          stt_provider: this.sttProvider,
          llm_provider: "none",
          title: this.root.dataset.title || "",
        }),
      });
      if (!res.ok) throw new Error(`session start failed (${res.status})`);
      this.session = await res.json();
      this.t0 = performance.now();
      return this.session;
    }

    async start() {
      if (!SR) return;
      try {
        await this._ensureSession();
      } catch (err) {
        this.$.status.textContent = `error: ${err.message}`;
        return;
      }
      this.recognizer = new SR();
      this.recognizer.continuous = true;
      this.recognizer.interimResults = true;
      this.recognizer.lang = this.language;
      this.recognizer.onresult = (event) => this._onResult(event);
      this.recognizer.onerror = (e) => {
        this.$.status.textContent = `error: ${e.error || "unknown"}`;
      };
      this.recognizer.onend = () => {
        if (this.recording) {
          // Restart for long dictations — most browsers stop after ~60s
          try { this.recognizer.start(); } catch (_) { /* already running */ }
        }
      };
      try {
        this.recognizer.start();
        this.recording = true;
        this.$.status.textContent = "listening…";
        this.$.start.disabled = true;
        this.$.stop.disabled = false;
        this.$.polish.disabled = false;
      } catch (err) {
        this.$.status.textContent = `error: ${err.message}`;
      }
    }

    stop() {
      this.recording = false;
      if (this.recognizer) {
        try { this.recognizer.stop(); } catch (_) { /* noop */ }
      }
      this.$.status.textContent = "stopped";
      this.$.start.disabled = false;
      this.$.stop.disabled = true;
    }

    _onResult(event) {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript;
        const confidence = result[0].confidence || 0.9;
        if (result.isFinal) {
          const now = performance.now();
          this._appendChunk(text, true, confidence, Math.round(this.t0 - this.t0), Math.round(now - this.t0));
          this.t0 = now;
        }
      }
    }

    async _appendChunk(text, isFinal, confidence, startMs, endMs) {
      if (!this.session) return;
      const res = await API(`/api/voxlen/sessions/${this.session.id}/append`, {
        method: "POST",
        body: JSON.stringify({
          text,
          is_final: isFinal,
          confidence,
          started_at_ms: startMs,
          ended_at_ms: endMs,
        }),
      });
      if (!res.ok) return;
      const data = await res.json();
      this.$.transcript.value = data.transcript;
      if (data.commands_applied && data.commands_applied.length) {
        this.$.commands.textContent =
          "commands: " + data.commands_applied.join(", ");
      }
    }

    async polish() {
      if (!this.session) return;
      this.$.status.textContent = "polishing…";
      const res = await API(`/api/voxlen/sessions/${this.session.id}/polish`, {
        method: "POST",
        body: JSON.stringify({ style: this.style }),
      });
      if (!res.ok) {
        this.$.status.textContent = "polish failed";
        return;
      }
      const data = await res.json();
      this.$.transcript.value = data.transcript;
      this.$.status.textContent = data.deterministic_fallback
        ? "polished (offline)"
        : `polished via ${data.provider}`;
    }

    async export(fmt) {
      if (!this.session) return;
      const res = await API(
        `/api/voxlen/sessions/${this.session.id}/export?fmt=${fmt}`
      );
      if (!res.ok) return;
      const data = await res.json();
      const blob = new Blob([data.content], { type: data.mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }
  }

  function mount() {
    document.querySelectorAll("[data-voxlen]").forEach((el) => {
      if (!el.__voxlen) el.__voxlen = new VoxlenWidget(el);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  window.Voxlen = { mount, Widget: VoxlenWidget };
})();
