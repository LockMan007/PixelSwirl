import os
import sys
import re
import webbrowser
import subprocess
import configparser
from datetime import datetime, date, time, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

APP_VERSION = "0.3.3"
CONFIG_FILE = "medications.ini"
SETTINGS_FILE = "settings.ini"
DATE_FORMAT = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "%m/%d/%Y"
GITHUB_URL = "https://github.com/LockMan007/PixelSwirl/tree/main/Python-apps/pills-inventory"

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_time_string(val_str):
    """
    Parses flexible user inputs like '8am', '8:00 AM', '9pm', '21:00', '9:30p', '0', 'closed'.
    Returns datetime.time object or None if closed/invalid.
    """
    s = val_str.strip().lower()
    if not s or s in ("0", "closed", "none", "off", "-"):
        return None

    # Match numbers + optional colon + optional am/pm
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m?\.?)?$", s)
    if not match:
        return None

    hr = int(match.group(1))
    mn = int(match.group(2)) if match.group(2) else 0
    ampm = match.group(3)

    if ampm:
        is_pm = 'p' in ampm
        if is_pm and hr < 12:
            hr += 12
        elif not is_pm and hr == 12:
            hr = 0
    elif hr < 7:  # Heuristic: single numbers like 1..6 default to PM for closing hours
        hr += 12

    try:
        return time(hr, mn)
    except ValueError:
        return None


def censor_text(text):
    """Censors strings so 'SusanTheLady' becomes 'S***' and 'VitaminC' becomes 'V***'."""
    if not text:
        return text
    return text[0] + "***"


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
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
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
        self.settings_config = configparser.ConfigParser()
        self.selected_section = None
        self.last_refresh_time = None
        self.include_days_left_var = tk.BooleanVar(value=False)
        self.include_phone_var = tk.BooleanVar(value=False)
        self.refill_type_var = tk.StringVar(value="NUMERIC")

        # Element Visibility Settings Variables
        self.show_name_var = tk.BooleanVar(value=True)
        self.show_pill_var = tk.BooleanVar(value=True)
        self.show_days_remaining_var = tk.BooleanVar(value=True)
        self.show_quantity_remaining_var = tk.BooleanVar(value=True)
        self.show_taken_per_day_var = tk.BooleanVar(value=True)
        self.show_refills_left_var = tk.BooleanVar(value=True)

        # Censoring Options Variables
        self.censor_username_var = tk.BooleanVar(value=False)
        self.censor_medication_var = tk.BooleanVar(value=False)

        self.day_entries = {}

        self.load_settings()
        self.load_config()
        self.process_daily_deductions()
        
        saved_geo = self.settings_config.get("SYSTEM", "window_geometry", fallback="980x780")
        try:
            self.root.geometry(saved_geo)
        except tk.TclError:
            self.root.geometry("980x780")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_titlebar()

        self.create_menu()

        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)

        # Toggle Button
        self.is_panel_visible = True
        self.btn_toggle_panel = ttk.Button(
            main_container, 
            text="▲ Collapse Add / Update Section", 
            command=self.toggle_input_panel
        )
        self.btn_toggle_panel.pack(fill="x", padx=10, pady=(5, 0))

        # Main Input Panel (Collapsible Container)
        self.input_frame = ttk.Frame(main_container, padding=5)
        self.input_frame.pack(fill="x", padx=10, pady=5)

        # Left Sub-Frame: Add/Update Medication + Refill Controls
        left_main_box = ttk.LabelFrame(self.input_frame, text=" Add / Update Medication ", padding=8)
        left_main_box.pack(side="left", fill="both", expand=True, padx=(0, 5))

        left_col = ttk.Frame(left_main_box)
        left_col.grid(row=0, column=0, sticky="nw", padx=(0, 15))

        ttk.Label(left_col, text="Person Name:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.entry_person = ttk.Entry(left_col, width=18)
        self.entry_person.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        self.entry_person.bind("<KeyRelease>", self.on_input_change)

        ttk.Label(left_col, text="Pill Name:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self.entry_pill = ttk.Entry(left_col, width=18)
        self.entry_pill.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        self.entry_pill.bind("<KeyRelease>", self.on_input_change)

        ttk.Label(left_col, text="Current Quantity:").grid(row=2, column=0, sticky="w", padx=2, pady=2)
        self.entry_quantity = ttk.Entry(left_col, width=18)
        self.entry_quantity.grid(row=2, column=1, sticky="w", padx=2, pady=2)

        ttk.Label(left_col, text="Daily Frequency:").grid(row=3, column=0, sticky="w", padx=2, pady=2)
        self.entry_daily = ttk.Entry(left_col, width=18)
        self.entry_daily.grid(row=3, column=1, sticky="w", padx=2, pady=2)

        ttk.Label(left_col, text="Refills Left:").grid(row=4, column=0, sticky="w", padx=2, pady=2)
        
        refills_container = ttk.Frame(left_col)
        refills_container.grid(row=4, column=1, sticky="w", padx=2, pady=2)

        self.radio_num = ttk.Radiobutton(
            refills_container, variable=self.refill_type_var, value="NUMERIC", command=self.toggle_refill_mode
        )
        self.radio_num.pack(side="left", padx=(0, 2))

        self.entry_refills_left = ttk.Entry(refills_container, width=8)
        self.entry_refills_left.pack(side="left", padx=(0, 4))

        self.radio_otc = ttk.Radiobutton(
            refills_container, text="OTC", variable=self.refill_type_var, value="OTC", command=self.toggle_refill_mode
        )
        self.radio_otc.pack(side="left", padx=(0, 4))

        self.radio_unk = ttk.Radiobutton(
            refills_container, text="???", variable=self.refill_type_var, value="???", command=self.toggle_refill_mode
        )
        self.radio_unk.pack(side="left")

        btn_box_left = ttk.Frame(left_col)
        btn_box_left.grid(row=5, column=0, columnspan=2, pady=(8, 0), sticky="w")

        self.btn_save = ttk.Button(btn_box_left, text="Save New Medication", command=self.save_medication)
        self.btn_save.pack(side="left", padx=(0, 4))

        self.btn_clear = ttk.Button(btn_box_left, text="Cancel / Reset Selection", command=self.reset_form)
        self.btn_clear.pack(side="left", padx=2)

        self.btn_delete = ttk.Button(btn_box_left, text="Delete", command=self.delete_medication, state="disabled")
        self.btn_delete.pack(side="left", padx=2)

        # Refill Controls Frame
        right_col = ttk.LabelFrame(left_main_box, text=" Refill Controls ", padding=6)
        right_col.grid(row=0, column=1, sticky="nw", padx=(0, 10))

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

        # Right Sub-Frame: Pharmacy Hours & Settings
        pharmacy_box = ttk.LabelFrame(self.input_frame, text=" Pharmacy Hours ", padding=6)
        pharmacy_box.pack(side="right", fill="y", anchor="n")

        # Grid for Mon-Sun
        ttk.Label(pharmacy_box, text="Open", font=("Arial", 8, "bold")).grid(row=0, column=1, padx=2)
        ttk.Label(pharmacy_box, text="Close", font=("Arial", 8, "bold")).grid(row=0, column=2, padx=2)

        for idx, day in enumerate(DAYS, start=1):
            ttk.Label(pharmacy_box, text=f"{day}:").grid(row=idx, column=0, sticky="e", padx=2, pady=1)
            e_open = ttk.Entry(pharmacy_box, width=7)
            e_open.grid(row=idx, column=1, padx=2, pady=1)
            e_close = ttk.Entry(pharmacy_box, width=7)
            e_close.grid(row=idx, column=2, padx=2, pady=1)
            self.day_entries[day] = (e_open, e_close)

        # Quick Copy & Save Controls
        copy_box = ttk.Frame(pharmacy_box)
        copy_box.grid(row=8, column=0, columnspan=3, pady=(3, 3))

        btn_copy_wk = ttk.Button(copy_box, text="Mon→Wkdays", command=self.copy_mon_to_weekdays)
        btn_copy_wk.pack(side="left", padx=1)
        ToolTip(btn_copy_wk, "Copy Monday hours to Tue-Fri")

        btn_copy_all = ttk.Button(copy_box, text="Mon→All", command=self.copy_mon_to_all)
        btn_copy_all.pack(side="left", padx=1)
        ToolTip(btn_copy_all, "Copy Monday hours to all days")

        btn_save_pharmacy = ttk.Button(pharmacy_box, text="Save Pharmacy", command=self.save_pharmacy_data)
        btn_save_pharmacy.grid(row=9, column=0, columnspan=3, sticky="ew", padx=2, pady=(2, 4))

        # Phone Number Entry
        phone_frame = ttk.Frame(pharmacy_box)
        phone_frame.grid(row=10, column=0, columnspan=3, sticky="w", pady=(2, 0))
        
        ttk.Label(phone_frame, text="Phone:").pack(side="left", padx=(0, 2))
        self.entry_phone = ttk.Entry(phone_frame, width=16)
        self.entry_phone.pack(side="left")

        # Status Label
        self.lbl_status = tk.Label(
            main_container, 
            text="", 
            fg="blue", 
            font=("Arial", 9, "bold"),
            cursor="hand2",
            anchor="w"
        )
        self.lbl_status.pack(fill="x", padx=10, pady=4)
        self.lbl_status.bind("<Button-1>", lambda e: self.reload_data_from_ini())
        ToolTip(self.lbl_status, "refresh data")

        # Dashboard View Area
        dashboard_view = ttk.Frame(main_container)
        dashboard_view.pack(fill="both", expand=True, padx=10, pady=5)

        # Left Side: Cards
        canvas_container = ttk.Frame(dashboard_view)
        canvas_container.pack(side="left", fill="both", expand=True)

        canvas = tk.Canvas(canvas_container)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Right Side: Pharmacy Status + Text Generator
        right_panel = ttk.Frame(dashboard_view, padding=(10, 0, 0, 0))
        right_panel.pack(side="right", fill="y", anchor="n")

        # Pharmacy Closing Countdown Widget
        ttk.Label(right_panel, text="Pharmacy Closes in:", font=("Arial", 9, "bold")).pack(anchor="w")
        
        self.lbl_closing_time = tk.Label(right_panel, text="Closed", font=("Arial", 9, "normal"), fg="black", anchor="w")
        self.lbl_closing_time.pack(anchor="w", pady=(0, 4))

        self.lbl_phone_display = ttk.Label(right_panel, text="", font=("Arial", 9))
        self.lbl_phone_display.pack(anchor="w", pady=(0, 2))

        chk_phone = ttk.Checkbutton(
            right_panel, 
            text="Include phone in message", 
            variable=self.include_phone_var,
            command=self.on_setting_changed
        )
        chk_phone.pack(anchor="w", pady=(0, 10))

        ttk.Separator(right_panel, orient="horizontal").pack(fill="x", pady=5)

        ttk.Label(right_panel, text="Text Message Generator:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 2))
        
        self.txt_global_message = tk.Text(right_panel, width=32, height=12, font=("Arial", 9), wrap="word")
        self.txt_global_message.pack(fill="both", expand=True)

        chk_days = ttk.Checkbutton(
            right_panel, 
            text="Include days left in text message generator", 
            variable=self.include_days_left_var,
            command=self.on_setting_changed
        )
        chk_days.pack(anchor="w", pady=(5, 0))

        self.load_pharmacy_fields()
        self.reload_data_from_ini()
        self.schedule_hourly_auto_refresh()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            self.settings_config.read(SETTINGS_FILE)

        if not self.settings_config.has_section("VISIBILITY"):
            self.settings_config.add_section("VISIBILITY")
        if not self.settings_config.has_section("CENSORING"):
            self.settings_config.add_section("CENSORING")
        if not self.settings_config.has_section("GENERATOR"):
            self.settings_config.add_section("GENERATOR")
        if not self.settings_config.has_section("SYSTEM"):
            self.settings_config.add_section("SYSTEM")

        self.show_name_var.set(self.settings_config.getboolean("VISIBILITY", "show_name", fallback=True))
        self.show_pill_var.set(self.settings_config.getboolean("VISIBILITY", "show_pill", fallback=True))
        self.show_days_remaining_var.set(self.settings_config.getboolean("VISIBILITY", "show_days_remaining", fallback=True))
        self.show_quantity_remaining_var.set(self.settings_config.getboolean("VISIBILITY", "show_quantity_remaining", fallback=True))
        self.show_taken_per_day_var.set(self.settings_config.getboolean("VISIBILITY", "show_taken_per_day", fallback=True))
        self.show_refills_left_var.set(self.settings_config.getboolean("VISIBILITY", "show_refills_left", fallback=True))

        self.censor_username_var.set(self.settings_config.getboolean("CENSORING", "censor_username", fallback=False))
        self.censor_medication_var.set(self.settings_config.getboolean("CENSORING", "censor_medication", fallback=False))

        self.include_days_left_var.set(self.settings_config.getboolean("GENERATOR", "include_days_left", fallback=False))
        self.include_phone_var.set(self.settings_config.getboolean("GENERATOR", "include_phone", fallback=False))

    def save_settings(self):
        self.settings_config.set("VISIBILITY", "show_name", str(self.show_name_var.get()))
        self.settings_config.set("VISIBILITY", "show_pill", str(self.show_pill_var.get()))
        self.settings_config.set("VISIBILITY", "show_days_remaining", str(self.show_days_remaining_var.get()))
        self.settings_config.set("VISIBILITY", "show_quantity_remaining", str(self.show_quantity_remaining_var.get()))
        self.settings_config.set("VISIBILITY", "show_taken_per_day", str(self.show_taken_per_day_var.get()))
        self.settings_config.set("VISIBILITY", "show_refills_left", str(self.show_refills_left_var.get()))

        self.settings_config.set("CENSORING", "censor_username", str(self.censor_username_var.get()))
        self.settings_config.set("CENSORING", "censor_medication", str(self.censor_medication_var.get()))

        self.settings_config.set("GENERATOR", "include_days_left", str(self.include_days_left_var.get()))
        self.settings_config.set("GENERATOR", "include_phone", str(self.include_phone_var.get()))

        current_geo = self.root.geometry()
        self.settings_config.set("SYSTEM", "window_geometry", current_geo)

        with open(SETTINGS_FILE, "w") as f:
            self.settings_config.write(f)

    def on_setting_changed(self):
        self.save_settings()
        self.render_dashboard()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save All", command=self.save_all)
        file_menu.add_command(label="Open _ini_ File", command=self.open_ini_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        
        show_hide_menu = tk.Menu(settings_menu, tearoff=0)
        show_hide_menu.add_checkbutton(label="Name", variable=self.show_name_var, command=self.on_setting_changed)
        show_hide_menu.add_checkbutton(label="Pill", variable=self.show_pill_var, command=self.on_setting_changed)
        show_hide_menu.add_checkbutton(label="Days Remaining", variable=self.show_days_remaining_var, command=self.on_setting_changed)
        show_hide_menu.add_checkbutton(label="Quantity Remaining", variable=self.show_quantity_remaining_var, command=self.on_setting_changed)
        show_hide_menu.add_checkbutton(label="Taken Per Day", variable=self.show_taken_per_day_var, command=self.on_setting_changed)
        show_hide_menu.add_checkbutton(label="Refills Left", variable=self.show_refills_left_var, command=self.on_setting_changed)
        
        settings_menu.add_cascade(label="Show / Hide Elements", menu=show_hide_menu)
        settings_menu.add_separator()
        settings_menu.add_checkbutton(label="Censor Username", variable=self.censor_username_var, command=self.on_setting_changed)
        settings_menu.add_checkbutton(label="Censor Medication", variable=self.censor_medication_var, command=self.on_setting_changed)

        menubar.add_cascade(label="Settings", menu=settings_menu)

        menubar.add_command(label="Refresh", command=self.reload_data_from_ini)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="About", command=self.show_about_dialog)
        menubar.add_cascade(label="About", menu=about_menu)

        self.root.config(menu=menubar)

    def save_all(self):
        # Save Pharmacy fields actively typed into UI to config
        if not self.config.has_section("PHARMACY"):
            self.config.add_section("PHARMACY")

        for day in DAYS:
            self.config.set("PHARMACY", f"{day}_open", self.day_entries[day][0].get().strip())
            self.config.set("PHARMACY", f"{day}_close", self.day_entries[day][1].get().strip())

        self.config.set("PHARMACY", "phone", self.entry_phone.get().strip())

        # Write out configuration files
        self.save_config()
        self.save_settings()

        msg = (
            "All data has been saved successfully!\n\n"
            "Saved Groups & Target Files:\n"
            "• Medication Info -> medications.ini\n"
            "• Pharmacy Info -> medications.ini\n"
            "• Visibility Settings -> settings.ini\n"
            "• Censoring Settings -> settings.ini\n"
            "• Text Generator Settings -> settings.ini\n"
            "• System Preferences & Layout -> settings.ini"
        )
        messagebox.showinfo("Save All Complete", msg)

    def log_manual_change(self, entry_str):
        year = date.today().strftime("%Y")
        log_filename = f"Log-{year}.txt"
        timestamp = datetime.now().strftime("%m/%d/%Y %I:%M %p")
        with open(log_filename, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {entry_str}\n")

    def log_refill_action(self, person, pill, refill_amount, refills_left):
        year = date.today().strftime("%Y")
        refill_filename = f"Refills-{year}.txt"
        file_exists = os.path.exists(refill_filename)
        
        today_str = date.today().strftime(DISPLAY_DATE_FORMAT)
        log_line = f"{today_str} - {person}, {pill}, {refill_amount}, {refills_left}\n"
        
        with open(refill_filename, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("Refills were added on these dates\n")
            f.write(log_line)

    def toggle_refill_mode(self):
        if self.refill_type_var.get() == "NUMERIC":
            self.entry_refills_left.config(state="normal")
            self.entry_refills_left.focus_set()
        else:
            self.entry_refills_left.config(state="disabled")

    def copy_mon_to_weekdays(self):
        mon_open = self.day_entries["Mon"][0].get()
        mon_close = self.day_entries["Mon"][1].get()
        for day in ["Tue", "Wed", "Thu", "Fri"]:
            self.day_entries[day][0].delete(0, tk.END)
            self.day_entries[day][0].insert(0, mon_open)
            self.day_entries[day][1].delete(0, tk.END)
            self.day_entries[day][1].insert(0, mon_close)

    def copy_mon_to_all(self):
        mon_open = self.day_entries["Mon"][0].get()
        mon_close = self.day_entries["Mon"][1].get()
        for day in DAYS[1:]:
            self.day_entries[day][0].delete(0, tk.END)
            self.day_entries[day][0].insert(0, mon_open)
            self.day_entries[day][1].delete(0, tk.END)
            self.day_entries[day][1].insert(0, mon_close)

    def load_pharmacy_fields(self):
        if not self.config.has_section("PHARMACY"):
            return
        
        for day in DAYS:
            o_val = self.config.get("PHARMACY", f"{day}_open", fallback="")
            c_val = self.config.get("PHARMACY", f"{day}_close", fallback="")
            
            self.day_entries[day][0].delete(0, tk.END)
            self.day_entries[day][0].insert(0, o_val)
            
            self.day_entries[day][1].delete(0, tk.END)
            self.day_entries[day][1].insert(0, c_val)

        phone_val = self.config.get("PHARMACY", "phone", fallback="")
        self.entry_phone.delete(0, tk.END)
        self.entry_phone.insert(0, phone_val)

    def save_pharmacy_data(self):
        if not self.config.has_section("PHARMACY"):
            self.config.add_section("PHARMACY")

        for day in DAYS:
            self.config.set("PHARMACY", f"{day}_open", self.day_entries[day][0].get().strip())
            self.config.set("PHARMACY", f"{day}_close", self.day_entries[day][1].get().strip())

        self.config.set("PHARMACY", "phone", self.entry_phone.get().strip())
        self.save_config()
        self.render_dashboard()
        self.log_manual_change("Updated Pharmacy hours / phone details.")
        messagebox.showinfo("Saved", "Pharmacy hours and phone number updated successfully.")

    def update_pharmacy_closing_widget(self):
        if not self.config.has_section("PHARMACY"):
            self.lbl_closing_time.config(text="Hours not set", fg="black")
            return

        phone_str = self.config.get("PHARMACY", "phone", fallback="")
        self.lbl_phone_display.config(text=phone_str if phone_str else "")

        today_name = DAYS[date.today().weekday()]
        close_str = self.config.get("PHARMACY", f"{today_name}_close", fallback="")
        open_str = self.config.get("PHARMACY", f"{today_name}_open", fallback="")

        close_time = parse_time_string(close_str)
        open_time = parse_time_string(open_str)

        if not close_time or not open_time:
            self.lbl_closing_time.config(text="Closed Today", fg="black", font=("Arial", 9, "normal"))
            return

        now = datetime.now()
        dt_close = datetime.combine(now.date(), close_time)
        dt_open = datetime.combine(now.date(), open_time)

        if now < dt_open:
            self.lbl_closing_time.config(text=f"Opens at {dt_open.strftime('%I:%M %p')}", fg="black", font=("Arial", 9, "normal"))
        elif now > dt_close:
            self.lbl_closing_time.config(text="Closed for the day", fg="red", font=("Arial", 9, "bold"))
        else:
            diff = dt_close - now
            seconds = int(diff.total_seconds())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60

            time_text = f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
            
            # Red text if 1 hour or less remaining
            if seconds <= 3600:
                self.lbl_closing_time.config(text=time_text, fg="red", font=("Arial", 9, "bold"))
            else:
                self.lbl_closing_time.config(text=time_text, fg="black", font=("Arial", 9, "normal"))

    def reload_data_from_ini(self):
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
                if section in ("SYSTEM", "PHARMACY"):
                    continue
                qty = int(self.config.get(section, "Quantity", fallback="0"))
                daily = int(self.config.get(section, "Daily", fallback="0"))
                
                new_qty = qty - (daily * days_passed)
                self.config.set(section, "Quantity", str(new_qty))

            self.config.set("SYSTEM", "last_updated", today.strftime(DATE_FORMAT))
            self.save_config()

    def is_valid_int(self, value):
        try:
            int(value)
            return True
        except ValueError:
            return False

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

    def select_medication(self, person, pill, qty, daily, default_refill, refills_left):
        self.selected_section = f"{person} - {pill}"
        
        self.entry_person.delete(0, tk.END)
        self.entry_person.insert(0, person)

        self.entry_pill.delete(0, tk.END)
        self.entry_pill.insert(0, pill)

        self.entry_quantity.delete(0, tk.END)
        self.entry_quantity.insert(0, str(qty))

        self.entry_daily.delete(0, tk.END)
        self.entry_daily.insert(0, str(daily))

        refills_str = str(refills_left).strip()
        if refills_str in ("OTC", "???"):
            self.refill_type_var.set(refills_str)
            self.entry_refills_left.delete(0, tk.END)
            self.entry_refills_left.config(state="disabled")
        else:
            self.refill_type_var.set("NUMERIC")
            self.entry_refills_left.config(state="normal")
            self.entry_refills_left.delete(0, tk.END)
            self.entry_refills_left.insert(0, refills_str)

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
        
        self.refill_type_var.set("NUMERIC")
        self.entry_refills_left.config(state="normal")
        self.entry_refills_left.delete(0, tk.END)

        self.entry_add_refill.delete(0, tk.END)
        self.entry_default_refill.delete(0, tk.END)

        self.btn_save.config(text="Save New Medication")
        self.btn_delete.config(state="disabled")

    def get_selected_refills_value(self):
        mode = self.refill_type_var.get()
        if mode == "OTC":
            return "OTC"
        elif mode == "???":
            return "???"
        else:
            val = self.entry_refills_left.get().strip()
            return val if self.is_valid_int(val) else None

    def save_medication(self):
        person = self.entry_person.get().strip()
        pill = self.entry_pill.get().strip()
        qty = self.entry_quantity.get().strip()
        daily = self.entry_daily.get().strip()
        refills_left = self.get_selected_refills_value()

        if not person or not pill or not self.is_valid_int(qty) or not self.is_valid_int(daily) or refills_left is None:
            messagebox.showerror("Error", "Please enter valid integers for Quantity, Daily, and Refills Left.")
            return

        new_section_name = f"{person} - {pill}"
        is_update = False

        if self.selected_section and self.selected_section != new_section_name:
            def_ref = self.config.get(self.selected_section, "DefaultRefill", fallback="0")
            self.config.remove_section(self.selected_section)
            self.config.add_section(new_section_name)
            self.config.set(new_section_name, "DefaultRefill", def_ref)
            is_update = True
        elif self.config.has_section(new_section_name):
            is_update = True
        else:
            self.config.add_section(new_section_name)

        self.config.set(new_section_name, "Quantity", qty)
        self.config.set(new_section_name, "Daily", daily)
        self.config.set(new_section_name, "RefillsLeft", refills_left)
        
        today_str = date.today().strftime(DATE_FORMAT)
        self.config.set("SYSTEM", "last_updated", today_str)

        self.save_config()
        
        # Logging manual modification
        action = "Updated" if is_update else "Added new"
        self.log_manual_change(f"{action} medication: {person} - {pill} (Qty: {qty}, Daily: {daily}, Refills Left: {refills_left})")

        self.update_titlebar()
        self.render_dashboard()
        self.reset_form(keep_person=True)

    def execute_refill(self):
        add_amount = self.entry_add_refill.get().strip()
        current_qty = self.entry_quantity.get().strip()
        person = self.entry_person.get().strip()
        pill = self.entry_pill.get().strip()

        if not self.is_valid_int(add_amount) or not self.is_valid_int(current_qty):
            messagebox.showerror("Error", "Enter valid integers for current quantity and refill amount.")
            return

        new_total = int(current_qty) + int(add_amount)
        self.entry_quantity.delete(0, tk.END)
        self.entry_quantity.insert(0, str(new_total))

        refills_val = self.get_selected_refills_value()
        if refills_val and self.is_valid_int(refills_val):
            updated_refills = max(0, int(refills_val) - 1)
            self.entry_refills_left.delete(0, tk.END)
            self.entry_refills_left.insert(0, str(updated_refills))
            refill_log_val = str(updated_refills)
        else:
            refill_log_val = refills_val if refills_val else "0"

        # Log to Refills-YEAR.txt
        self.log_refill_action(person, pill, add_amount, refill_log_val)

        self.save_medication()

    def save_default_refill(self):
        if not self.selected_section or not self.config.has_section(self.selected_section):
            messagebox.showwarning("Warning", "Select an existing medication from the list first.")
            return

        def_val = self.entry_default_refill.get().strip()
        if not self.is_valid_int(def_val):
            messagebox.showerror("Error", "Default Refill must be an integer.")
            return

        self.config.set(self.selected_section, "DefaultRefill", def_val)
        self.save_config()
        
        self.log_manual_change(f"Set default refill for {self.selected_section} to {def_val}.")
        
        self.render_dashboard()
        messagebox.showinfo("Saved", f"Default refill amount of {def_val} saved for {self.selected_section}.")

    def delete_medication(self):
        if not self.selected_section or not self.config.has_section(self.selected_section):
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {self.selected_section}?")
        if confirm:
            deleted_name = self.selected_section
            self.config.remove_section(self.selected_section)
            self.save_config()
            
            self.log_manual_change(f"Deleted medication section: {deleted_name}")
            
            self.render_dashboard()
            self.reset_form(keep_person=True)

    def format_refill_message(self, person, needed_meds):
        if not needed_meds:
            return ""

        show_days = self.include_days_left_var.get()
        med_strings = []
        
        disp_person = censor_text(person) if self.censor_username_var.get() else person

        for m in needed_meds:
            disp_pill = censor_text(m["pill"]) if self.censor_medication_var.get() else m["pill"]
            suffix = f" ({m['days_left']} days left)" if show_days else ""
            med_strings.append(f'"{disp_pill}"{suffix}')

        if len(med_strings) == 1:
            msg = f'{disp_person} needs to call in refills on {med_strings[0]}.'
        elif len(med_strings) == 2:
            msg = f'{disp_person} needs to call in refills for {med_strings[0]} and {med_strings[1]}.'
        else:
            formatted_list = ", ".join(med_strings[:-1]) + f', and {med_strings[-1]}'
            msg = f'{disp_person} needs to call in refills for {formatted_list}.'

        return msg

    def render_dashboard(self):
        self.update_pharmacy_closing_widget()

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        people = {}
        for section in self.config.sections():
            if section in ("SYSTEM", "PHARMACY"):
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
            refills_left = self.config.get(section, "RefillsLeft", fallback="0").strip()
            days_left = qty // daily if daily > 0 else 0

            people[person].append({
                "pill": pill,
                "qty": qty,
                "daily": daily,
                "days_left": days_left,
                "default_refill": def_refill,
                "refills_left": refills_left
            })

        if not people:
            ttk.Label(self.scroll_frame, text="No medications logged yet.", font=("Arial", 11, "italic")).pack(pady=20)
            self.txt_global_message.delete("1.0", tk.END)
            return

        all_messages = []

        for person, meds in people.items():
            sorted_meds = sorted(meds, key=lambda item: item["days_left"])

            display_person = censor_text(person) if self.censor_username_var.get() else person
            card_title = f" Name: {display_person} " if self.show_name_var.get() else ""

            p_frame = ttk.LabelFrame(self.scroll_frame, text=card_title, padding=10)
            p_frame.pack(fill="x", expand=True, padx=5, pady=8)

            # Build Grid Headers based on settings visibility
            headers_map = [
                ("Pill", self.show_pill_var.get()),
                ("Days Remaining", self.show_days_remaining_var.get()),
                ("Quantity Remaining", self.show_quantity_remaining_var.get()),
                ("Taken Per Day", self.show_taken_per_day_var.get()),
                ("Refills Left", self.show_refills_left_var.get()),
            ]

            active_col_index = 0
            col_mapping = {}

            for original_idx, (header_text, is_visible) in enumerate(headers_map):
                if is_visible:
                    lbl = ttk.Label(p_frame, text=header_text, font=("Arial", 9, "bold"))
                    lbl.grid(row=0, column=active_col_index, padx=6, pady=2, sticky="w")
                    col_mapping[original_idx] = active_col_index
                    active_col_index += 1

            refill_needed = []

            for row_idx, med in enumerate(sorted_meds, start=1):
                display_pill = censor_text(med["pill"]) if self.censor_medication_var.get() else med["pill"]

                is_low_stock = med["days_left"] <= 7
                qty_fg = "red" if is_low_stock else "black"
                qty_font = ("Arial", 9, "bold") if is_low_stock else ("Arial", 9, "normal")

                r_val = med["refills_left"]
                if r_val == "OTC":
                    refill_text_str = "OTC"
                    refill_fg = "black"
                    refill_font = ("Arial", 9, "normal")
                elif r_val == "???":
                    refill_text_str = "???"
                    refill_fg = "red"
                    refill_font = ("Arial", 9, "bold")
                else:
                    refill_text_str = f"{r_val} left"
                    has_no_refills = (r_val == "0")
                    refill_fg = "red" if has_no_refills else "black"
                    refill_font = ("Arial", 9, "bold") if has_no_refills else ("Arial", 9, "normal")

                # Column 0: Pill
                if self.show_pill_var.get():
                    lbl_pill = ttk.Label(p_frame, text=display_pill, cursor="hand2")
                    lbl_pill.grid(row=row_idx, column=col_mapping[0], padx=6, pady=2, sticky="w")
                    lbl_pill.bind("<Button-1>", lambda e, p=person, m=med: self.select_medication(
                        p, m["pill"], m["qty"], m["daily"], m["default_refill"], m["refills_left"]
                    ))

                # Column 1: Days Remaining
                if self.show_days_remaining_var.get():
                    lbl_days = ttk.Label(p_frame, text=f"{med['days_left']} Days remaining", cursor="hand2")
                    lbl_days.grid(row=row_idx, column=col_mapping[1], padx=6, pady=2, sticky="w")
                    lbl_days.bind("<Button-1>", lambda e, p=person, m=med: self.select_medication(
                        p, m["pill"], m["qty"], m["daily"], m["default_refill"], m["refills_left"]
                    ))

                # Column 2: Quantity Remaining
                if self.show_quantity_remaining_var.get():
                    lbl_qty = tk.Label(
                        p_frame, 
                        text=f"{med['qty']} pills", 
                        fg=qty_fg, 
                        font=qty_font, 
                        cursor="hand2"
                    )
                    lbl_qty.grid(row=row_idx, column=col_mapping[2], padx=6, pady=2, sticky="w")
                    lbl_qty.bind("<Button-1>", lambda e, p=person, m=med: self.select_medication(
                        p, m["pill"], m["qty"], m["daily"], m["default_refill"], m["refills_left"]
                    ))

                # Column 3: Taken Per Day
                if self.show_taken_per_day_var.get():
                    lbl_daily = ttk.Label(p_frame, text=f"{med['daily']} per day")
                    lbl_daily.grid(row=row_idx, column=col_mapping[3], padx=6, pady=2, sticky="w")

                # Column 4: Refills Left
                if self.show_refills_left_var.get():
                    lbl_refills = tk.Label(
                        p_frame, 
                        text=refill_text_str,
                        fg=refill_fg,
                        font=refill_font
                    )
                    lbl_refills.grid(row=row_idx, column=col_mapping[4], padx=6, pady=2, sticky="w")

                if is_low_stock:
                    refill_needed.append(med)

            refill_names = [
                censor_text(m["pill"]) if self.censor_medication_var.get() else m["pill"] 
                for m in refill_needed
            ]
            refill_text = f"[NEED REFILL ON: {', '.join(refill_names)}]" if refill_names else "[NEED REFILL ON: none]"
            alert_color = "red" if refill_names else "green"
            
            refill_lbl = tk.Label(p_frame, text=refill_text, fg=alert_color, font=("Arial", 9, "bold"))
            refill_lbl.grid(row=len(sorted_meds) + 1, column=0, columnspan=max(1, active_col_index), pady=(8, 2), sticky="w")

            person_msg = self.format_refill_message(person, refill_needed)
            if person_msg:
                all_messages.append(person_msg)

        # Update Global Message Box
        self.txt_global_message.delete("1.0", tk.END)
        if all_messages:
            full_text = "\n".join(all_messages)
            if self.include_phone_var.get():
                phone_str = self.config.get("PHARMACY", "phone", fallback="").strip()
                if phone_str:
                    full_text += f"\nPhone: {phone_str}"
            self.txt_global_message.insert("1.0", full_text)

    def on_close(self):
        self.save_settings()
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MedTrackerApp(root)
    root.mainloop()
