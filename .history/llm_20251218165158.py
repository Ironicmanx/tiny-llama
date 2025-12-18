#Upgrade module once new cpu arrives - Mistral 7B Instruct GGUF model with llama.cpp

import subprocess
import time
import select
import os

# You need two variables here: the path to your LLM executable and the path to your model file
# You can get models from https://huggingface.co/models?search=gguf
# And you can compile llama.cpp from https://github.com/ggerganov/llama.cpp

LLM_PATH = "/home/arttu/jarvis_local/llama.cpp/build/bin/llama-cli" # Path to your LLM executable
MODEL_PATH = "/home/arttu/jarvis_local/models/mistral-7b-instruct-v0.2.Q4_0.gguf" # Path to your model file

# Configuration constants
STALL_TIMEOUT = 10  # Seconds to wait for new output before considering stalled
MAX_TOTAL_TIME = 120  # Maximum total time for entire generation
MAX_CONTINUATIONS = 3  # Maximum number of continuation attempts
MIN_RESPONSE_LENGTH = 10  # Minimum response length to consider complete


def _read_output_nonblocking(process, timeout):
    """Read output from process without blocking, using select."""
    output_lines = []
    start_time = time.time()
    last_output_time = start_time
    buffer = ""
    
    # Get file descriptor for non-blocking reads
    fd = process.stdout.fileno()
    
    while True:
        # Check if we exceeded total timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"[Echo] Read timeout after {elapsed:.1f}s")
            break
            
        # Check for stall (no output for too long)
        time_since_output = time.time() - last_output_time
        if time_since_output > STALL_TIMEOUT:
            print(f"[Echo] Output stalled for {time_since_output:.1f}s, stopping read")
            break
        
        # Check if process is still running
        if process.poll() is not None:
            # Process finished, read any remaining output using os.read
            try:
                while True:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8', errors='replace')
            except (OSError, BlockingIOError):
                pass
            break
        
        # Use select to check if data is available (non-blocking)
        try:
            ready, _, _ = select.select([process.stdout], [], [], 0.5)
            if ready:
                # Use os.read for non-blocking read
                chunk = os.read(fd, 4096)
                if chunk:
                    buffer += chunk.decode('utf-8', errors='replace')
                    last_output_time = time.time()
                    
                    # Process complete lines from buffer
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            print(f"[LLM] {line.strip()}")
                            output_lines.append(line)
        except (OSError, ValueError, BlockingIOError):
            # Handle select errors gracefully
            break
    
    # Add any remaining buffer content
    if buffer.strip():
        output_lines.append(buffer.strip())
    
    return output_lines


def _is_response_complete(text):
    """Check if the response appears to be complete."""
    if not text:
        return False
    
    text = text.strip()
    
    # Check for sentence-ending punctuation
    if text.endswith(('.', '!', '?', '"', "'", ')', ']')):
        return True
    
    # Check for common ending patterns
    ending_patterns = ['...', '—', '–', ':']
    if any(text.endswith(p) for p in ending_patterns):
        return True
    
    return False


def _clean_response(text):
    """Clean up the LLM response, removing prompt echoes and artifacts."""
    if not text:
        return ""
    
    # Remove common artifacts
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines and common artifacts
        if not line:
            continue
        if line.startswith('[INST]') or line.startswith('[/INST]'):
            continue
        if line.startswith('llama_') or line.startswith('main:'):
            continue
        cleaned_lines.append(line)
    
    return ' '.join(cleaned_lines)


def ask_local_llm(prompt):
    formatted_prompt = f"[INST] {prompt} [/INST]"
>>>>>>> 46c72bda01cb3cdc0ba5fa9f20b0ca361deff459
    print("\n[Echo Thinking] Sending prompt to LLM...")
    print(f"[Prompt] {full_prompt}")

    start = time.time()
    full_response = ""
    continuation_count = 0

    try:
        while True:
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
