# README: 
# tkinterdnd2 (493kb)
# ttkbootstrap (5.5kb + 152kb), pillow (9.3kb + 2.6mb)
#
# INSTALL THESE 2: 
# pip install tkinterdnd2
# pip install ttkbootstrap
# 
# python video_compressor3.py


import os
import sys
import shutil
import subprocess
from tkinter import Tk, StringVar, filedialog, messagebox, Frame, Canvas, BooleanVar
from tkinter.ttk import Button, Entry, Progressbar, Checkbutton, Label # Import Label from ttk

from threading import Thread
import time
from tkinter import font # Import the font module

# Attempt to use ttkbootstrap for a modern look, fall back to standard ttk if not found
try:
    from ttkbootstrap import Style
    from tkinterdnd2 import DND_FILES, TkinterDnD
    is_ttkbootstrap_available = True
except ImportError:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    is_ttkbootstrap_available = False
    print("ttkbootstrap not found. The program will use standard tkinter theme.")

# Path to FFmpeg and FFprobe executables.
# If they are in your system's PATH, you don't need to change this.
# If not, provide the full path, e.g., FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"
FFMPEG_PATH = 'ffmpeg'
FFPROBE_PATH = 'ffprobe'

class MP4CompressorGUI(TkinterDnD.Tk if is_ttkbootstrap_available else Tk):
    def __init__(self):
        # Initialize the Tkinter window
        if is_ttkbootstrap_available:
            super().__init__()
            self.style = Style(theme="flatly")
        else:
            super().__init__()
        
        self.title("MP4 Video Compressor")
        self.geometry("600x450") # Increased window height to accommodate new widgets
        self.resizable(False, False)

        # Class variables
        self.source_file_path = None
        self.compression_process = None
        self.delete_logs_var = BooleanVar(value=True)

        # Create GUI elements
        self.create_widgets()

        # Check for a command-line argument (a file path)
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.isfile(file_path):
                self.set_file_path(file_path)

    def create_widgets(self):
        # Define fonts for conditional display
        # These font objects will be used within ttk styles
        self.normal_font_style = font.Font(self, family="TkDefaultFont", size=10)
        self.warning_font_style = font.Font(self, family="TkDefaultFont", size=10, weight="bold")
        self.entry_normal_font_style = font.Font(self, family="TkDefaultFont", size=12)
        self.entry_warning_font_style = font.Font(self, family="TkDefaultFont", size=12, weight="bold")

        # Define ttk styles for Labels and Entries
        self.style.configure('Normal.TLabel', foreground='black', font=self.normal_font_style)
        self.style.configure('Warning.TLabel', foreground='red', font=self.warning_font_style)
        self.style.configure('Normal.TEntry', foreground='black', font=self.entry_normal_font_style)
        self.style.configure('Warning.TEntry', foreground='red', font=self.entry_warning_font_style)

        # --- Drag and Drop Area ---
        dnd_canvas = Canvas(self, relief="groove", borderwidth=8)
        dnd_canvas.configure(bg="#d0d0d0")
        dnd_canvas.place(relx=0.5, rely=0.21, anchor="center", relwidth=0.97, relheight=0.38)
        
        # Add a label inside the canvas to guide the user
        # Note: This is a plain tkinter.Label and does not use ttk styles
        dnd_label = Label(dnd_canvas, text=" Drag & Drop Zone", 
                          anchor="center", font=("Consolas", 10))
        dnd_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Register the canvas as the drop target
        dnd_canvas.drop_target_register(DND_FILES)
        dnd_canvas.dnd_bind('<<Drop>>', self.on_drop)

        # --- File Selection Button ---
        select_button = Button(self, text="Select MP4 File", command=self.browse_file)
        select_button.place(relx=0.5, rely=0.43, anchor="center")

        # --- File Path Display ---
        file_label = Label(self, text="Source File:", style='Normal.TLabel') # Using ttk.Label
        file_label.place(relx=0.05, rely=0.45)
        
        self.source_entry = Entry(self, state='readonly', width=70, style='Normal.TEntry') # Using ttk.Entry
        self.source_entry.place(relx=0.05, rely=0.5, relwidth=0.9)
        
        # --- Output File Path Display ---
        output_label = Label(self, text="Output File:", style='Normal.TLabel') # Using ttk.Label
        output_label.place(relx=0.05, rely=0.6)
        
        self.output_entry = Entry(self, width=70, style='Normal.TEntry') # Using ttk.Entry
        self.output_entry.place(relx=0.05, rely=0.65, relwidth=0.9)
        
        # --- Target Size Input ---
        size_label = Label(self, text="Target Size (MB):", style='Normal.TLabel') # Using ttk.Label
        size_label.place(relx=0.05, rely=0.75)
        
        self.size_var = StringVar(value="7.9")
        # Applying ttk style to Entry
        self.size_entry = Entry(self, textvariable=self.size_var, width=5, style='Normal.TEntry')
        self.size_entry.place(relx=0.30, rely=0.75)
        
        # This line ensures the calculation updates when the size_var changes
        self.size_var.trace_add("write", lambda *args: self.calculate_compression_percentage())

        # --- File Size Information ---
        size_info_canvas = Canvas(self, relief="groove", borderwidth=0)
        size_info_canvas.configure(bg='white')
        size_info_canvas.place(relx=0.45, rely=0.82, relwidth=0.25, relheight=0.08)

        # Labels for displaying size information
        self.original_size_label = Label(size_info_canvas, text="Original Size: N/A", style='Normal.TLabel') # Using ttk.Label
        self.original_size_label.place(relx=0.02, rely=0.2, anchor="w")
        
        # Initialize compression label with default style
        self.compression_label = Label(size_info_canvas, text="Compression: N/A", style='Normal.TLabel') # Using ttk.Label
        self.compression_label.place(relx=0.02, rely=0.8, anchor="w")

        # --- Delete Logs Checkbox ---
        self.delete_logs_checkbox = Checkbutton(self, text="Delete Both Temp Log Files", 
                                                variable=self.delete_logs_var)
        self.delete_logs_checkbox.place(relx=0.95, rely=0.75, anchor="e")

        # --- Compress Button ---
        self.compress_button = Button(self, 
                                     text="Compress Video", 
                                     command=self.start_compression_thread)
        self.compress_button.place(relx=0.95, rely=0.86, anchor="e", relwidth=0.25, relheight=0.15)
        
        # Initialize status label with default style
        self.status_label = Label(self, text="Status: Ready", style='Normal.TLabel') # Using ttk.Label
        self.status_label.place(relx=0.05, rely=0.90)

        # --- Progress Bar ---
        self.progress_bar = Progressbar(self, orient="horizontal", length=540, mode="determinate")
        self.progress_bar.place(relx=0.5, rely=0.97, anchor="center")
        
    def on_drop(self, event):
        """Handle a file being dropped onto the GUI."""
        file_path = event.data
        if "{" in file_path and "}" in file_path:
            file_path = file_path.strip("{}")
        
        self.set_file_path(file_path)

    def browse_file(self):
        """Open a file dialog to select the video."""
        file_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if file_path:
            self.set_file_path(file_path)

    def set_file_path(self, path):
        """Update the GUI with the selected file path."""
        self.source_file_path = path
        self.source_entry.config(state='normal')
        self.source_entry.delete(0, 'end')
        self.source_entry.insert(0, self.source_file_path)
        self.source_entry.config(state='readonly')
        
        # Calculate and display the original file size
        try:
            original_size_bytes = os.path.getsize(self.source_file_path)
            original_size_mb = original_size_bytes / (1024 * 1024)
            self.original_size_label.config(text=f"Original Size: {original_size_mb:.2f} MB", style='Normal.TLabel')
        except OSError:
            self.original_size_label.config(text="Original Size: N/A", style='Normal.TLabel')
        
        # Always call calculate_compression_percentage after setting file path
        # to update all related labels and status based on new file and current target size
        self.calculate_compression_percentage()

        # Generate and set the output path
        dir_name, file_name = os.path.split(self.source_file_path)
        output_file_name = f"Shrunk_{file_name}"
        output_file_path = os.path.join(dir_name, output_file_name)
        
        self.output_entry.delete(0, 'end')
        self.output_entry.insert(0, output_file_path)

    def calculate_compression_percentage(self):
        """Calculates and displays the compression percentage, handles input validation and status."""
        try:
            target_size_input = self.size_var.get()
            
            # Reset formatting to default first for all affected widgets
            self.size_entry.config(style='Normal.TEntry')
            self.status_label.config(text="Status: Ready", style='Normal.TLabel')
            self.compression_label.config(style='Normal.TLabel')

            try:
                target_size_mb = float(target_size_input)
            except ValueError:
                # Non-numeric input
                self.size_entry.config(style='Warning.TEntry')
                self.status_label.config(text="ERROR: Invalid Target Size Input", style='Warning.TLabel')
                self.compression_label.config(text="Compression: N/A", style='Warning.TLabel')
                return

            if target_size_mb <= 0:
                # Target size is 0 or negative
                self.size_entry.config(style='Warning.TEntry')
                self.status_label.config(text="ERROR: Target Size Must Be > 0", style='Warning.TLabel')
                self.compression_label.config(text="Compression: N/A", style='Warning.TLabel')
                return
            
            # Get original file size
            original_size_mb = 0
            if self.source_file_path and os.path.exists(self.source_file_path):
                original_size_bytes = os.path.getsize(self.source_file_path)
                original_size_mb = original_size_bytes / (1024 * 1024)
            
            if original_size_mb == 0:
                self.original_size_label.config(text="Original Size: N/A", style='Normal.TLabel')
                self.compression_label.config(text="Compression: N/A", style='Normal.TLabel')
                self.status_label.config(text="Status: Ready", style='Normal.TLabel')
                return # No source file or zero size, cannot calculate compression

            if target_size_mb >= original_size_mb:
                # Target size is larger than or equal to source size
                self.size_entry.config(style='Warning.TEntry')
                self.status_label.config(text="ERROR: Target Size Larger Than Source Size", style='Warning.TLabel')
                self.compression_label.config(text="Compression: N/A", style='Warning.TLabel')
                return

            # If all checks pass, calculate and display compression percentage
            compression_percent = ((original_size_mb - target_size_mb) / original_size_mb) * 100
            display_text = f"Compression: {int(round(compression_percent, 0))}%"
            
            if compression_percent <= 0:
                self.compression_label.config(text=display_text, style='Warning.TLabel')
            else:
                self.compression_label.config(text=display_text, style='Normal.TLabel')
            
            # If everything is valid, ensure status is 'Ready'
            self.status_label.config(text="Status: Ready", style='Normal.TLabel')
                
        except (ValueError, OSError) as e:
            # General error during calculation/file access
            self.status_label.config(text=f"ERROR: Calculation Issue", style='Warning.TLabel')
            self.compression_label.config(text="Compression: N/A", style='Warning.TLabel')
            self.size_entry.config(style='Warning.TEntry')


    def get_video_info(self):
        """Use ffprobe to get the video duration."""
        try:
            cmd = [
                FFPROBE_PATH,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                self.source_file_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            duration_str = result.stdout.decode('utf-8').strip()
            return float(duration_str)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            messagebox.showerror("Error", f"Could not get video duration with ffprobe.\nIs FFmpeg installed and in your PATH?\nError: {e}")
            return None

    def start_compression_thread(self):
        """Starts the compression in a separate thread to prevent GUI freeze."""
        # Perform a final check before starting compression
        try:
            target_size_mb = float(self.size_var.get())
            
            # Get original size for pre-compression check
            original_size_mb = 0
            if self.source_file_path and os.path.exists(self.source_file_path):
                original_size_bytes = os.path.getsize(self.source_file_path)
                original_size_mb = original_size_bytes / (1024 * 1024)

            if not self.source_file_path or not os.path.exists(self.source_file_path) or not self.source_file_path.endswith('.mp4'):
                messagebox.showerror("Error", "Please select a valid MP4 file.")
                return
            
            if target_size_mb <= 0:
                messagebox.showerror("Error", "Target size must be greater than 0 MB.")
                return
            
            if target_size_mb >= original_size_mb:
                messagebox.showerror("Error", "Target size cannot be larger than or equal to the source file size.")
                return

        except (ValueError, OSError):
            messagebox.showerror("Error", "Please ensure a valid file is selected and target size is a valid positive number.")
            return

        # Disable button to prevent multiple compressions
        self.compress_button.config(state='disabled')
        # Ensure status is black/normal when compression starts
        self.status_label.config(text="Status: Starting...", style='Normal.TLabel')
        
        # Start the compression in a new thread
        compression_thread = Thread(target=self.compress_video)
        compression_thread.start()

    def compress_video(self):
        """Performs the video compression using FFmpeg."""
        try:
            # Get video duration using ffprobe
            duration = self.get_video_info()
            if duration is None:
                raise ValueError("Could not determine video duration.")

            # Get target size from GUI input
            target_size_mb = float(self.size_var.get())
            target_size_bits = target_size_mb * 1024 * 1024 * 8

            # Assuming a standard audio bitrate of 128 kbps
            audio_bitrate = 128000
            target_video_bitrate = (target_size_bits - audio_bitrate * duration) / duration
            
            if target_video_bitrate < 100000:
                messagebox.showwarning("Warning", "Calculated bitrate is very low. Output quality may be poor.")
            
            target_video_bitrate_k = int(target_video_bitrate / 1000)

            # Get output path from the entry box
            output_path = self.output_entry.get()

            # --- Two-pass encoding command ---
            # Pass 1: Analysis Pass
            self.status_label.config(text="Status: Pass 1 (Analyzing video)...", style='Normal.TLabel')
            pass1_command = [
                FFMPEG_PATH, '-y', '-nostdin',
                '-i', self.source_file_path,
                '-c:v', 'libx264',
                '-b:v', f'{target_video_bitrate_k}k',
                '-pass', '1',
                '-an',
                '-f', 'mp4',
                os.devnull
            ]
            
            subprocess.run(pass1_command, check=True)
            self.update_progress(50)

            # Pass 2: Encoding Pass
            self.status_label.config(text="Status: Pass 2 (Encoding video)...", style='Normal.TLabel')
            pass2_command = [
                FFMPEG_PATH, '-y', '-nostdin',
                '-i', self.source_file_path,
                '-c:v', 'libx264',
                '-b:v', f'{target_video_bitrate_k}k',
                '-pass', '2',
                '-c:a', 'aac',
                '-b:a', '128k',
                output_path
            ]

            process = subprocess.Popen(pass2_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            for line in process.stderr:
                self.update_progress_from_ffmpeg(line, duration)
            
            process.wait()
            
            if process.returncode == 0:
                self.status_label.config(text="Status: Compression Complete!", style='Normal.TLabel')
                self.progress_bar['value'] = 100
                messagebox.showinfo("Success", "Video compressed successfully!")
            else:
                stderr_output = process.stderr.read()
                raise subprocess.CalledProcessError(process.returncode, pass2_command, stderr=stderr_output)

        except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as e:
            self.status_label.config(text="Status: Error during compression", style='Warning.TLabel')
            error_message = f"An error occurred during compression:\n{e}"
            messagebox.showerror("Compression Error", error_message)
        finally:
            self.compress_button.config(state='normal')
            
            # Clean up the log files only if the checkbox is checked
            if self.delete_logs_var.get():
                try:
                    log_file = "ffmpeg2pass-0.log"
                    mbtree_file = "ffmpeg2pass-0.log.mbtree"
                    if os.path.exists(log_file):
                        os.remove(log_file)
                    if os.path.exists(mbtree_file):
                        os.remove(mbtree_file)
                except OSError as e:
                    print(f"Error removing log files: {e}")
            # Ensure status and other labels are correctly updated after compression attempt
            self.calculate_compression_percentage()
            
    def update_progress(self, value):
        """Update progress bar value on the main thread."""
        self.progress_bar['value'] = value
        self.update_idletasks()

    def update_progress_from_ffmpeg(self, line, duration):
        """Parse FFmpeg output to update the progress bar."""
        if 'time=' in line:
            parts = line.split('time=')[1].split(' ')[0]
            try:
                h, m, s = map(float, parts.split(':'))
                current_time = h * 3600 + m * 60 + s
                
                # Progress is 50% for pass 1, 50% for pass 2
                progress_val = 50 + (current_time / duration) * 50
                self.progress_bar['value'] = progress_val
                
                # Only update status text if no critical error state (red status) is active
                current_status_style = self.status_label.cget("style")
                if current_status_style != 'Warning.TLabel': 
                    self.status_label.config(text=f"Status: Encoding... ({int(progress_val)}%)", style='Normal.TLabel')
                self.update_idletasks()
            except ValueError:
                pass


if __name__ == "__main__":
    app = MP4CompressorGUI()
    app.mainloop()
