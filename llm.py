import subprocess
import time

# You need two variables here: the path to your LLM executable and the path to your model file
# You can get models from https://huggingface.co/models?search=gguf
# And you can compile llama.cpp from https://github.com/ggerganov/llama.cpp

LLM_PATH = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-cli" # Path to your LLM executable
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf" # Path to your model file

def ask_local_llm(prompt):
    formatted_prompt = f"[INST] {prompt} [/INST]"
    print("\n[Echo Thinking] Sending prompt to LLM...")
    print(f"[Prompt] {formatted_prompt}")

    start = time.time()
    full_response = ""
    continuation_count = 0

    try:
        while True:
            # Use original prompt for first generation, then ask to continue
            if continuation_count == 0:
                current_prompt = formatted_prompt
            else:
                current_prompt = full_response + " [Continue the response]"
            
            process = subprocess.Popen(
                [
                    LLM_PATH,
                    "-m", MODEL_PATH,
                    "-p", current_prompt,
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
            last_output_time = time.time()
            stall_timeout = 3  # Shorter timeout - 3 seconds
            process_terminated = False
            
            while True:
                line = process.stdout.readline()
                if not line:
                    # Check if process is still running
                    if process.poll() is not None:
                        break
                    # Check if we've been waiting too long for output
                    if time.time() - last_output_time > stall_timeout:
                        print("[Echo] Generation seems stalled, continuing to next part...")
                        process.terminate()
                        process_terminated = True
                        break
                    time.sleep(0.1)
                    continue
                
                print(f"[LLM] {line.strip()}")
                output_lines.append(line)
                last_output_time = time.time()

            # Wait a bit for process to finish cleanly
            if not process_terminated:
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            stderr = process.stderr.read()
            if stderr:
                print(f"[LLM STDERR] {stderr.strip()}")

            current_output = "".join(output_lines).strip()
            
            # Always add to response, even if it was terminated
            if continuation_count == 0:
                full_response = current_output
            else:
                # For continuations, append only new content
                if current_output:  # Only add if there's actually content
                    full_response += " " + current_output
            
            # Check if response seems complete OR if we got very little new content
            if (current_output.endswith(('.', '!', '?')) or 
                len(current_output) < 20 or  # Very short response likely complete
                continuation_count >= 4):  # Reduced safety limit
                break
            
            # Continue if we have content or if this was the first iteration
            if current_output or continuation_count == 0:
                continuation_count += 1
                print(f"[Echo] Continuing generation... (part {continuation_count + 1})")
            else:
                print("[Echo] No new content generated, stopping.")
                break

        duration = round(time.time() - start, 2)
        print(f"[LLM Completed] Took {duration} seconds with {continuation_count} continuations.")

        return full_response

    except Exception as e:
        return f"[LLM Error] {e}"
