import subprocess
import time

LLM_PATH = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-cli"
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf"

def ask_local_llm(prompt):
    formatted_prompt = f"[INST] {prompt} [/INST]"
    print("\n[Jarvis Thinking] Sending prompt to LLM...")
    print(f"[Prompt] {formatted_prompt}")

    start = time.time()

    try:
        process = subprocess.Popen(
            [
                LLM_PATH,
                "-m", MODEL_PATH,
                "-p", formatted_prompt,
                "--threads", "4",
                "--ctx_size", "256",
                "--n_predict", "96",
                "--temp", "0.7",
                "--top_k", "40",
                "--top_p", "0.9",
                "--repeat_penalty", "1.1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line:
                break
            print(f"[LLM] {line.strip()}")
            output_lines.append(line)

        stderr = process.stderr.read()
        if stderr:
            print(f"[LLM STDERR] {stderr.strip()}")

        duration = round(time.time() - start, 2)
        print(f"[LLM Completed] Took {duration} seconds.")

        return "".join(output_lines).strip()

    except Exception as e:
        return f"[LLM Error] {e}"
