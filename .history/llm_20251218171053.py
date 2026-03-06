#Upgrade module once new cpu arrives - Mistral 7B Instruct GGUF model with llama.cpp

import subprocess
import time

# You need two variables here: the path to your LLM executable and the path to your model file
# You can get models from https://huggingface.co/models?search=gguf
# And you can compile llama.cpp from https://github.com/ggerganov/llama.cpp

LLM_PATH = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-cli" # Path to your LLM executable
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf" # Path to your model file

def do_you_want_to_start():
    response = input("Do you want to start the Echo assistant? (y/n): ").strip().lower()
    return response == 'y'
    if response == 'y' or response == 'yes' or response ==:
        return True
    else:
        return False
    


def ask_local_llm(prompt):
    formatted_prompt = f"[INST] {prompt} [/INST]"
    print("\n[Echo Thinking] Sending prompt to LLM...")
    print(f"[Prompt] {full_prompt}")

    start = time.time()
    full_response = ""
    continuation_count = 0

    try:
        while continuation_count <= MAX_CONTINUATIONS:
            # Check total time limit
            if time.time() - start > MAX_TOTAL_TIME:
                print(f"[Echo] Total time limit ({MAX_TOTAL_TIME}s) exceeded, stopping.")
                break
            
            # Use original prompt for first generation, then ask to continue
            if continuation_count == 0:
                current_prompt = formatted_prompt
            else:
                # For continuations, create a new prompt asking to continue
                current_prompt = f"[INST] Continue this response: {full_response[-200:]} [/INST]"
            
            process = subprocess.Popen(
                [
                    LLM_PATH,
                    "-m", MODEL_PATH,
                    "-p", current_prompt,
                    "--threads", "4",
                    "--ctx_size", "512",
                    "--n_predict", "128",
                    "--temp", "0.7",
                    "--top_k", "40",
                    "--top_p", "0.9",
                    "--repeat_penalty", "1.1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # Calculate remaining time for this iteration
            elapsed = time.time() - start
            remaining_time = min(MAX_TOTAL_TIME - elapsed, 60)
            
            # Read output using non-blocking method
            output_lines = _read_output_nonblocking(process, remaining_time)
            
            # Clean up the process
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            
            # Read any stderr
            try:
                stderr = process.stderr.read()
                if stderr:
                    # Ensure stderr is a string (text=True should handle this)
                    stderr_str = stderr if isinstance(stderr, str) else stderr.decode('utf-8', errors='replace')
                    print(f"[LLM STDERR] {stderr_str.strip()[:200]}")
            except Exception:
                pass

            current_output = _clean_response('\n'.join(output_lines))
            
            # Add to response
            if continuation_count == 0:
                full_response = current_output
            elif current_output:
                full_response = full_response.rstrip() + " " + current_output
            
            # Check if we should stop
            if not current_output:
                print("[Echo] No new content generated, stopping.")
                break
            
            if len(current_output) < MIN_RESPONSE_LENGTH:
                print("[Echo] Very short response, likely complete.")
                break
                
            if _is_response_complete(full_response):
                print("[Echo] Response appears complete.")
                break
            
            continuation_count += 1
            if continuation_count <= MAX_CONTINUATIONS:
                print(f"[Echo] Continuing generation... (part {continuation_count + 1})")

        duration = round(time.time() - start, 2)
        print(f"[LLM Completed] Took {duration} seconds with {continuation_count} continuations.")

        return full_response if full_response else "[No response generated]"

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