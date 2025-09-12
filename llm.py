#Upgrade module once new cpu arrives - Mistral 7B Instruct GGUF model with llama.cpp

import subprocess
import time
import os
import json
from startup import do_you_want_to_start

LLM_PATH = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-cli"
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf"
MEMORY_FILE = "local_memory.json"

# Load or initialize memory
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
else:
    memory = []

MAX_MEMORY_ENTRIES = 8  # rolling memory length

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory[-MAX_MEMORY_ENTRIES:], f, indent=2)

def ask_local_llm(prompt, file_context=""):
    # Include rolling memory + current file context
    memory_context = "\n".join([f"- {m}" for m in memory[-MAX_MEMORY_ENTRIES:]])
    if memory_context:
        full_prompt = f"[INST] You are a local AI assistant.\nMemory:\n{memory_context}\n\nFile context:\n{file_context}\n\nInstruction:\n{prompt} [/INST]"
    else:
        full_prompt = f"[INST] You are a local AI assistant.\nFile context:\n{file_context}\n\nInstruction:\n{prompt} [/INST]"

    print("\n[Echo Thinking] Sending prompt to LLM...")
    print(f"[Prompt] {full_prompt}")

    start = time.time()
    full_response = ""

    try:
        process = subprocess.Popen(
            [
                LLM_PATH,
                "-m", MODEL_PATH,
                "-p", full_prompt,
                "--threads", "12",
                "--ctx_size", "4096",
                "--n_predict", "512",
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
        last_output_time = time.time()
        total_timeout = 30  # Maximum 30 seconds total
        no_output_timeout = 8  # 8 seconds without output = done

        while True:
            # Check total time limit
            if time.time() - start > total_timeout:
                print("[Echo] Total timeout reached, terminating...")
                process.terminate()
                break
                
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                if time.time() - last_output_time > no_output_timeout:
                    print("[Echo] No output timeout, terminating...")
                    process.terminate()
                    break
                time.sleep(0.1)
                continue

            # We got output, update timestamp
            last_output_time = time.time()
            
            # Stop if we see continuation prompts
            if line.strip().startswith(">") and len(line.strip()) <= 2:
                print("[Echo] Detected continuation prompt, stopping...")
                process.terminate()
                break

            print(f"[LLM] {line.strip()}")
            output_lines.append(line)

        # Aggressive cleanup
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        stderr = process.stderr.read()
        if stderr:
            print(f"[LLM STDERR] {stderr.strip()}")

        full_response = "".join(output_lines).strip()

        # Save this output to memory
        if full_response:
            memory.append(full_response)
            save_memory()

        duration = round(time.time() - start, 2)
        print(f"[LLM Completed] Took {duration} seconds.")

        return full_response

    except Exception as e:
        return f"[LLM Error] {e}"

def main():
    """Main interactive loop for the Echo assistant"""
    if not do_you_want_to_start():
        print("Echo: Exiting before start.")
        exit()
    
    print("Echo: Ready for text commands. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() == "exit":
                print("Echo: Goodbye!")
                break
            if not user_input:
                continue

            print("Echo: (thinking...)")
            response = ask_local_llm(user_input)
            print("Echo:", response)
            print()  # Add a blank line for better readability
            
        except KeyboardInterrupt:
            print("\nEcho: Exiting.")
            break
        except Exception as e:
            print(f"Echo: [Error] {e}")

# Example usage:
if __name__ == "__main__":
    main()
