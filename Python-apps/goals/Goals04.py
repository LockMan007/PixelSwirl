import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Entry, Button, Frame, Checkbutton, IntVar
import json
import os
from datetime import datetime, timedelta

# --- Audio Utility ---
def play_audio_alert():
    """Plays a simple system beep sound."""
    if os.name == 'nt':  # Check if the OS is Windows
        try:
            import winsound
            winsound.Beep(440, 200)  # Play a 440 Hz beep for 200 ms
        except ImportError:
            print("winsound module not available. Cannot play beep.")
    else:
        # Fallback for other systems
        print('\a')

# --- JSON File Setup ---
JSON_FILE = 'goals.json'

def setup_json_file():
    """Initializes the JSON file with a default structure."""
    if not os.path.exists(JSON_FILE):
        data = {'last_goal_id': 0, 'goals': []}
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=4)

def load_goals():
    """Loads all goals from the JSON file."""
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    goals = []
    for goal in data['goals']:
        goal_id = goal['id']
        name = goal['name']
        
        # Load frequency in parts (days, hours, minutes)
        frequency_days_ini = goal.get('frequency_days', 0)
        frequency_hours_ini = goal.get('frequency_hours', 0)
        frequency_minutes_ini = goal.get('frequency_minutes', 0)
        
        # Convert to a single float for internal calculations
        frequency_days_calc = frequency_days_ini + frequency_hours_ini / 24 + frequency_minutes_ini / (24 * 60)
        
        last_completed_date = datetime.fromisoformat(goal['last_completed_date'])
        image_path = goal.get('image_path', '')
        audio_alert = goal.get('audio_alert', False) # New field
        
        goals.append((goal_id, name, frequency_days_calc, last_completed_date, image_path, audio_alert))
    return goals

def get_goal_by_id(goal_id):
    """Retrieves a single goal dictionary by its ID."""
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    for goal in data['goals']:
        if goal['id'] == goal_id:
            return goal
    return None

def save_or_update_goal(goal_id, name, days, hours, minutes, image_path, audio_alert):
    """Saves a new goal or updates an existing one."""
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    # Check if this is an existing goal
    is_existing = False
    for i, goal in enumerate(data['goals']):
        if goal['id'] == goal_id:
            data['goals'][i] = {
                'id': goal_id,
                'name': name,
                'frequency_days': days,
                'frequency_hours': hours,
                'frequency_minutes': minutes,
                'last_completed_date': goal['last_completed_date'],
                'image_path': image_path,
                'audio_alert': audio_alert
            }
            is_existing = True
            break
            
    # If not existing, create a new one
    if not is_existing:
        last_id = data.get('last_goal_id', 0)
        new_id = last_id + 1
        
        new_goal = {
            'id': new_id,
            'name': name,
            'frequency_days': days,
            'frequency_hours': hours,
            'frequency_minutes': minutes,
            'last_completed_date': datetime.now().isoformat(),
            'image_path': image_path,
            'audio_alert': audio_alert
        }
        
        data['goals'].append(new_goal)
        data['last_goal_id'] = new_id

    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_goal_completion(goal_id, last_completed_date):
    """Updates the last completion date for a goal in the JSON file."""
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
        
    for goal in data['goals']:
        if goal['id'] == goal_id:
            goal['last_completed_date'] = last_completed_date.isoformat()
            break

    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def delete_goal(goal_id):
    """Deletes a goal from the JSON file."""
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    data['goals'] = [goal for goal in data['goals'] if goal['id'] != goal_id]
    
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Color Utility ---
def hex_to_rgb(hex_color):
    """Converts a hex color string to an RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_tuple):
    """Converts an RGB tuple to a hex color string."""
    return '#{:02x}{:02x}{:02x}'.format(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2])

def interpolate_color(color1, color2, ratio):
    """Blends two colors based on a ratio."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    
    return rgb_to_hex((r, g, b))

# --- GUI Application ---
class GoalTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Goal Tracker")
        self.geometry("800x600")

        self.column_frames = {}

        self.setup_ui()
        self.load_and_display_goals()
        
        self.after(1000, self.update_timers_and_heights)

    def setup_ui(self):
        """Sets up the main application layout."""
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        add_button = Button(self, text="Add Goal", command=lambda: self.open_goal_window(None))
        add_button.pack(pady=5)
        
    def open_goal_window(self, goal_id):
        """Opens a new window for adding/modifying a goal."""
        is_modify_mode = goal_id is not None
        if is_modify_mode:
            goal_data = get_goal_by_id(goal_id)
            if not goal_data:
                messagebox.showerror("Error", "Goal not found.")
                return
        
        add_window = Toplevel(self)
        add_window.title("Modify Goal" if is_modify_mode else "Add New Goal")
        add_window.geometry("300x300")
        
        # --- Form Fields ---
        Label(add_window, text="Name:").pack(pady=5)
        name_entry = Entry(add_window)
        name_entry.pack(padx=10)
        if is_modify_mode:
            name_entry.insert(0, goal_data['name'])

        Label(add_window, text="Frequency:").pack(pady=5)
        freq_frame = Frame(add_window)
        freq_frame.pack(pady=5)

        Label(freq_frame, text="Days:").pack(side='left')
        days_entry = Entry(freq_frame, width=5)
        days_entry.pack(side='left', padx=5)
        days_entry.insert(0, str(goal_data['frequency_days']) if is_modify_mode else "0")

        Label(freq_frame, text="Hours:").pack(side='left')
        hours_entry = Entry(freq_frame, width=5)
        hours_entry.pack(side='left', padx=5)
        hours_entry.insert(0, str(goal_data['frequency_hours']) if is_modify_mode else "0")
        
        Label(freq_frame, text="Minutes:").pack(side='left')
        minutes_entry = Entry(freq_frame, width=5)
        minutes_entry.pack(side='left', padx=5)
        minutes_entry.insert(0, str(goal_data['frequency_minutes']) if is_modify_mode else "0")

        Label(add_window, text="Image name:").pack(pady=5)
        image_entry = Entry(add_window)
        image_entry.pack(padx=10)
        if is_modify_mode:
            image_entry.insert(0, goal_data['image_path'])

        audio_var = IntVar()
        audio_checkbox = Checkbutton(add_window, text="Audio Alert", variable=audio_var)
        audio_checkbox.pack(pady=5)
        if is_modify_mode and goal_data['audio_alert']:
            audio_var.set(1)

        def save_and_close():
            try:
                name = name_entry.get().strip()
                days = int(days_entry.get() or 0)
                hours = int(hours_entry.get() or 0)
                minutes = int(minutes_entry.get() or 0)
                image_name = image_entry.get().strip()
                audio_alert = bool(audio_var.get())
                
                if not name or (days == 0 and hours == 0 and minutes == 0):
                    messagebox.showerror("Invalid Input", "Name and frequency must be specified.")
                    return
                if days < 0 or hours < 0 or minutes < 0:
                    messagebox.showerror("Invalid Input", "Frequency values must be non-negative.")
                    return

                save_or_update_goal(goal_id, name, days, hours, minutes, image_name, audio_alert)
                add_window.destroy()
                self.load_and_display_goals()
                
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid integers for frequency.")

        save_button = Button(add_window, text="Save Goal", command=save_and_close)
        save_button.pack(pady=10)

    def load_and_display_goals(self):
        """Clears existing columns and loads all goals from the JSON file."""
        for frame in self.column_frames.values():
            frame.destroy()
        self.column_frames.clear()

        goals = load_goals()
        for i, (goal_id, name, freq_calc, last_date, img_path, audio_alert) in enumerate(goals):
            self.create_goal_column(goal_id, name, freq_calc, last_date, img_path, audio_alert)
    
    def create_goal_column(self, goal_id, name, frequency, last_completed_date, image_path, audio_alert):
        """Creates a single column for a goal."""
        column_frame = Frame(self.main_frame, bd=2, relief="groove")
        column_frame.pack(side='left', fill='y', padx=5, expand=True)
        self.column_frames[goal_id] = column_frame
        
        # Make the frame and its children clickable to open the modify window
        column_frame.bind("<Button-1>", lambda event: self.open_goal_window(goal_id))
        
        timer_label = Label(column_frame, text="", font=("Helvetica", 12))
        timer_label.pack(pady=5)
        timer_label.bind("<Button-1>", lambda event: self.open_goal_window(goal_id))

        canvas = tk.Canvas(column_frame, width=120, height=400)
        canvas.pack(pady=5, padx=5, fill='y', expand=True)
        canvas.bind("<Button-1>", lambda event: self.open_goal_window(goal_id))

        try:
            if image_path and os.path.exists(f"images/{image_path}"):
                img = tk.PhotoImage(file=f"images/{image_path}")
            else:
                img = tk.PhotoImage(file="images/default_balloon.png")
            
            canvas.image = img
            
            y_pos = self.calculate_y_position(last_completed_date, frequency, canvas.winfo_height())
            canvas.create_image(60, y_pos, image=img, tags="balloon")
            
        except tk.TclError:
            messagebox.showerror("Image Error", f"Could not load image: {image_path}. Using a circle instead.")
            canvas.create_oval(30, 10, 90, 70, fill="blue", tags="balloon")
        
        canvas.tag_bind("balloon", "<Button-1>", lambda event: self.open_goal_window(goal_id))

        label = Label(column_frame, text=name, wraplength=120)
        label.pack(pady=5)
        label.bind("<Button-1>", lambda event: self.open_goal_window(goal_id))

        reset_button = Button(column_frame, text="Reset", command=lambda: self.reset_goal(goal_id))
        reset_button.pack(pady=2)

        delete_button = Button(column_frame, text="Delete", fg="red", command=lambda: self.delete_and_reload(goal_id))
        delete_button.pack(pady=2)

        column_frame.data = {
            "id": goal_id,
            "frequency": frequency,
            "last_completed_date": last_completed_date,
            "canvas": canvas,
            "timer_label": timer_label,
            "audio_alert": audio_alert,
            "alerted": False
        }

    def calculate_y_position(self, last_completed, frequency_days, canvas_height):
        """Calculates the vertical position of the balloon image."""
        time_elapsed = (datetime.now() - last_completed).total_seconds()
        total_time = frequency_days * 24 * 60 * 60
        
        progress = min(time_elapsed / total_time, 1.0)
        
        padding = 30
        min_y = padding
        max_y = canvas_height - padding
        
        return min_y + progress * (max_y - min_y)

    def get_bg_color(self, progress):
        """Returns a hex color based on the progress from green to red."""
        green = "#00FF00"
        yellow = "#FFFF00"
        red = "#FF0000"

        if progress < 0.5:
            ratio = progress / 0.5
            return interpolate_color(green, yellow, ratio)
        else:
            ratio = (progress - 0.5) / 0.5
            return interpolate_color(yellow, red, ratio)

    def format_countdown_timer(self, time_left: timedelta, audio_alert: bool) -> str:
        """Formats the timedelta into a concise string and adds audio indicator."""
        total_seconds = int(time_left.total_seconds())
        
        sign = ""
        if total_seconds < 0:
            sign = "-"
            total_seconds = abs(total_seconds)

        years = total_seconds // (365 * 24 * 3600)
        total_seconds %= (365 * 24 * 3600)
        months = total_seconds // (30 * 24 * 3600)
        total_seconds %= (30 * 24 * 3600)
        days = total_seconds // (24 * 3600)
        total_seconds %= (24 * 3600)
        hours = total_seconds // 3600
        total_seconds %= 3600
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        parts = []
        if years > 0:
            parts.append(f"{years}y")
        if months > 0:
            parts.append(f"{months}m")
        if days > 0:
            parts.append(f"{days}d")
        
        if not parts:
            timer_str = f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0 and len(parts) < 3:
                parts.append(f"{minutes}m")
            timer_str = f"{sign}{' '.join(parts)}"
        
        # Append audio emoji if enabled
        if audio_alert:
            timer_str += " 🔊"
        
        return timer_str

    def reset_goal(self, goal_id):
        """Resets the goal's completion date and updates the JSON file."""
        update_goal_completion(goal_id, datetime.now())
        self.load_and_display_goals()

    def delete_and_reload(self, goal_id):
        """Deletes a goal after confirmation and reloads the UI."""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this goal?"):
            delete_goal(goal_id)
            self.load_and_display_goals()

    def update_timers_and_heights(self):
        """Periodically updates the height of all balloon images and the countdown timers."""
        for frame in self.column_frames.values():
            data = frame.data
            canvas = data["canvas"]
            timer_label = data["timer_label"]
            
            time_elapsed = (datetime.now() - data["last_completed_date"]).total_seconds()
            total_time = data["frequency"] * 24 * 60 * 60
            progress = min(time_elapsed / total_time, 1.0)
            
            bg_color = self.get_bg_color(progress)
            canvas.config(bg=bg_color)

            new_y = self.calculate_y_position(data["last_completed_date"], data["frequency"], canvas.winfo_height())
            canvas.coords("balloon", 60, new_y)
            
            time_left = timedelta(days=data["frequency"]) - (datetime.now() - data["last_completed_date"])
            timer_label.config(text=self.format_countdown_timer(time_left, data["audio_alert"]))
            
            if time_left.total_seconds() <= 0:
                timer_label.config(fg="red")
                if data["audio_alert"] and not data["alerted"]:
                    play_audio_alert()
                    data["alerted"] = True
            else:
                timer_label.config(fg="black")
                data["alerted"] = False
        
        self.after(1000, self.update_timers_and_heights)

if __name__ == "__main__":
    if not os.path.exists("images"):
        os.makedirs("images")
        print("Created 'images' directory.")

    if not os.path.exists('images/default_balloon.png'):
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((10, 10, 90, 90), fill='skyblue', outline='darkblue', width=2)
        img.save('images/default_balloon.png')

    setup_json_file()
    app = GoalTrackerApp()
    app.mainloop()