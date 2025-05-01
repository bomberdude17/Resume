import os
import subprocess

def build_exe():
    script_name = "Unemployment gadget.py"
    if not os.path.exists(script_name):
        print(f"❌ File not found: {script_name}")
        return

    command = [
        "pyinstaller",
        "--onefile",
        "--clean",
        script_name
    ]

    print("🛠 Building executable...")
    subprocess.run(command)

if __name__ == "__main__":
    build_exe()