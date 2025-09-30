import os
import sys
import subprocess
import zipfile
import io
import threading
from logger import Logger
logger = Logger("bootstrap")

__version__ = "3.0.0"

GITHUB_REPO = "enhancedrock/squishy"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ZIP_URL_TEMPLATE = "https://github.com/{repo}/archive/refs/tags/{tag}.zip"

def get_latest_release_version():
    """Fetch the latest release version from GitHub API"""
    import requests
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["tag_name"], data["zipball_url"]

def version_tuple(v):
    """Convert version string to a tuple of integers for comparison"""
    return tuple(map(int, (v.lstrip('v').split("."))))

def is_in_venv():
    """Check if we're currently running in a virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def get_venv_path():
    """Get the path to the virtual environment directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "venv")

def check_python_version():
    """Check if we're running Python 3.10 or higher"""
    if sys.version_info < (3, 10):
        logger.error(f"Python 3.10 or higher is required. Current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        logger.error("Please install Python 3.10+ and run the script with that version.")
        sys.exit(1)
    else:
        logger.info(f"Python version check passed: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

def find_python310():
    """Find Python 3.10+ executable"""
    # Try common Python 3.10+ executable names
    python_candidates = [
        "python3.10", "python3.11", "python3.12", "python3.13",
        "python3", "python"
    ]
    
    for candidate in python_candidates:
        try:
            result = subprocess.run([candidate, "--version"], 
                                  capture_output=True, text=True, check=True)
            version_output = result.stdout.strip()
            # Extract version number
            version_parts = version_output.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])
            
            if major == 3 and minor >= 10:
                logger.info(f"Found suitable Python: {candidate} ({version_output})")
                return candidate
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
            continue
    
    logger.error("Could not find Python 3.10+ in PATH")
    logger.error("Please install Python 3.10+ and make sure it's accessible via one of these commands:")
    logger.error("  python3.10, python3.11, python3.12, python3, or python")
    sys.exit(1)

def create_and_activate_venv():
    """Create a virtual environment and install requirements"""
    # First check if current Python is 3.10+
    check_python_version()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = get_venv_path()
    requirements_path = os.path.join(script_dir, "requirements.txt")
    
    # Find Python 3.10+ executable
    python_executable = find_python310()
    
    # Check if venv already exists
    if os.path.exists(venv_path):
        logger.info("Virtual environment already exists")
    else:
        logger.info(f"Creating virtual environment with {python_executable}...")
        # Use the found Python 3.10+ executable to create venv
        subprocess.run([python_executable, "-m", "venv", venv_path], check=True)
        logger.info(f"Virtual environment created at {venv_path}")
    
    # Determine the python executable path in the venv
    if sys.platform == "win32":
        venv_python = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_path, "bin", "python")
    
    # Install requirements if the file exists
    if os.path.exists(requirements_path):
        logger.info("Installing requirements...")
        try:
            subprocess.run([venv_python, "-m", "pip", "install", "-r", requirements_path], 
                          capture_output=True, text=True, check=True)
            logger.info("Requirements installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install requirements: {e}")
            logger.error(f"stderr: {e.stderr}")
            return False
    else:
        logger.warning("No requirements.txt found, skipping package installation")
    
    # Re-run the script with the venv python
    logger.info("Restarting with virtual environment...")
    os.execv(venv_python, [venv_python] + sys.argv)

def ensure_venv():
    """Ensure we're running in the local virtual environment"""
    # First check if current Python is 3.10+
    check_python_version()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = get_venv_path()
    requirements_path = os.path.join(script_dir, "requirements.txt")
    
    # Determine the python executable path in the local venv
    if sys.platform == "win32":
        venv_python = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_path, "bin", "python")
    
    # Always ensure requirements are up to date
    def install_requirements():
        if os.path.exists(requirements_path):
            logger.info("Installing/updating requirements...")
            try:
                subprocess.run([venv_python, "-m", "pip", "install", "-r", requirements_path], 
                              capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install requirements: {e}")
                logger.error(f"stderr: {e.stderr}")
                return False
        else:
            logger.warning("No requirements.txt found, skipping package installation")
            return True
    
    # Check if we're already running with the correct local venv python
    if sys.executable == venv_python:
        logger.info("Already running in the local virtual environment")
        # Still update requirements even if already in the right venv
        install_requirements()
        return
    
    logger.info(f"Switching to local virtual environment at {venv_path}")
    
    if os.path.exists(venv_path):
        # Venv exists, install/update requirements and activate it
        logger.info("Local virtual environment found, installing/updating requirements...")
        
        # Install requirements
        if not install_requirements():
            return False
        
        logger.info("Restarting with local virtual environment...")
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        # No venv, create one
        logger.info("Local virtual environment not found, creating...")
        create_and_activate_venv()

def update_to_latest(zip_url, target_dir):
    """Download and extract the latest release zip to target_dir"""
    logger.info(f"Downloading update from {zip_url}...")
    import requests
    resp = requests.get(zip_url, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        # Source zip always has a top-level folder, extract its contents over target_dir
        top_leve = z.namelist()[0].split("/")[0]
        for member in z.namelist():
            if member.endswith("/"):
                continue
            rel_path = os.path.relpath(member, top_leve)
            if rel_path == ".":
                continue
            dest_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with z.open(member) as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
    print("Update complete! Please restart the application.")
    sys.exit(0)

def main():
    """Check for updates"""
    # Ensure we're running in a virtual environment
    ensure_venv()
    
    try:
        latest_version, zip_url = get_latest_release_version()
        if version_tuple(__version__) < version_tuple(latest_version):
            logger.info(f"New version available: {latest_version} (current: {__version__})")
            user_input = input("Do you want to update now? (y/n): ").strip().lower()
            if user_input == 'y':
                update_to_latest(zip_url, os.path.dirname(os.path.abspath(__file__)))
            else:
                logger.info("Update skipped.")
    except Exception as e:
        logger.exception(f"Error checking for updates: {e}")

def run_subprocess_with_output(script_name, script_path):
    """Run a subprocess and stream its output to the terminal"""
    logger.info(f"Starting {script_name}...")
    try:
        # Use subprocess.run instead of Popen to run in foreground
        result = subprocess.run([sys.executable, script_path], 
                              check=False,  # Don't raise exception on non-zero exit
                              text=True)
        logger.info(f"{script_name} finished with exit code: {result.returncode}")
        return result.returncode
    except Exception as e:
        logger.error(f"Error running {script_name}: {e}")
        return 1

if __name__ == "__main__":
    main()
    
    # Run bot and dashboard simultaneously
    script_dir = os.path.dirname(__file__)
    bot_path = os.path.join(script_dir, "bot.py")
    dashboard_path = os.path.join(script_dir, "dashboard.py")
    
    def run_bot():
        run_subprocess_with_output("bot.py", bot_path)
    
    def run_dashboard():
        run_subprocess_with_output("dashboard.py", dashboard_path)
    
    # Start both in separate threads
    bot_thread = threading.Thread(target=run_bot, name="BotThread")
    dashboard_thread = threading.Thread(target=run_dashboard, name="DashboardThread")

    bot_thread.start()
    dashboard_thread.start()
    
    try:
        # Wait for both to complete
        bot_thread.join()
        dashboard_thread.join()
        logger.info("Both processes have finished.")
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
        sys.exit(0)