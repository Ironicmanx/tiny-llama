import sys
import time

def do_you_want_to_start():
    """Sleeper function right now but will be expanded into preignition"""
    capabilities = [
        "Natural language understanding",
        "Local LLM-powered responses", 
        "Text command processing",
        "Safe and private (runs locally)",
        "Easy exit anytime"
    ]

    print("Echo: Initializing...")
    for i, cap in enumerate(capabilities, 1):
        print(f"  • {cap}", end="")
        
        # Small progress bar for each capability
        bar_length = 10
        for j in range(bar_length + 1):
            bar = "#" * j + " " * (bar_length - j)
            sys.stdout.write(f"\r  • {cap} [{bar}] {int((j/bar_length)*100)}%")
            sys.stdout.flush()
            time.sleep(0.1)
        
        print()  # Move to next line after progress bar completes
        time.sleep(0.2)

    # Main loading bar
    bar_length = 30
    print("Echo: Loading core processes...", end=" ")
    for i in range(bar_length + 1):
        percent = int((i / bar_length) * 100)
        bar = "#" * i + "-" * (bar_length - i)
        sys.stdout.write(f"\rEcho: Loading core processes... [{bar}] {percent}%")
        sys.stdout.flush()
        time.sleep(0.04)
    print("\nEcho: Ready to execute!")

    answer = input("Echo: Do you want to start? (y/n): ").strip().lower()

    while answer not in ("y", "yes") and answer not in ("n", "no"):
        print("Echo: Please answer with 'y' or 'n'.")
        answer = input("Echo: Do you want to start? (y/n): ").strip().lower()

    return answer in ("y", "yes")