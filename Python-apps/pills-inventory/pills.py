import os
import sys
import webbrowser
import subprocess
import configparser
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox

APP_VERSION = "0.2.01"
CONFIG_FILE = "medications.ini"
DATE_FORMAT = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "%m/%d/%Y"
GITHUB_URL = "https://github.com/LockMan007/PixelSwirl/tree/main/Python-apps/pills-inventory"

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        
        # Calculate popup offset using cursor coordinates
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Use a solid background frame to act as the border line
        border_frame = tk.Frame(tw, background="black", padx=1, pady=1)
        border_frame.pack()

        label = tk.Label(
            border_frame, 
            text=self.text, 
            justify=tk.LEFT,
            background="#ffffe0", 
            foreground="black",
            font=("Arial", 8, "normal")
        )
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class MedTrackerApp:
    def __init__(self, root):
        self.root = root
        self.config = configparser.ConfigParser()
        self.selected_section = None
        self.last_refresh_time = None

        self.load_config()
        self.process_daily_deductions()
        
        # Setup Window Size
        saved_geo = self.config.get("SYSTEM", "window_geometry", fallback="650x700")
        try:
            self.root.geometry(saved_geo)
        except tk.TclError:
            self.root.geometry("650x700")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_titlebar()

        # Build Menu
        self.create_menu()

        # Main Container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)

        # Collapsible Header Toggle
        self.is_panel_visible = True
        self.btn_toggle_panel = ttk.Button(
            main_container, 
            text="▲ Collapse Add / Update Section", 
            command=self.toggle_input_panel
        )
        self.btn_toggle_panel.pack(fill="x", padx=10, pady=(5, 0))

        # Input Frame (Add / Update Medication)
        self.input_frame = ttk.LabelFrame(main_container, text="Add / Update Medication", padding=10)
        self.input_frame.pack(fill="x", padx=10, pady=5)

        # Left Column - Standard Inputs
        left_col = ttk.Frame(self.input_frame)
        left_col.grid(row=0, column=0, sticky="nw", padx=(0, 15))

        ttk.Label(left_col, text="Person Name:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.entry_person = ttk.Entry(left_col, width=20)
        self.entry_person.grid(row=0, column=1, padx=2, pady=2)
        self.entry_person.bind("<KeyRelease>", self.on_input_change)

        ttk.Label(left_col, text="Pill Name:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self.entry_pill = ttk.Entry(left_col, width=20)
        self.entry_pill.grid(row=1, column=1, padx=2, pady=2)
        self.entry_pill.bind("<KeyRelease>", self.on_input_change)

        ttk.Label(left_col, text="Current Quantity:").grid(row=2, column=0, sticky="w", padx=2, pady=2)
        self.entry_quantity = ttk.Entry(left_col, width=20)
        self.entry_quantity.grid(row=2, column=1, padx=2, pady=2)

        ttk.Label(left_col, text="Daily Frequency:").grid(row=3, column=0, sticky="w", padx=2, pady=2)
        self.entry_daily = ttk.Entry(left_col, width=20)
        self.entry_daily.grid(row=3, column=1, padx=2, pady=2)

        # Left Action Buttons
        btn_box_left = ttk.Frame(left_col)
        btn_box_left.grid(row=4, column=0, columnspan=2, pady=(8, 0), sticky="w")

        self.btn_save = ttk.Button(btn_box_left, text="Save New Medication", command=self.save_medication)
        self.btn_save.pack(side="left", padx=(0, 4))

        self.btn_clear = ttk.Button(btn_box_left, text="Cancel / Clear Selection", command=self.reset_form)
        self.btn_clear.pack(side="left", padx=2)

        self.btn_delete = ttk.Button(btn_box_left, text="Delete", command=self.delete_medication, state="disabled")
        self.btn_delete.pack(side="left", padx=2)

        # Right Column - Quick Refill Controls
        right_col = ttk.LabelFrame(self.input_frame, text=" Quick Refill Controls ", padding=8)
        right_col.grid(row=0, column=1, sticky="nsew", padx=5)

        ttk.Label(right_col, text="Add Refill Amount:").grid(row=0, column=0, columnspan=2, sticky="w", padx=2, pady=(0, 2))
        self.entry_add_refill = ttk.Entry(right_col, width=8)
        self.entry_add_refill.grid(row=1, column=0, sticky="w", padx=(2, 4), pady=(0, 8))
        btn_refill_now = ttk.Button(right_col, text="Refill Now", command=self.execute_refill)
        btn_refill_now.grid(row=1, column=1, sticky="w", padx=0, pady=(0, 8))

        ttk.Label(right_col, text="Set Default Amount:").grid(row=2, column=0, columnspan=2, sticky="w", padx=2, pady=(0, 2))
        self.entry_default_refill = ttk.Entry(right_col, width=8)
        self.entry_default_refill.grid(row=3, column=0, sticky="w", padx=(2, 4), pady=0)
        btn_save_default = ttk.Button(right_col, text="Save Default", command=self.save_default_refill)
        btn_save_default.grid(row=3, column=1, sticky="w", padx=0, pady=0)

        # Interactive Daily Deduction Banner Indicator
        self.lbl_status = tk.Label(
            main_container, 
            text="", 
            fg="blue", 
            font=("Arial", 9, "bold"),
            cursor="hand2"
        )
        self.lbl_status.pack(pady=4)
        self.lbl_status.bind("<Button-1>", lambda e: self.reload_data_from_ini())
        ToolTip(self.lbl_status, "refresh data")

        # Scrollable Display Area
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")

        # Initial Load & Timer Activation
        self.reload_data_from_ini()
        self.schedule_hourly_auto_refresh()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open _ini_ File", command=self.open_ini_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # Added Refresh Menu Option
        menubar.add_command(label="Refresh", command=self.reload_data_from_ini)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="About", command=self.show_about_dialog)
        menubar.add_cascade(label="About", menu=about_menu)

        self.root.config(menu=menubar)

    def reload_data_from_ini(self):
        """Reloads medications.ini, updates timestamp, and renders dashboard."""
        self.last_refresh_time = datetime.now().strftime("%I:%M %p")
        self.load_config()
        self.process_daily_deductions()
        self.update_titlebar()
        self.update_status_label()
        self.render_dashboard()

    def update_status_label(self):
        today_str = date.today().strftime(DISPLAY_DATE_FORMAT)
        time_str = f" (Refreshed at {self.last_refresh_time})" if self.last_refresh_time else ""
        self.lbl_status.config(
            text=f"All of today's pills have been subtracted for {today_str}{time_str}"
        )

    def schedule_hourly_auto_refresh(self):
        """Schedules auto refresh every 3,600,000 milliseconds (1 hour)."""
        self.root.after(3600000, self.auto_refresh)

    def auto_refresh(self):
        self.reload_data_from_ini()
        self.schedule_hourly_auto_refresh()

    def toggle_input_panel(self):
        if self.is_panel_visible:
            self.input_frame.pack_forget()
            self.btn_toggle_panel.config(text="▼ Expand Add / Update Section")
            self.is_panel_visible = False
        else:
            self.input_frame.pack(fill="x", padx=10, pady=5, before=self.lbl_status)
            self.btn_toggle_panel.config(text="▲ Collapse Add / Update Section")
            self.is_panel_visible = True

    def open_ini_file(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config()
        
        if sys.platform == "win32":
            os.startfile(CONFIG_FILE)
        elif sys.platform == "darwin":
            subprocess.run(["open", CONFIG_FILE])
        else:
            subprocess.run(["xdg-open", CONFIG_FILE])

    def show_about_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("About Medication Stock Tracker")
        dlg.geometry("520x160")
        dlg.resizable(False, False)
        
        ttk.Label(dlg, text=f"Medication Stock Tracker v{APP_VERSION}", font=("Arial", 11, "bold")).pack(pady=(15, 5))
        ttk.Label(dlg, text="Repository / Source Code:").pack()

        link_lbl = tk.Label(dlg, text=GITHUB_URL, fg="blue", cursor="hand2", font=("Arial", 9, "underline"))
        link_lbl.pack(pady=5)
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open_new(GITHUB_URL))

        context_menu = tk.Menu(dlg, tearoff=0)
        context_menu.add_command(label="Copy URL to clipboard", command=lambda: self.copy_to_clipboard(GITHUB_URL))

        def popup(event):
            context_menu.tk_popup(event.x_root, event.y_root)

        link_lbl.bind("<Button-3>", popup)

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Clipboard", "URL copied to clipboard!")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
        
        if not self.config.has_section("SYSTEM"):
            self.config.add_section("SYSTEM")
            self.config.set("SYSTEM", "last_updated", date.today().strftime(DATE_FORMAT))
            self.save_config()

    def save_config(self):
        with open(CONFIG_FILE, "w") as configfile:
            self.config.write(configfile)

    def update_titlebar(self):
        last_updated_raw = self.config.get("SYSTEM", "last_updated", fallback=date.today().strftime(DATE_FORMAT))
        try:
            parsed_date = datetime.strptime(last_updated_raw, DATE_FORMAT).strftime(DISPLAY_DATE_FORMAT)
        except ValueError:
            parsed_date = last_updated_raw
            
        self.root.title(f"Medication Stock Tracker -- Version {APP_VERSION} -- {parsed_date}")

    def process_daily_deductions(self):
        last_date_str = self.config.get("SYSTEM", "last_updated", fallback=date.today().strftime(DATE_FORMAT))
        try:
            last_date = datetime.strptime(last_date_str, DATE_FORMAT).date()
        except ValueError:
            last_date = date.today()

        today = date.today()
        days_passed = (today - last_date).days

        if days_passed > 0:
            for section in self.config.sections():
                if section == "SYSTEM":
                    continue
                qty = int(self.config.get(section, "Quantity", fallback="0"))
                daily = int(self.config.get(section, "Daily", fallback="0"))
                
                new_qty = max(0, qty - (daily * days_passed))
                self.config.set(section, "Quantity", str(new_qty))

            self.config.set("SYSTEM", "last_updated", today.strftime(DATE_FORMAT))
            self.save_config()

    def on_input_change(self, event=None):
        if not self.selected_section:
            return
        
        current_p, current_m = self.selected_section.split(" - ", 1)
        entered_p = self.entry_person.get().strip()
        entered_m = self.entry_pill.get().strip()

        if entered_p != current_p or entered_m != current_m:
            self.btn_save.config(text="Save New Medication")
        else:
            self.btn_save.config(text="Update Medication")

    def select_medication(self, person, pill, qty, daily, default_refill):
        self.selected_section = f"{person} - {pill}"
        
        self.entry_person.delete(0, tk.END)
        self.entry_person.insert(0, person)

        self.entry_pill.delete(0, tk.END)
        self.entry_pill.insert(0, pill)

        self.entry_quantity.delete(0, tk.END)
        self.entry_quantity.insert(0, str(qty))

        self.entry_daily.delete(0, tk.END)
        self.entry_daily.insert(0, str(daily))

        self.entry_add_refill.delete(0, tk.END)
        self.entry_add_refill.insert(0, str(default_refill))

        self.entry_default_refill.delete(0, tk.END)
        self.entry_default_refill.insert(0, str(default_refill))

        self.btn_save.config(text="Update Medication")
        self.btn_delete.config(state="normal")

    def reset_form(self, keep_person=False):
        person_name = self.entry_person.get() if keep_person else ""
        self.selected_section = None
        
        self.entry_person.delete(0, tk.END)
        if keep_person:
            self.entry_person.insert(0, person_name)

        self.entry_pill.delete(0, tk.END)
        self.entry_quantity.delete(0, tk.END)
        self.entry_daily.delete(0, tk.END)
        self.entry_add_refill.delete(0, tk.END)
        self.entry_default_refill.delete(0, tk.END)

        self.btn_save.config(text="Save New Medication")
        self.btn_delete.config(state="disabled")

    def save_medication(self):
        person = self.entry_person.get().strip()
        pill = self.entry_pill.get().strip()
        qty = self.entry_quantity.get().strip()
        daily = self.entry_daily.get().strip()

        if not person or not pill or not qty.isdigit() or not daily.isdigit():
            messagebox.showerror("Error", "Please enter valid values. Quantity and Daily must be integers.")
            return

        new_section_name = f"{person} - {pill}"

        if self.selected_section and self.selected_section != new_section_name:
            def_ref = self.config.get(self.selected_section, "DefaultRefill", fallback="0")
            self.config.remove_section(self.selected_section)
            self.config.add_section(new_section_name)
            self.config.set(new_section_name, "DefaultRefill", def_ref)
        elif not self.config.has_section(new_section_name):
            self.config.add_section(new_section_name)

        self.config.set(new_section_name, "Quantity", qty)
        self.config.set(new_section_name, "Daily", daily)
        
        today_str = date.today().strftime(DATE_FORMAT)
        self.config.set("SYSTEM", "last_updated", today_str)

        self.save_config()
        self.update_titlebar()
        self.render_dashboard()
        self.reset_form(keep_person=True)

    def execute_refill(self):
        add_amount = self.entry_add_refill.get().strip()
        current_qty = self.entry_quantity.get().strip()

        if not add_amount.isdigit() or not current_qty.isdigit():
            messagebox.showerror("Error", "Enter valid numbers for current quantity and refill amount.")
            return

        new_total = int(current_qty) + int(add_amount)
        self.entry_quantity.delete(0, tk.END)
        self.entry_quantity.insert(0, str(new_total))
        self.save_medication()

    def save_default_refill(self):
        if not self.selected_section or not self.config.has_section(self.selected_section):
            messagebox.showwarning("Warning", "Select an existing medication from the list first.")
            return

        def_val = self.entry_default_refill.get().strip()
        if not def_val.isdigit():
            messagebox.showerror("Error", "Default Refill must be an integer.")
            return

        self.config.set(self.selected_section, "DefaultRefill", def_val)
        self.save_config()
        self.render_dashboard()
        messagebox.showinfo("Saved", f"Default refill amount of {def_val} saved for {self.selected_section}.")

    def delete_medication(self):
        if not self.selected_section or not self.config.has_section(self.selected_section):
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {self.selected_section}?")
        if confirm:
            self.config.remove_section(self.selected_section)
            self.save_config()
            self.render_dashboard()
            self.reset_form(keep_person=True)

    def render_dashboard(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        people = {}
        for section in self.config.sections():
            if section == "SYSTEM":
                continue

            try:
                person, pill = section.split(" - ", 1)
            except ValueError:
                continue

            if person not in people:
                people[person] = []

            qty = int(self.config.get(section, "Quantity", fallback="0"))
            daily = int(self.config.get(section, "Daily", fallback="1"))
            def_refill = int(self.config.get(section, "DefaultRefill", fallback="0"))
            days_left = qty // daily if daily > 0 else 0

            people[person].append({
                "pill": pill,
                "qty": qty,
                "daily": daily,
                "days_left": days_left,
                "default_refill": def_refill
            })

        if not people:
            ttk.Label(self.scroll_frame, text="No medications logged yet.", font=("Arial", 11, "italic")).pack(pady=20)
            return

        for person, meds in people.items():
            sorted_meds = sorted(meds, key=lambda item: item["days_left"])

            p_frame = ttk.LabelFrame(self.scroll_frame, text=f" Name: {person} ", padding=10)
            p_frame.pack(fill="x", expand=True, padx=5, pady=8)

            headers = ["Pill", "Days Remaining", "Quantity Remaining", "Taken Per Day"]
            for col_idx, text in enumerate(headers):
                lbl = ttk.Label(p_frame, text=text, font=("Arial", 9, "bold"))
                lbl.grid(row=0, column=col_idx, padx=10, pady=2, sticky="w")

            refill_needed = []

            for row_idx, med in enumerate(sorted_meds, start=1):
                lbl_pill = ttk.Label(p_frame, text=med["pill"], cursor="hand2")
                lbl_days = ttk.Label(p_frame, text=f"{med['days_left']} Days remaining", cursor="hand2")
                lbl_qty = ttk.Label(p_frame, text=f"{med['qty']} pills", cursor="hand2")
                lbl_daily = ttk.Label(p_frame, text=f"{med['daily']} per day")

                lbl_pill.grid(row=row_idx, column=0, padx=10, pady=2, sticky="w")
                lbl_days.grid(row=row_idx, column=1, padx=10, pady=2, sticky="w")
                lbl_qty.grid(row=row_idx, column=2, padx=10, pady=2, sticky="w")
                lbl_daily.grid(row=row_idx, column=3, padx=10, pady=2, sticky="w")

                for widget in (lbl_pill, lbl_days, lbl_qty):
                    widget.bind("<Button-1>", lambda e, p=person, m=med: self.select_medication(
                        p, m["pill"], m["qty"], m["daily"], m["default_refill"]
                    ))

                if med["days_left"] <= 7:
                    refill_needed.append(med["pill"])

            refill_text = f"[NEED REFILL ON: {', '.join(refill_needed)}]" if refill_needed else "[NEED REFILL ON: none]"
            alert_color = "red" if refill_needed else "green"
            
            refill_lbl = tk.Label(p_frame, text=refill_text, fg=alert_color, font=("Arial", 10, "bold"))
            refill_lbl.grid(row=len(sorted_meds) + 1, column=0, columnspan=4, pady=(8, 2), sticky="w")

    def on_close(self):
        current_geo = self.root.geometry()
        self.config.set("SYSTEM", "window_geometry", current_geo)
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MedTrackerApp(root)
    root.mainloop()