
#from web_tools import maybe_search_online
#from commands import try_command

from llm import ask_local_llm
import os
import time
import sys

def do_you_want_to_start():

    capabilities = [
        "Natural language understanding",
        "Local LLM-powered responses",
        "Text command processing",
        "Safe and private (runs locally)",
        "Easy exit anytime"
    ]

    print("Echo: Initializing...")
    for i, cap in enumerate(capabilities, 1):
        print(f"  • {cap}")
        time.sleep(0.4)

    # Loading bar
    bar_length = 30
    print("Echo: Loading...", end=" ")
    for i in range(bar_length + 1):
        percent = int((i / bar_length) * 100)
        bar = "#" * i + "-" * (bar_length - i)
        sys.stdout.write(f"\rEcho: Loading... [{bar}] {percent}%")
        sys.stdout.flush()
        time.sleep(0.04)
    print("\nEcho: Ready to execute!")

    answer = input("Echo: Do you want to start? (y/n): ").strip().lower()

    while answer not in ("y", "yes") and answer not in ("n", "no"):
        print("Echo: Please answer with 'y' or 'n'.")
        answer = input("Echo: Do you want to start? (y/n): ").strip().lower()

    return answer in ("y", "yes")


if not do_you_want_to_start():
    print("Echo: Exiting before start.")
    exit()


def main():
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

        except KeyboardInterrupt:
            print("\nEcho: Exiting.")
            break
        except Exception as e:
            print(f"Echo: [Error] {e}")

if __name__ == "__main__":
    main()
