import subprocess
import json
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# --- Helper function for running PowerShell commands ---

def run_powershell_command(command):
    """Executes a PowerShell command and returns its output."""
    try:
        full_command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"& {{ {command} | ConvertTo-Json -Compress }}\""
        process = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing PowerShell command: {command}")
        print(f"Stderr: {e.stderr}")
        print(f"Stdout: {e.stdout}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# --- Main GUI Application Class ---

class UsbRestarterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB Device Restarter")
        self.root.geometry("600x500") # Set initial window size
        self.root.resizable(False, False) # Make window not resizable

        self.device_map = {} # To store InstanceId mapping for listbox items

        self.check_admin_privileges()
        self.create_widgets()

    def check_admin_privileges(self):
        """Checks if the script is running with administrator privileges."""
        try:
            import ctypes
            self.is_admin = (ctypes.windll.shell32.IsUserAnAdmin() != 0)
        except (AttributeError, ImportError):
            self.is_admin = False # Not on Windows or ctypes not available

        if not self.is_admin:
            messagebox.showwarning(
                "Administrator Privileges Required",
                "This application must be run as an administrator to restart USB devices.\n"
                "Please close this window and run the script again as administrator."
            )
            # Disable buttons if not admin
            self.root.after(100, self.disable_buttons_for_non_admin) # Delay to allow widgets to be created

    def disable_buttons_for_non_admin(self):
        if not self.is_admin:
            if hasattr(self, 'search_button'):
                self.search_button['state'] = tk.DISABLED
            if hasattr(self, 'restart_button'):
                self.restart_button['state'] = tk.DISABLED
            if hasattr(self, 'status_label'):
                 self.status_label.config(text="STATUS: Requires Admin Privileges!", foreground="red")


    def create_widgets(self):
        # --- Search Frame ---
        search_frame = ttk.LabelFrame(self.root, text="Search for Devices", padding="10")
        search_frame.pack(pady=10, padx=10, fill="x")

        ttk.Label(search_frame, text="Search Term:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.insert(0, "wireless") # Default search term
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.search_button = ttk.Button(search_frame, text="Search Devices", command=self.search_devices)
        self.search_button.grid(row=0, column=2, padx=5, pady=5)
        search_frame.columnconfigure(1, weight=1) # Allow entry field to expand

        # --- Device List Frame ---
        list_frame = ttk.LabelFrame(self.root, text="Found Devices", padding="10")
        list_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.device_list = tk.Listbox(list_frame, selectmode=tk.SINGLE, height=10, width=50,
                                       font=('Segoe UI', 10))
        self.device_list.pack(side=tk.LEFT, fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.device_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.device_list.config(yscrollcommand=scrollbar.set)

        # --- Action Frame ---
        action_frame = ttk.Frame(self.root, padding="10")
        action_frame.pack(pady=5, padx=10, fill="x")

        self.restart_button = ttk.Button(action_frame, text="Restart Selected Device", command=self.restart_selected_device)
        self.restart_button.pack(pady=5)

        # --- Status Bar ---
        self.status_label = ttk.Label(self.root, text="STATUS: Ready", relief=tk.SUNKEN, anchor="w")
        self.status_label.pack(side=tk.BOTTOM, fill="x")

        # Initial check to disable buttons if not admin (in case widgets created after check_admin_privileges finishes)
        self.disable_buttons_for_non_admin()


    def search_devices(self):
        """Searches for devices based on the entry field and populates the listbox."""
        if not self.is_admin:
            messagebox.showerror("Error", "Admin privileges are required for this action.")
            return

        search_term = self.search_entry.get().strip()
        self.status_label.config(text=f"STATUS: Searching for '{search_term}'...")
        self.root.update_idletasks() # Update GUI immediately

        self.device_list.delete(0, tk.END) # Clear previous results
        self.device_map = {} # Clear previous mapping

        get_devices_cmd = "Get-PnpDevice | Select-Object FriendlyName, InstanceId, Status"
        json_output = run_powershell_command(get_devices_cmd)

        if not json_output:
            self.status_label.config(text="STATUS: Could not retrieve device list.", foreground="red")
            return

        try:
            devices = json.loads(json_output)
            if not isinstance(devices, list):
                devices = [devices] # Ensure it's a list even if only one device
        except json.JSONDecodeError:
            self.status_label.config(text=f"STATUS: Failed to decode JSON from PowerShell output.", foreground="red")
            return

        found_devices_count = 0
        for device in devices:
            friendly_name = device.get('FriendlyName') or ''
            instance_id = device.get('InstanceId') or ''
            status = device.get('Status', '')

            if search_term.lower() in friendly_name.lower() or search_term.lower() in instance_id.lower():
                display_text = f"Name: {friendly_name} (Status: {status})"
                self.device_list.insert(tk.END, display_text)
                # Corrected: Use the count of found devices as the key
                # This ensures the key matches the listbox item's index
                self.device_map[found_devices_count] = instance_id
                found_devices_count += 1

        if found_devices_count == 0:
            self.status_label.config(text=f"STATUS: No devices found matching '{search_term}'.", foreground="orange")
        else:
            self.status_label.config(text=f"STATUS: Found {found_devices_count} device(s).", foreground="green")

    def restart_selected_device(self):
        """Restarts the currently selected USB device."""
        if not self.is_admin:
            messagebox.showerror("Error", "Admin privileges are required for this action.")
            return

        selected_indices = self.device_list.curselection()
        if not selected_indices:
            messagebox.showwarning("No Device Selected", "Please select a device from the list to restart.")
            return

        selected_index = selected_indices[0]
        instance_id_to_restart = self.device_map.get(selected_index)

        if not instance_id_to_restart:
            messagebox.showerror("Error", "Could not retrieve instance ID for the selected device.")
            return

        selected_device_display = self.device_list.get(selected_index)
        response = messagebox.askyesno(
            "Confirm Restart",
            f"Are you sure you want to restart:\n'{selected_device_display}'\n(Instance ID: {instance_id_to_restart})?"
        )

        if not response:
            self.status_label.config(text="STATUS: Restart cancelled by user.")
            return

        self.status_label.config(text=f"STATUS: Attempting to restart '{selected_device_display}'...", foreground="blue")
        self.root.update_idletasks()

        # Disable device
        disable_cmd = f"Disable-PnpDevice -InstanceId '{instance_id_to_restart}' -Confirm:$false"
        disable_output = run_powershell_command(disable_cmd)
        if disable_output is None:
            messagebox.showerror("Restart Failed", f"Failed to disable device:\n'{selected_device_display}'.\n"
                                                  "Check console for details. Ensure script is run as admin.")
            self.status_label.config(text="STATUS: Restart failed (disable).", foreground="red")
            return

        # Enable device
        enable_cmd = f"Enable-PnpDevice -InstanceId '{instance_id_to_restart}' -Confirm:$false"
        enable_output = run_powershell_command(enable_cmd)
        if enable_output is None:
            messagebox.showerror("Restart Failed", f"Failed to enable device:\n'{selected_device_display}'.\n"
                                                  "Check console for details.")
            self.status_label.config(text="STATUS: Restart failed (enable).", foreground="red")
            return

        messagebox.showinfo("Restart Successful", f"Successfully sent restart commands to:\n'{selected_device_display}'")
        self.status_label.config(text=f"STATUS: Successfully restarted '{selected_device_display}'.", foreground="green")
        # Re-search devices to update their status (e.g., if it changed)
        self.search_devices()

# --- Run the Application ---
if __name__ == "__main__":
    root = tk.Tk()
    app = UsbRestarterApp(root)
    root.mainloop()