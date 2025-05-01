import os
import sys
import subprocess
import platform

REQ_FILE = "requirements.txt"
SCRIPT   = "Econgadget.py"

def ensure_requirements():
    """If requirements.txt is present, pip‐install everything in it."""
    if os.path.exists(REQ_FILE):
        print(f"[INFO] Installing dependencies from {REQ_FILE}…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "-r", REQ_FILE])
    else:
        print(f"[WARN] {REQ_FILE} not found; skipping dependency install.")

def launch_in_new_terminal():
    """Open a new terminal window/process that runs Econgadget.py."""
    python = sys.executable
    script = os.path.abspath(SCRIPT)

    system = platform.system()
    if system == "Windows":
        # Creates a new console window on Windows
        from subprocess import CREATE_NEW_CONSOLE
        subprocess.Popen([python, script], creationflags=CREATE_NEW_CONSOLE)
    elif system == "Linux":
        # Try common Linux terminals
        for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            if shutil.which(term):
                subprocess.Popen([term, "--", python, script])
                return
        # Fallback
        subprocess.Popen([python, script])
    elif system == "Darwin":
        # macOS: open Terminal.app and run the script
        subprocess.Popen(["open", "-a", "Terminal.app", script])
    else:
        # Unknown OS: just run in‐place
        subprocess.Popen([python, script])
def main():
    ensure_requirements()
    launch_in_new_terminal()
    input("Press ENTER here to close launcher…")
if __name__ == "__main__":
    main()