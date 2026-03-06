"""
Echo LLM Web UI — Flask app proxying to llama-server (llama.cpp).

llama-server keeps the model loaded in RAM with proper EOS detection
and native SSE streaming via an OpenAI-compatible API.

Start the server first:
    ~/jarvis_local/llama.cpp/build/bin/llama-server \
        -m ~/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf \
        --host 127.0.0.1 --port 8080 --threads 4 --ctx-size 2048

Then run this:
    python3 app.py
"""

import os
import json
import time
import subprocess
import signal
import sys
import requests
from flask import Flask, request, Response, jsonify, render_template

app = Flask(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
LLAMA_SERVER = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-server"
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf"
LLAMA_API = "http://127.0.0.1:8080"

# ── Default model parameters ────────────────────────────────────────────────
DEFAULTS = {
    "temperature": 0.7,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "n_predict": 512,
    "ctx_size": 2048,
    "threads": 4,
}

# ── In-memory conversation history ──────────────────────────────────────────
conversations = []

# ── llama-server process handle ──────────────────────────────────────────────
server_proc = None


def _validate_params(data):
    """Clamp user parameters to safe ranges and merge with defaults."""
    params = dict(DEFAULTS)
    if "temperature" in data:
        params["temperature"] = max(0.0, min(2.0, float(data["temperature"])))
    if "top_k" in data:
        params["top_k"] = max(1, min(200, int(data["top_k"])))
    if "top_p" in data:
        params["top_p"] = max(0.0, min(1.0, float(data["top_p"])))
    if "repeat_penalty" in data:
        params["repeat_penalty"] = max(1.0, min(2.0, float(data["repeat_penalty"])))
    if "n_predict" in data:
        params["n_predict"] = max(16, min(2048, int(data["n_predict"])))
    return params


def start_llama_server():
    """Start llama-server as a subprocess if not already running."""
    global server_proc

    # Check if already running
    try:
        r = requests.get(f"{LLAMA_API}/health", timeout=2)
        if r.status_code == 200:
            print("   llama-server already running")
            return True
    except requests.ConnectionError:
        pass

    if not os.path.isfile(LLAMA_SERVER):
        print(f"   ERROR: llama-server not found at {LLAMA_SERVER}")
        return False
    if not os.path.isfile(MODEL_PATH):
        print(f"   ERROR: Model not found at {MODEL_PATH}")
        return False

    print("   Starting llama-server (loading model into RAM)...")
    print("   This takes 30-60s on first load, then stays fast.")

    server_proc = subprocess.Popen(
        [
            LLAMA_SERVER,
            "-m", MODEL_PATH,
            "--host", "127.0.0.1",
            "--port", "8080",
            "--threads", str(DEFAULTS["threads"]),
            "--ctx-size", str(DEFAULTS["ctx_size"]),
            "--chat-template", "mistral-instruct",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
    )

    # Wait for server to be ready (model loading)
    for i in range(120):  # Up to 2 minutes
        try:
            r = requests.get(f"{LLAMA_API}/health", timeout=1)
            if r.status_code == 200:
                data = r.json() if r.text else {}
                status = data.get("status", "ok")
                if status == "ok":
                    print(f"   llama-server ready ({i+1}s)")
                    return True
                elif status == "loading model":
                    if i % 10 == 0:
                        print(f"   Still loading model... ({i}s)")
        except (requests.ConnectionError, requests.Timeout):
            pass

        # Check if process died
        if server_proc.poll() is not None:
            stderr = server_proc.stderr.read().decode("utf-8", errors="replace")
            print(f"   ERROR: llama-server exited: {stderr[:500]}")
            return False

        time.sleep(1)

    print("   ERROR: llama-server failed to start within 120s")
    return False


def stop_llama_server():
    """Gracefully stop llama-server."""
    global server_proc
    if server_proc and server_proc.poll() is None:
        try:
            os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
            server_proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(server_proc.pid), signal.SIGKILL)
                server_proc.wait()
            except Exception:
                pass
    server_proc = None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/defaults")
def get_defaults():
    return jsonify(DEFAULTS)


@app.route("/health")
def health():
    """Check llama-server health."""
    try:
        r = requests.get(f"{LLAMA_API}/health", timeout=2)
        return jsonify(r.json() if r.text else {"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 503


@app.route("/history")
def get_history():
    return jsonify(conversations)


@app.route("/history", methods=["DELETE"])
def clear_history():
    conversations.clear()
    return jsonify({"status": "cleared"})


@app.route("/stream", methods=["POST"])
def stream():
    """SSE endpoint — proxies streaming from llama-server's OpenAI-compatible API."""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    params = _validate_params(data)

    # Build OpenAI-compatible chat completion request
    payload = {
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "temperature": params["temperature"],
        "top_k": params["top_k"],
        "top_p": params["top_p"],
        "repeat_penalty": params["repeat_penalty"],
        "n_predict": params["n_predict"],
    }

    def generate():
        full_response = []
        start = time.time()
        try:
            with requests.post(
                f"{LLAMA_API}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=300,
            ) as r:
                if r.status_code != 200:
                    error_text = r.text[:200]
                    yield f"data: {json.dumps({'token': '', 'done': True, 'error': f'Server error {r.status_code}: {error_text}'})}\n\n"
                    return

                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        elapsed = time.time() - start
                        text = "".join(full_response)
                        yield f"data: {json.dumps({'token': '', 'done': True, 'elapsed': round(elapsed, 1)})}\n\n"
                        # Save to history
                        if text.strip():
                            conversations.append({
                                "prompt": prompt,
                                "response": text.strip(),
                                "params": params,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "elapsed": round(elapsed, 1),
                            })
                        return

                    try:
                        obj = json.loads(chunk)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            full_response.append(token)
                            yield f"data: {json.dumps({'token': token})}\n\n"
                    except json.JSONDecodeError:
                        continue

        except requests.ConnectionError:
            yield f"data: {json.dumps({'token': '', 'done': True, 'error': 'llama-server not running. Restart the app.'})}\n\n"
        except requests.Timeout:
            yield f"data: {json.dumps({'token': '', 'done': True, 'error': 'Request timed out (5 min)'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': '', 'done': True, 'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print()
    print("🦞 Echo LLM Web UI")
    print(f"   Model:   {os.path.basename(MODEL_PATH)}")
    print(f"   Server:  {LLAMA_API}")

    if not start_llama_server():
        print("\n   Failed to start llama-server. Exiting.")
        sys.exit(1)

    print(f"   UI:      http://localhost:5000")
    print()

    def cleanup(sig, frame):
        print("\n   Shutting down...")
        stop_llama_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)