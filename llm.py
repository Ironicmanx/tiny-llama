#Upgrade module once new cpu arrives - Mistral 7B Instruct GGUF model with llama.cpp
import subprocess
import time
import select
import os
import startup

# You need two variables here: the path to your LLM executable and the path to your model file
# You can get models from https://huggingface.co/models?search=gguf
# And you can compile llama.cpp from https://github.com/ggerganov/llama.cpp

LLM_PATH = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-cli" # Path to your LLM executable
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf" # Path to your model file

# Configuration constants (sane defaults)
STALL_TIMEOUT = 30
MAX_TOTAL_TIME = 360
MAX_CONTINUATIONS = 3
MIN_RESPONSE_LENGTH = 1


def _read_output_nonblocking(process, timeout):
    """Read output from process without blocking, using select/os.read."""
    output_lines = []
    start_time = time.time()
    last_output_time = start_time
    buffer = ""
    fd = process.stdout.fileno()

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            break

        if time.time() - last_output_time > STALL_TIMEOUT:
            break

        if process.poll() is not None:
            try:
                while True:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8', errors='replace')
            except (OSError, BlockingIOError):
                pass
            break

        try:
            ready, _, _ = select.select([process.stdout], [], [], 0.5)
            if ready:
                chunk = os.read(fd, 4096)
                if chunk:
                    buffer += chunk.decode('utf-8', errors='replace')
                    last_output_time = time.time()
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            output_lines.append(line)
        except (OSError, ValueError, BlockingIOError):
            break

    if buffer.strip():
        output_lines.append(buffer.strip())
    return output_lines


def _is_response_complete(text):
    if not text:
        return False
    text = text.strip()
    if text.endswith(('.', '!', '?', '"', "'", ')', ']')):
        return True
    ending_patterns = ['...', '—', '–', ':']
    return any(text.endswith(p) for p in ending_patterns)


def _clean_response(text):
    if not text:
        return ""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('[INST]') or line.startswith('[/INST]'):
            continue
        cleaned.append(line)
    return ' '.join(cleaned)

def ask_local_llm(prompt):
    formatted_prompt = f"[INST] {prompt} [/INST]"
    print("\n[Echo Thinking] Sending prompt to LLM...")
    print(f"[Prompt] {formatted_prompt}")

    start = time.time()
    full_response = ""
    continuation_count = 0

    try:
        while continuation_count <= MAX_CONTINUATIONS:
            if time.time() - start > MAX_TOTAL_TIME:
                break

            if continuation_count == 0:
                current_prompt = formatted_prompt
            else:
                current_prompt = f"[INST] Continue this response: {full_response[-200:]} [/INST]"

            proc = subprocess.Popen([
                LLM_PATH, "-m", MODEL_PATH, "-p", current_prompt, "--verbose",
                "--threads", "4", "--ctx_size", "2048", "--n_predict", "512",
                "--temp", "0.7", "--top_k", "40", "--top_p", "0.9", "--repeat_penalty", "1.1",
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            elapsed = time.time() - start
            remaining = min(MAX_TOTAL_TIME - elapsed, 60)
            output_lines = _read_output_nonblocking(proc, remaining)

            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

            stderr_output = ""
            if proc.stderr:
                try:
                    stderr_output = proc.stderr.read().decode('utf-8', errors='replace')
                except Exception as e:
                    print(f"[LLM STDERR READ ERROR] {e}")

            if stderr_output:
                print(f"[LLM STDERR] {stderr_output.strip()}")

            current_output = _clean_response('\n'.join(output_lines))
            if continuation_count == 0:
                full_response = current_output
            elif current_output:
                full_response = full_response.rstrip() + " " + current_output

            if not current_output:
                break
            if len(current_output) < MIN_RESPONSE_LENGTH:
                break
            if _is_response_complete(full_response):
                break

            continuation_count += 1

        return full_response if full_response else "[No response generated]"
    except Exception as e:
        return f"[LLM Error] {e}"


def main():
    # Prefer startup.do_you_want_to_start() if available, otherwise use local fallback
    try:
        starter = startup.do_you_want_to_start
    except Exception:
        starter = do_you_want_to_start

    if not starter():
        print("Echo: Exiting before start.")
        return
    import sys
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        print("Echo: (thinking...)")
        resp = ask_local_llm(user_input)
        print("Echo:", resp)
        print()
    else:
        print("Echo: Initialized. Provide a prompt as a command-line argument to get a response.")


if __name__ == '__main__':
    main()