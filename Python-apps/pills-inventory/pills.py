import os
import configparser
from datetime import datetime, date, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG_FILE = "medications.ini"
DATE_FORMAT = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "%m/%d/%Y"

class MedTrackerApp:
    def __init__(self, root):
        self.root = root
        self.config = configparser.ConfigParser()
        self.root.geometry("535x775")
        
        self.selected_section = None
        self.load_config()
        
        # Check and process daily dosage roll
        self.process_daily_deductions()

        self.update_titlebar()

        # Input Frame (Add / Update Medication)
        input_frame = ttk.LabelFrame(self.root, text="Add / Update Medication", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Person Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.entry_person = ttk.Entry(input_frame)
        self.entry_person.grid(row=0, column=1, padx=5, pady=2)
        self.entry_person.bind("<KeyRelease>", self.on_input_change)

        ttk.Label(input_frame, text="Pill Name:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.entry_pill = ttk.Entry(input_frame)
        self.entry_pill.grid(row=1, column=1, padx=5, pady=2)
        self.entry_pill.bind("<KeyRelease>", self.on_input_change)

        ttk.Label(input_frame, text="Current Quantity:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.entry_quantity = ttk.Entry(input_frame)
        self.entry_quantity.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Daily Frequency:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.entry_daily = ttk.Entry(input_frame)
        self.entry_daily.grid(row=3, column=1, padx=5, pady=2)

        # Action Button & Clear Selection
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=8)

        self.btn_save = ttk.Button(btn_frame, text="Save New Medication", command=self.save_medication)
        self.btn_save.pack(side="left", padx=5)

        self.btn_clear = ttk.Button(btn_frame, text="Cancel / Clear Selection", command=self.reset_form)
        self.btn_clear.pack(side="left", padx=5)

        # Daily Deduction Banner Indicator
        today_str = date.today().strftime(DISPLAY_DATE_FORMAT)
        self.lbl_status = tk.Label(
            self.root, 
            text=f"All of today's pills have been subtracted for {today_str}", 
            fg="blue", 
            font=("Arial", 9, "bold")
        )
        self.lbl_status.pack(pady=2)

        # Scrollable Area for Displaying Results
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")

        self.render_dashboard()

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
            
        self.root.title(f"Medication Stock Tracker -- {parsed_date}")

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
                
                # Subtract total dosage accumulated over passed days
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

        # If user changes Name or Pill fields away from selected item, default to new save
        if entered_p != current_p or entered_m != current_m:
            self.btn_save.config(text="Save New Medication")
        else:
            self.btn_save.config(text="Update Medication")

    def select_medication(self, person, pill, qty, daily):
        self.selected_section = f"{person} - {pill}"
        
        self.entry_person.delete(0, tk.END)
        self.entry_person.insert(0, person)

        self.entry_pill.delete(0, tk.END)
        self.entry_pill.insert(0, pill)

        self.entry_quantity.delete(0, tk.END)
        self.entry_quantity.insert(0, str(qty))

        self.entry_daily.delete(0, tk.END)
        self.entry_daily.insert(0, str(daily))

        self.btn_save.config(text="Update Medication")

    def reset_form(self):
        self.selected_section = None
        self.entry_person.delete(0, tk.END)
        self.entry_pill.delete(0, tk.END)
        self.entry_quantity.delete(0, tk.END)
        self.entry_daily.delete(0, tk.END)
        self.btn_save.config(text="Save New Medication")

    def save_medication(self):
        person = self.entry_person.get().strip()
        pill = self.entry_pill.get().strip()
        qty = self.entry_quantity.get().strip()
        daily = self.entry_daily.get().strip()

        if not person or not pill or not qty.isdigit() or not daily.isdigit():
            messagebox.showerror("Error", "Please enter valid values. Quantity and Daily must be integers.")
            return

        section_name = f"{person} - {pill}"
        
        if not self.config.has_section(section_name):
            self.config.add_section(section_name)

        self.config.set(section_name, "Quantity", qty)
        self.config.set(section_name, "Daily", daily)
        
        # Record update date
        today_str = date.today().strftime(DATE_FORMAT)
        self.config.set("SYSTEM", "last_updated", today_str)

        self.save_config()
        self.update_titlebar()
        self.render_dashboard()
        self.reset_form()

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
            days_left = qty // daily if daily > 0 else 0

            people[person].append({
                "pill": pill,
                "qty": qty,
                "daily": daily,
                "days_left": days_left
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
                # Clickable labels that auto-fill the edit panel
                lbl_pill = ttk.Label(p_frame, text=med["pill"], cursor="hand2")
                lbl_days = ttk.Label(p_frame, text=f"{med['days_left']} Days remaining", cursor="hand2")
                lbl_qty = ttk.Label(p_frame, text=f"{med['qty']} pills", cursor="hand2")
                lbl_daily = ttk.Label(p_frame, text=f"{med['daily']} per day")

                lbl_pill.grid(row=row_idx, column=0, padx=10, pady=2, sticky="w")
                lbl_days.grid(row=row_idx, column=1, padx=10, pady=2, sticky="w")
                lbl_qty.grid(row=row_idx, column=2, padx=10, pady=2, sticky="w")
                lbl_daily.grid(row=row_idx, column=3, padx=10, pady=2, sticky="w")

                # Bind click events to load data into the input form
                for widget in (lbl_pill, lbl_days, lbl_qty):
                    widget.bind("<Button-1>", lambda e, p=person, m=med: self.select_medication(
                        p, m["pill"], m["qty"], m["daily"]
                    ))

                if med["days_left"] <= 7:
                    refill_needed.append(med["pill"])

            refill_text = f"[NEED REFILL ON: {', '.join(refill_needed)}]" if refill_needed else "[NEED REFILL ON: none]"
            alert_color = "red" if refill_needed else "green"
            
            refill_lbl = tk.Label(p_frame, text=refill_text, fg=alert_color, font=("Arial", 10, "bold"))
            refill_lbl.grid(row=len(sorted_meds) + 1, column=0, columnspan=4, pady=(8, 2), sticky="w")

if __name__ == "__main__":
    root = tk.Tk()
    app = MedTrackerApp(root)
    root.mainloop()