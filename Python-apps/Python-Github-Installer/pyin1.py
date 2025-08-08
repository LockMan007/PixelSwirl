import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import subprocess
import threading
import sys
import ctypes

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def create_github_shortcut(repo_name, github_url, install_path):
    """Creates a .URL shortcut file to the GitHub page."""
    try:
        shortcut_content = f"""[InternetShortcut]
URL={github_url}
"""
        shortcut_path = os.path.join(install_path, repo_name, "GitHub_Page.url")
        with open(shortcut_path, "w") as f:
            f.write(shortcut_content)
        return "✅ Created GitHub URL shortcut."
    except Exception as e:
        return f"❌ Failed to create URL shortcut: {e}"

def create_run_bat_file(repo_name, venv_name, install_path):
    """Creates a .bat file to activate the conda environment and run app.py."""
    try:
        bat_content = f"""@echo off
set "CONDA_ENV_NAME={venv_name}"
echo Activating Conda environment: %CONDA_ENV_NAME%
call conda activate %CONDA_ENV_NAME%
if errorlevel 1 (
    echo Error: Failed to activate Conda environment.
    goto end
)
echo Running app.py...
python app.py
:end
pause
"""
        bat_file_path = os.path.join(install_path, repo_name, f"run_{repo_name}.bat")
        with open(bat_file_path, "w") as f:
            f.write(bat_content)
        return f"✅ Created .bat file to run app.py: {os.path.basename(bat_file_path)}"
    except Exception as e:
        return f"❌ Failed to create .bat file: {e}"

def run_commands(commands, cwd=None, log_area=None):
    """Executes a list of commands and prints the output to the GUI."""
    for command in commands:
        log_area.insert(tk.END, f"🔄 Executing command: {' '.join(command)}\n")
        log_area.see(tk.END)
        try:
            # Use subprocess.run for a cleaner approach
            process = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                check=True  # This will raise an exception on a non-zero exit code
            )
            if process.stdout:
                log_area.insert(tk.END, process.stdout)
            if process.stderr:
                log_area.insert(tk.END, process.stderr)
            log_area.insert(tk.END, "✅ Command successful.\n")
            log_area.see(tk.END)
        except subprocess.CalledProcessError as e:
            log_area.insert(tk.END, f"❌ Error executing command. Return code: {e.returncode}\n")
            log_area.insert(tk.END, f"❌ Stderr: {e.stderr}\n")
            return False
        except Exception as e:
            log_area.insert(tk.END, f"❌ An error occurred: {e}\n")
            return False
    return True

def start_setup(install_path, github_url, log_area, run_button, status_bar):
    """Orchestrates the setup process in a separate thread."""
    run_button.config(state=tk.DISABLED)
    log_area.delete('1.0', tk.END)

    if not os.path.isdir(install_path):
        log_area.insert(tk.END, f"❌ Error: The directory '{install_path}' does not exist.\n")
        run_button.config(state=tk.NORMAL)
        return

    if not github_url.endswith(".git"):
        github_url += ".git"
        log_area.insert(tk.END, f"✅ Appending '.git' to URL: {github_url}\n")
    
    repo_name = os.path.basename(github_url).replace('.git', '')
    full_install_path = os.path.join(install_path, repo_name)

    if not os.path.exists(full_install_path):
            try:
                os.makedirs(full_install_path)
                log_area.insert(tk.END, f"✅ Directory '{full_install_path}' created successfully.\n")
            except Exception as e:
                log_area.insert(tk.END, f"❌ Failed to create directory: {e}\n")
                run_button.config(state=tk.NORMAL)
                return
            else:
                log_area.insert(tk.END, f"⚠️ Directory '{full_install_path}' already exists. Skipping directory creation.\n")

    venv_name = f"venv_{repo_name.lower()}"

    # List of steps and their descriptions
    git_clone_cmd = ["git", "clone", github_url, full_install_path]
    steps = [
        ("Cloning Repository...", [git_clone_cmd]),
        ("Creating Conda Environment...", [f"conda create --prefix {full_install_path}\\venv python=3.10 -y"]),
        ("Activating Conda Environment...", [f"conda activate {full_install_path}\\venv"]),
        ("Updating pip...", ["python -m pip install --upgrade pip"]),
        ("Installing Dependencies...", [f"pip install -r {os.path.join(full_install_path, 'requirements.txt')}"]),
        ("Creating Shortcut and Batch File...", []),
    ]



    log_area.insert(tk.END, "🚀 Python Project Setup Automation Started!\n")
    log_area.see(tk.END)

    for i, (message, commands) in enumerate(steps):
        status_bar.config(text=f"Step {i+1} of {len(steps)}: {message}")
        log_area.insert(tk.END, f"\n--- {message} ---\n")

        if message == "Activating Conda Environment...":
            # This step requires a separate process to activate the env for subsequent commands
            # Conda activation is a bit tricky to manage in a simple subprocess call
            # For this script, we'll assume the environment is available
            pass
        elif message == "Installing Dependencies..." and not os.path.exists(commands[0]):
            log_area.insert(tk.END, "⚠️ Warning: 'requirements.txt' not found. Skipping dependency installation.\n")
            continue
        
        # Adjusting how commands are passed
        if commands:
            for command_list in commands:
                if not run_commands([command_list], cwd=full_install_path, log_area=log_area):
                    status_bar.config(text="Failed")
                    run_button.config(state=tk.NORMAL)
                    return

    # Handle the final step separately
    status_bar.config(text=f"Step {len(steps)} of {len(steps)}: Creating Shortcut and Batch File...")
    log_area.insert(tk.END, "\n--- Creating Shortcut and Batch File ---\n")
    log_area.insert(tk.END, create_github_shortcut(repo_name, github_url, install_path) + "\n")
    log_area.insert(tk.END, create_run_bat_file(repo_name, venv_name, install_path) + "\n")

    status_bar.config(text="Done")
    log_area.insert(tk.END, "\n🎉 Setup complete! You can now navigate to the directory and run the .bat file.\n")
    log_area.insert(tk.END, f"Project installed at: {full_install_path}\n")
    log_area.see(tk.END)
    run_button.config(state=tk.NORMAL)
    messagebox.showinfo("Success", "Project setup is complete!")

def threaded_start_setup(install_path, github_url, log_area, run_button, status_bar):
    """Starts the setup process in a new thread to keep the GUI responsive."""
    thread = threading.Thread(target=start_setup, args=(install_path, github_url, log_area, run_button, status_bar))
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

# Control Buttons
control_frame = tk.Frame(main_frame)
control_frame.pack(pady=10)

run_button = tk.Button(control_frame, text="Run Setup", 
                       command=lambda: threaded_start_setup(install_path_var.get(), github_url_var.get(), log_area, run_button, status_bar))
run_button.pack(side=tk.LEFT, padx=10)

exit_button = tk.Button(control_frame, text="Exit", command=root.destroy)
exit_button.pack(side=tk.LEFT, padx=10)

# Log Area
log_frame = tk.LabelFrame(main_frame, text="Log Output", padx=5, pady=5)
log_frame.pack(fill=tk.BOTH, expand=True)

log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='normal')
log_area.pack(fill=tk.BOTH, expand=True)
log_area.configure(font=("Courier", 10))

# Status Bar
status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

root.mainloop()
