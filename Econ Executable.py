import os
import subprocess
import sys
import importlib.util

REQUIRED_PACKAGES = [
    "pandas",
    "matplotlib",
    "seaborn",
    "beautifulsoup4",
    "requests",
    "python-dateutil",
    "pyinstaller"
]

def ensure_packages_installed():
    print("🔍 Checking for required packages...")
    for package in REQUIRED_PACKAGES:
        package_import = package.split("-")[0].replace("-", "_")
        if importlib.util.find_spec(package_import) is None:
            print(f"📦 Installing missing package: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        else:
            print(f"✅ {package} is already installed.")

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
    ensure_packages_installed()
    build_exe()
    print("✅ Done.")