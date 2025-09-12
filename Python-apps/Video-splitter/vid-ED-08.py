import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import cv2
import threading

class VideoCutterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Video Cutter")
        self.root.geometry("900x600")
        
        self.video_path = None
        self.total_frames = 0
        self.split_points = []
        self.current_frame = 0
        self.cap = None
        self.photo_image = None
        self.slider_is_moving = False
        self.frame_to_display = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top frame with buttons and video info
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        open_button = ttk.Button(top_frame, text="Open Video", command=self.open_video)
        open_button.pack(side="left")
        
        self.video_info_label = ttk.Label(top_frame, text="No video loaded.")
        self.video_info_label.pack(side="left", padx=10)
        
        # Paned window for video and controls
        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left Pane: Video Display and Controls
        video_pane = ttk.Frame(main_paned_window)
        main_paned_window.add(video_pane, weight=4)

        video_display_frame = ttk.LabelFrame(video_pane, text="Video Preview")
        video_display_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.video_label = ttk.Label(video_display_frame)
        self.video_label.pack(fill="both", expand=True)
        self.video_label.bind("<Configure>", self.on_resize)
        
        video_controls_frame = ttk.Frame(video_pane)
        video_controls_frame.pack(fill="x", pady=5)
        
        prev_button = ttk.Button(video_controls_frame, text="<<", command=lambda: self.set_frame(self.current_frame - 1))
        prev_button.pack(side="left", padx=5)
        
        self.slider = ttk.Scale(video_controls_frame, from_=1, to=1, orient="horizontal", command=self.on_slider_move)
        self.slider.pack(side="left", fill="x", expand=True)
        
        next_button = ttk.Button(video_controls_frame, text=">>", command=lambda: self.set_frame(self.current_frame + 1))
        next_button.pack(side="left", padx=5)
        
        self.frame_number_label = ttk.Label(video_controls_frame, text="Frame: 1")
        self.frame_number_label.pack(side="right", padx=5)
        
        # Right Pane: Cutting Controls
        cutting_pane = ttk.Frame(main_paned_window)
        main_paned_window.add(cutting_pane, weight=1)

        cutting_frame = ttk.LabelFrame(cutting_pane, text="Cut Points")
        cutting_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(cutting_frame, text="Start Frame:").pack(padx=5, pady=2, anchor="w")
        self.start_frame_entry = ttk.Entry(cutting_frame)
        self.start_frame_entry.pack(fill="x", padx=5, pady=2)
        self.start_frame_entry.insert(0, "6")
        
        ttk.Label(cutting_frame, text="End Frame:").pack(padx=5, pady=2, anchor="w")
        self.end_frame_entry = ttk.Entry(cutting_frame)
        self.end_frame_entry.pack(fill="x", padx=5, pady=2)
        self.end_frame_entry.insert(0, "141")

        # Default Values button
        default_values_button = ttk.Button(cutting_frame, text="Default Values", command=self.set_default_values)
        default_values_button.pack(fill="x", padx=5, pady=5)
        
        # Buttons in the Cut Points frame
        cut_buttons_frame = ttk.Frame(cutting_frame)
        cut_buttons_frame.pack(fill="x", pady=5)

        add_cut_button = ttk.Button(cut_buttons_frame, text="Add Point", command=self.add_cut_point)
        add_cut_button.pack(side="left", expand=True, fill="x", padx=2)
        
        remove_selected_button = ttk.Button(cut_buttons_frame, text="Remove Selected", command=self.remove_segment)
        remove_selected_button.pack(side="right", expand=True, fill="x", padx=2)
        
        # Segment List and Control Buttons
        segments_frame = ttk.LabelFrame(cutting_pane, text="Segments to Save")
        segments_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.cut_listbox = tk.Listbox(segments_frame, selectmode=tk.SINGLE, height=10)
        self.cut_listbox.pack(padx=5, pady=5, fill="both", expand=True)
        
        # Bottom Frame: Start Splitting and Options
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill="x", padx=10, pady=5)

        # Bottom controls on the left
        bottom_left_frame = ttk.Frame(bottom_frame)
        bottom_left_frame.pack(side="left", padx=5, pady=5)
        
        set_first_frame_button = ttk.Button(bottom_left_frame, text="Set as First Frame", command=lambda: self.start_frame_entry.delete(0, tk.END) or self.start_frame_entry.insert(0, self.current_frame))
        set_first_frame_button.pack(side="left", padx=5)

        set_last_frame_button = ttk.Button(bottom_left_frame, text="Set as Last Frame", command=lambda: self.end_frame_entry.delete(0, tk.END) or self.end_frame_entry.insert(0, self.current_frame))
        set_last_frame_button.pack(side="left", padx=5)

        # Bottom controls on the right
        bottom_right_frame = ttk.Frame(bottom_frame)
        bottom_right_frame.pack(side="right", padx=5, pady=5)

        self.show_popup_var = tk.BooleanVar(value=True)
        self.show_popup_checkbox = ttk.Checkbutton(bottom_right_frame, text="popup on complete", variable=self.show_popup_var)
        self.show_popup_checkbox.pack(side="left", padx=5)
        
        self.split_button = ttk.Button(bottom_right_frame, text="Start Splitting", command=self.start_splitting, state="disabled")
        self.split_button.pack(side="right", padx=5)
        
    def set_default_values(self):
        """Sets the Start and End Frame entries to the default values."""
        self.start_frame_entry.delete(0, tk.END)
        self.start_frame_entry.insert(0, "6")
        self.end_frame_entry.delete(0, tk.END)
        self.end_frame_entry.insert(0, "141")

    def on_resize(self, event):
        if self.video_path and self.video_label.winfo_width() > 0 and self.video_label.winfo_height() > 0:
            self.display_current_frame()

    def open_video(self):
        file_path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")]
        )
        if file_path:
            self.load_video(file_path)

    def load_video(self, file_path):
        self.video_path = file_path
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open video file.")
            self.video_path = None
            return
            
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_info_label.config(text=f"Video: {os.path.basename(self.video_path)}\nTotal Frames: {self.total_frames}")
        
        # Set slider to go from 1 to the total number of frames
        self.slider.config(to=self.total_frames)
        self.set_frame(1) # Start on frame 1
        
        self.split_points.clear()
        self.cut_listbox.delete(0, tk.END)
        self.split_button.config(state="normal")
        
    def set_frame(self, frame_number):
        if not self.cap or not self.cap.isOpened():
            return
        
        if self.slider_is_moving:
            return

        frame_number = max(1, min(frame_number, self.total_frames))
        self.current_frame = frame_number
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame - 1)
        ret, frame = self.cap.read()
        
        if ret:
            self.frame_to_display = frame
            
            self.slider_is_moving = True
            self.slider.set(self.current_frame)
            self.slider_is_moving = False
            self.frame_number_label.config(text=f"Frame: {self.current_frame}")
            
            self.display_current_frame()
            
    def display_current_frame(self):
        if self.frame_to_display is None:
            return
            
        frame = self.frame_to_display.copy()
            
        max_width = self.video_label.winfo_width()
        max_height = self.video_label.winfo_height()

        if max_width <= 0 or max_height <= 0:
            return

        h, w, _ = frame.shape
        
        ratio = min(max_width / w, max_height / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        
        resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        cv2.putText(resized_frame, f"Frame: {self.current_frame}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        
        image = tk.PhotoImage(data=cv2.imencode('.ppm', resized_frame)[1].tobytes())
        self.photo_image = image
        self.video_label.config(image=self.photo_image)

    def on_slider_move(self, value):
        self.set_frame(int(float(value)))

    def add_cut_point(self):
        if not self.video_path:
            messagebox.showwarning("Warning", "Please open a video first.")
            return

        try:
            start_frame = int(self.start_frame_entry.get())
            end_frame = int(self.end_frame_entry.get())
            
            if not (1 <= start_frame < end_frame <= self.total_frames):
                raise ValueError
                
            self.split_points.append((start_frame, end_frame))
            self.split_points.sort()
            
            self.update_listbox()
            
        except ValueError:
            messagebox.showerror("Error", f"Invalid frame numbers. Must be integers where 1 <= Start < End <= {self.total_frames}")

    def remove_segment(self):
        selected_index = self.cut_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Warning", "Please select a segment to remove.")
            return
            
        self.split_points.pop(selected_index[0])
        self.update_listbox()

    def update_listbox(self):
        self.cut_listbox.delete(0, tk.END)
        for i, (start, end) in enumerate(self.split_points):
            self.cut_listbox.insert(tk.END, f"Segment {i+1}: Frames {start} to {end}")
            
    def start_splitting(self):
        if not self.video_path or not self.split_points:
            messagebox.showwarning("Warning", "Please open a video and add at least one cut point.")
            return
        
        def run_splitting():
            output_dir = filedialog.askdirectory(title="Select a folder to save the cut videos")
            if not output_dir:
                return
            
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            
            try:
                ffprobe_command = [
                    'ffprobe', 
                    '-v', 'error', 
                    '-select_streams', 'v:0', 
                    '-show_entries', 'stream=bit_rate', 
                    '-of', 'default=noprint_wrappers=1:nokey=1', 
                    self.video_path
                ]
                
                bitrate_output = subprocess.run(ffprobe_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                source_bitrate = bitrate_output.stdout.decode('utf-8').strip()
                
                if not source_bitrate:
                    bitrate_arg = ['-crf', '23']
                else:
                    bitrate_arg = ['-b:v', f"{int(int(source_bitrate) / 1000)}k"]

                frame_rate = self.cap.get(cv2.CAP_PROP_FPS)
                
                for i, (start_frame, end_frame) in enumerate(self.split_points):
                    output_file = os.path.join(output_dir, f"{base_name}_cut_{i+1}.mp4")
                    
                    start_time_sec = (start_frame - 1) / frame_rate
                    duration_sec = (end_frame - start_frame + 1) / frame_rate
                    
                    ffmpeg_command = [
                        'ffmpeg', '-y', 
                        '-ss', str(start_time_sec), 
                        '-i', self.video_path, 
                        '-t', str(duration_sec), 
                        '-c:v', 'libx264',
                    ]
                    ffmpeg_command.extend(bitrate_arg)
                    ffmpeg_command.extend(['-c:a', 'copy', output_file])
                    
                    subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                if self.show_popup_var.get():
                    messagebox.showinfo("Success", "Video splitting complete!")
                    
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"FFmpeg/FFprobe error: {e.stderr.decode()}")
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")

        threading.Thread(target=run_splitting).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCutterApp(root)
    root.mainloop()
