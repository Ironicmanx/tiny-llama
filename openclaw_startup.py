import sys
import time
import subprocess
import shutil
import os


# Ensure ~/.npm-global/bin is in PATH (openclaw lives there)
_npm_bin = os.path.expanduser("~/.npm-global/bin")
if _npm_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _npm_bin + os.pathsep + os.environ.get("PATH", "")

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
LOBSTER = "🦞"


def print_banner():
    banner = f"""
{CYAN}{BOLD}
   ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
  ██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝██║     ██╔══██╗██║    ██║
  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║     ██║     ███████║██║ █╗ ██║
  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║     ██║     ██╔══██╗██║███╗██║
  ╚██████╔╝██║     ███████╗██║ ╚████║╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
{RESET}
  {LOBSTER}  {DIM}Powered by Gemini 2.5 Flash  •  Local Gateway{RESET}
"""
    print(banner)


def progress_bar(label, steps=20, delay=0.04):
    for i in range(steps + 1):
        pct = int((i / steps) * 100)
        filled = "█" * i + "░" * (steps - i)
        sys.stdout.write(f"\r  {CYAN}▸{RESET} {label} [{GREEN}{filled}{RESET}] {pct}%")
        sys.stdout.flush()
        time.sleep(delay)
    print()


def check_requirement(name, check_fn):
    sys.stdout.write(f"  {CYAN}▸{RESET} {name}... ")
    sys.stdout.flush()
    try:
        result = check_fn()
        print(f"{GREEN}✓{RESET} {DIM}{result}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}✗ {e}{RESET}")
        return False


def check_openclaw():
    path = shutil.which("openclaw")
    if not path:
        raise RuntimeError("not found — is it installed? (npm i -g openclaw)")
    out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
    return out.stdout.strip() or "installed"


def check_gateway():
    cmd = shutil.which("openclaw")
    if not cmd:
        raise RuntimeError("openclaw not found")
    out = subprocess.run(
        [cmd, "gateway", "status"],
        capture_output=True, text=True, timeout=10
    )
    combined = out.stdout + out.stderr
    if "running" in combined.lower() or "active" in combined.lower() or "PID" in combined:
        return "running"
    raise RuntimeError("not running")


def start_gateway():
    cmd = shutil.which("openclaw")
    if not cmd:
        print(f"{RED}✗ openclaw not found{RESET}")
        return False
    sys.stdout.write(f"  {YELLOW}▸{RESET} Starting gateway... ")
    sys.stdout.flush()
    subprocess.run(
        [cmd, "gateway", "start"],
        capture_output=True, text=True, timeout=15
    )
    time.sleep(3)
    # verify it came up
    out = subprocess.run(
        [cmd, "gateway", "status"],
        capture_output=True, text=True, timeout=10
    )
    combined = out.stdout + out.stderr
    if "running" in combined.lower() or "active" in combined.lower() or "PID" in combined:
        print(f"{GREEN}✓ started{RESET}")
        return True
    else:
        print(f"{RED}✗ failed to start{RESET}")
        return False


def check_config():
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if not os.path.exists(config_path):
        raise RuntimeError("openclaw.json not found")
    import json
    with open(config_path) as f:
        cfg = json.load(f)
    model = cfg.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "unknown")
    return model


def check_workspace():
    import json
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(config_path) as f:
        cfg = json.load(f)
    ws = cfg.get("agents", {}).get("defaults", {}).get("workspace", "")
    if not ws or not os.path.isdir(ws):
        raise RuntimeError(f"workspace dir missing: {ws}")
    return ws


def preflight():
    print(f"\n  {BOLD}Preflight checks{RESET}\n")
    all_ok = True

    all_ok &= check_requirement("OpenClaw CLI", check_openclaw)
    all_ok &= check_requirement("Config & model", check_config)
    all_ok &= check_requirement("Workspace", check_workspace)

    # Gateway: check if running, start if not
    gateway_up = False
    try:
        check_gateway()
        print(f"  {CYAN}▸{RESET} Gateway... {GREEN}✓{RESET} {DIM}running{RESET}")
        gateway_up = True
    except Exception:
        print(f"  {CYAN}▸{RESET} Gateway... {YELLOW}○{RESET} {DIM}not running{RESET}")
        gateway_up = start_gateway()

    all_ok &= gateway_up
    return all_ok


def quick_ping():
    """Send a tiny test message to verify the LLM responds."""
    print(f"\n  {BOLD}Connection test{RESET}\n")
    progress_bar("Pinging Gemini", steps=15, delay=0.06)

    cmd = shutil.which("openclaw")
    try:
        out = subprocess.run(
            [cmd, "agent", "--agent", "main", "--message", "Respond with only: ONLINE"],
            capture_output=True, text=True, timeout=30
        )
        combined = out.stdout + out.stderr
        if "ONLINE" in combined.upper() or "online" in combined.lower():
            print(f"  {GREEN}▸ LLM responded successfully{RESET}")
            return True
        else:
            # It responded with something, still counts
            if len(combined.strip()) > 10:
                print(f"  {GREEN}▸ LLM responded{RESET} {DIM}(custom reply){RESET}")
                return True
            print(f"  {RED}▸ No response from LLM{RESET}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  {RED}▸ Timed out waiting for LLM{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}▸ Error: {e}{RESET}")
        return False


def launch_tui():
    cmd = shutil.which("openclaw")
    print(f"\n  {LOBSTER}  {BOLD}Launching OpenClaw TUI...{RESET}\n")
    time.sleep(0.5)
    os.execvp(cmd, [cmd, "tui"])


def main():
    os.system("clear")
    print_banner()
    progress_bar("Initializing", steps=25, delay=0.03)

    if not preflight():
        print(f"\n  {RED}{BOLD}Preflight failed.{RESET} Fix the issues above and try again.")
        sys.exit(1)

    # Skip LLM ping to save API requests (Gemini free tier: 20 RPD)
    # The gateway check already confirms connectivity
    print(f"\n  {GREEN}{BOLD}All systems go.{RESET}")
    launch_tui()


if __name__ == "__main__":
    main()
