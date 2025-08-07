
#from web_tools import maybe_search_online
#from commands import try_command

from llm import ask_local_llm

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
