import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import subprocess
import threading
import sys
import ctypes
import shutil

# --- Configuration and Helper Functions ---

# Define the log file name
LOG_FILE = "install_log.txt"

def update_log(log_area, message, is_error=False):
    """
    Updates the GUI log area and writes to a log file.
    Temporarily enables the widget to write, then disables it.
    """
    if is_error:
        message = f"❌ {message}"
    
    log_area.config(state='normal')
    log_area.insert(tk.END, message + "\n")
    log_area.see(tk.END)
    log_area.config(state='disabled')
    
    # Explicitly set encoding to UTF-8 for the log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def create_github_shortcut(repo_name, github_url, install_path, log_area):
    """Creates a .URL shortcut file to the GitHub page."""
    try:
        shortcut_content = f"""[InternetShortcut]
URL={github_url}
"""
        shortcut_path = os.path.join(install_path, repo_name, "GitHub_Page.url")
        # Explicitly set encoding to UTF-8
        with open(shortcut_path, "w", encoding="utf-8") as f:
            f.write(shortcut_content)
        update_log(log_area, "✅ Created GitHub URL shortcut.")
    except Exception as e:
        update_log(log_area, f"❌ Failed to create URL shortcut: {e}", is_error=True)

def create_run_bat_file(repo_name, venv_path, install_path, log_area):
    """Creates a .bat file to activate the conda environment and run app.py."""
    try:
        bat_content = f"""@echo off
set CONDA_PREFIX="{venv_path}"
echo Activating Conda environment: %CONDA_PREFIX%
call conda activate "%CONDA_PREFIX%"
if errorlevel 1 (
    echo Error: Failed to activate Conda environment.
    pause
    exit /b 1
)
echo Running app.py...
python app.py
:end
pause
"""
        bat_file_path = os.path.join(install_path, repo_name, f"run_{repo_name}.bat")
        # Explicitly set encoding to UTF-8
        with open(bat_file_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        update_log(log_area, f"✅ Created .bat file to run app.py: {os.path.basename(bat_file_path)}")
    except Exception as e:
        update_log(log_area, f"❌ Failed to create .bat file: {e}", is_error=True)

def run_commands(commands, cwd=None, log_area=None):
    """Executes a list of commands and prints the output to the GUI."""
    for command in commands:
        command_str = " ".join(command)
        update_log(log_area, f"🔄 Executing command: {command_str}")
        try:
            process = subprocess.run(
                command_str,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8", # Force UTF-8 decoding for subprocess output
                errors='ignore'  # Ignore any decoding errors
            )
            if process.stdout:
                update_log(log_area, process.stdout.strip())
            if process.stderr:
                update_log(log_area, process.stderr.strip(), is_error=True)
            update_log(log_area, "✅ Command successful.")
        except subprocess.CalledProcessError as e:
            update_log(log_area, f"❌ Error executing command. Return code: {e.returncode}", is_error=True)
            if e.stdout:
                update_log(log_area, e.stdout.strip())
            if e.stderr:
                update_log(log_area, e.stderr.strip())
            return False
        except Exception as e:
            update_log(log_area, f"❌ An error occurred: {e}", is_error=True)
            return False
    return True

# --- Main Setup Logic ---

def start_setup(install_path, github_url, python_version, log_area, run_button, status_bar):
    """Orchestrates the setup process in a separate thread."""
    run_button.config(state=tk.DISABLED)
    
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    update_log(log_area, "")

    if not os.path.isdir(install_path):
        update_log(log_area, f"❌ Error: The directory '{install_path}' does not exist.", is_error=True)
        run_button.config(state=tk.NORMAL)
        return

    if not github_url.endswith(".git"):
        github_url += ".git"
        update_log(log_area, f"✅ Appending '.git' to URL: {github_url}")
    
    repo_name = os.path.basename(github_url).replace('.git', '')
    full_install_path = os.path.join(install_path, repo_name)
    
    if os.path.exists(full_install_path):
        update_log(log_area, f"⚠️ Directory '{full_install_path}' already exists. Skipping directory creation.")
    else:
        try:
            os.makedirs(full_install_path)
            update_log(log_area, f"✅ Directory '{full_install_path}' created successfully.")
        except Exception as e:
            update_log(log_area, f"❌ Failed to create directory: {e}", is_error=True)
            run_button.config(state=tk.NORMAL)
            return

    venv_path = os.path.join(full_install_path, 'venv')

    git_clone_cmd = ["git", "clone", github_url, full_install_path]
    conda_create_cmd = ["conda", "create", "--prefix", f'"{venv_path}"', f"python={python_version}", "-y"]
    conda_activate_cmd = ["conda", "activate", f'"{venv_path}"']
    pip_update_cmd = ["python", "-m", "pip", "install", "--upgrade", "pip"]
    requirements_path = os.path.join(full_install_path, 'requirements.txt')
    pip_install_cmd = ["pip", "install", "-r", f'"{requirements_path}"']
    
    steps = [
        ("Cloning Repository...", [git_clone_cmd]),
        ("Creating Conda Environment...", [conda_create_cmd]),
        ("Activating Conda Environment...", [conda_activate_cmd]),
        ("Updating pip...", [pip_update_cmd]),
        ("Installing Dependencies...", [pip_install_cmd]),
    ]
    
    update_log(log_area, "🚀 Python Project Setup Automation Started!")
    
    for i, (message, commands) in enumerate(steps):
        status_bar.config(text=f"Step {i+1} of {len(steps) + 1}: {message}")
        update_log(log_area, f"\n--- {message} ---")
        
        if message == "Installing Dependencies...":
            if not os.path.exists(requirements_path):
                update_log(log_area, "⚠️ Warning: 'requirements.txt' not found. Skipping dependency installation.")
                continue

        if not run_commands(commands, cwd=full_install_path, log_area=log_area):
            status_bar.config(text="Failed")
            run_button.config(state=tk.NORMAL)
            return

    status_bar.config(text=f"Step {len(steps) + 1} of {len(steps) + 1}: Creating Shortcut and Batch File...")
    update_log(log_area, "\n--- Creating Shortcut and Batch File ---")
    create_github_shortcut(repo_name, github_url, install_path, log_area)
    create_run_bat_file(repo_name, venv_path, install_path, log_area)

    status_bar.config(text="Done")
    update_log(log_area, "\n🎉 Setup complete! You can now navigate to the directory and run the .bat file.")
    update_log(log_area, f"Project installed at: {full_install_path}")
    run_button.config(state=tk.NORMAL)
    messagebox.showinfo("Success", "Project setup is complete!")

def threaded_start_setup(install_path, github_url, python_version, log_area, run_button, status_bar):
    """Starts the setup process in a new thread to keep the GUI responsive."""
    thread = threading.Thread(target=start_setup, args=(install_path, github_url, python_version, log_area, run_button, status_bar))
    thread.daemon = True
    thread.start()

# --- Main GUI Setup ---

if not is_admin():
    messagebox.showerror("Permission Denied",
                         "This application must be run as an administrator.\n\n"
                         "To fix this, create a shortcut to your Python executable "
                         "and set it to run as an administrator. Then, add this "
                         "script as an argument to the shortcut.")
    sys.exit()

# Force the console to use UTF-8 encoding
try:
    subprocess.run("chcp 65001", shell=True, check=True, capture_output=True)
except Exception:
    pass

root = tk.Tk()
root.title("Python Project Setup Automation")
root.geometry("800x600")

main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Install Path Section
path_frame = tk.Frame(main_frame)
path_frame.pack(fill=tk.X, pady=5)

tk.Label(path_frame, text="Installation Directory:").pack(side=tk.LEFT)
install_path_var = tk.StringVar(value="d:\\ai\\apps\\")
install_path_entry = tk.Entry(path_frame, textvariable=install_path_var, width=50)
install_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

def browse_directory():
    directory = filedialog.askdirectory()
    if directory:
        install_path_var.set(directory)

browse_button = tk.Button(path_frame, text="Browse", command=browse_directory)
browse_button.pack(side=tk.LEFT)

# GitHub URL Section
url_frame = tk.Frame(main_frame)
url_frame.pack(fill=tk.X, pady=5)

tk.Label(url_frame, text="GitHub URL:").pack(side=tk.LEFT)
github_url_var = tk.StringVar()
github_url_entry = tk.Entry(url_frame, textvariable=github_url_var, width=50)
github_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

# Python Version Section
python_version_frame = tk.Frame(main_frame)
python_version_frame.pack(fill=tk.X, pady=5)

tk.Label(python_version_frame, text="Python Version:").pack(side=tk.LEFT)
python_version_var = tk.StringVar(value="3.11")
python_version_entry = tk.Entry(python_version_frame, textvariable=python_version_var, width=10)
python_version_entry.pack(side=tk.LEFT, padx=5)

# Control Buttons
control_frame = tk.Frame(main_frame)
control_frame.pack(pady=10)

run_button = tk.Button(control_frame, text="Run Setup", 
                       command=lambda: threaded_start_setup(install_path_var.get(), github_url_var.get(), python_version_var.get(), log_area, run_button, status_bar))
run_button.pack(side=tk.LEFT, padx=10)

exit_button = tk.Button(control_frame, text="Exit", command=root.destroy)
exit_button.pack(side=tk.LEFT, padx=10)

# Log Area
log_frame = tk.LabelFrame(main_frame, text="Log Output", padx=5, pady=5)
log_frame.pack(fill=tk.BOTH, expand=True)

log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled')
log_area.pack(fill=tk.BOTH, expand=True)
log_area.configure(font=("Courier", 10))

# Status Bar
status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

root.mainloop()
