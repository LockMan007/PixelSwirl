import tkinter as tk
from tkinter import filedialog, messagebox, PhotoImage, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
import seam_carving as sc
import sys
import subprocess
import os # Import os module for path manipulation

# --- Package Installation Check ---
REQUIRED_PACKAGES_MAP = {
    "opencv-python": "cv2",
    "numpy": "numpy",
    "Pillow": "PIL",
    "seam_carving": "seam_carving"
}

def check_and_install_packages(packages_map):
    missing_packages_for_install = []
    missing_modules_for_import = {}

    for install_name, import_name in packages_map.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages_for_install.append(install_name)
            missing_modules_for_import[install_name] = import_name

    if missing_packages_for_install:
        messagebox.showinfo("Missing Packages",
                            "The following packages are missing:\n" +
                            "\n".join([f"- {pkg_name} (module: {packages_map[pkg_name]})" for pkg_name in missing_packages_for_install]) +
                            "\n\nWould you like to install them? This might require an internet connection.")
        response = messagebox.askyesno("Install Packages?", "Install now?")

        if response:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages_for_install)
                messagebox.showinfo("Installation Complete", "Packages installed successfully! Please restart the application.")
                return False
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Installation Error", f"Error installing packages: {e}\nPlease try installing them manually: pip install " + " ".join(missing_packages_for_install))
                return False
            except Exception as e:
                messagebox.showerror("Installation Error", f"An unexpected error occurred during installation: {e}\nPlease try installing them manually: pip install " + " ".join(missing_packages_for_install))
                return False
        else:
            messagebox.showwarning("Installation Skipped", "Skipping package installation. The application may not run correctly without them.")
            return False
    else:
        return True

# --- Seam Carving Logic ---
def perform_seam_carving(image_np, target_width, target_height):
    current_height, current_width, _ = image_np.shape

    # Apply width adjustment
    if target_width != current_width:
        print(f"Seam Carving: Adjusting width from {current_width} to {target_width}...")
        image_np = sc.resize(image_np, size=(target_width, current_height), energy_mode="backward", order="width-first")
        current_height, current_width, _ = image_np.shape

    # Apply height adjustment
    if target_height != current_height:
        print(f"Seam Carving: Adjusting height from {current_height} to {target_height}...")
        image_np = sc.resize(image_np, size=(target_width, target_height), energy_mode="backward", order="height-first")
    
    return image_np

class ImageResizerApp:
    def __init__(self, master):
        self.master = master
        master.title("Image Resizer (Seam Carving GUI)")

        self.original_image_pil = None
        self.display_image_pil = None
        self.original_image_np = None

        self.width_trace_id = None
        self.height_trace_id = None

        self.create_widgets()
        self.update_info_display()

        # Initial state of checkboxes
        self.toggle_aspect_ratio()
        self.toggle_pixel_preserve()

    def create_widgets(self):
        control_frame = ttk.LabelFrame(self.master, text="Controls", padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.load_button = ttk.Button(control_frame, text="Load Image", command=self.load_image)
        self.load_button.grid(row=0, column=0, columnspan=2, pady=5)

        # Save Button - New
        self.save_button = ttk.Button(control_frame, text="Save Image As...", command=self.save_image)
        self.save_button.grid(row=0, column=2, columnspan=2, pady=5, padx=10) # Placed next to load
        self.save_button.config(state=tk.DISABLED) # Disable until image is loaded/processed


        ttk.Label(control_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.width_var = tk.IntVar(value=0)
        self.width_spinbox = ttk.Spinbox(control_frame, from_=1, to_=4000, textvariable=self.width_var, width=8)
        self.width_spinbox.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(control_frame, text="Height:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.height_var = tk.IntVar(value=0)
        self.height_spinbox = ttk.Spinbox(control_frame, from_=1, to_=4000, textvariable=self.height_var, width=8)
        self.height_spinbox.grid(row=2, column=1, sticky=tk.W, pady=2)

        self.maintain_aspect_ratio = tk.BooleanVar(value=False)
        self.aspect_ratio_checkbox = ttk.Checkbutton(control_frame, text="Maintain Aspect Ratio", variable=self.maintain_aspect_ratio, command=self.toggle_aspect_ratio)
        self.aspect_ratio_checkbox.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)

        self.preserve_total_pixels = tk.BooleanVar(value=True)
        self.preserve_total_pixels_checkbox = ttk.Checkbutton(control_frame, text="Preserve Total Pixels (Word-Wrap)", variable=self.preserve_total_pixels, command=self.toggle_pixel_preserve)
        self.preserve_total_pixels_checkbox.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Initial traces - they will be managed by toggle functions later
        self.width_trace_id = self.width_var.trace_add("write", self.on_width_change)
        self.height_trace_id = self.height_var.trace_add("write", self.on_height_change)


        self.apply_button = ttk.Button(control_frame, text="Apply Resize", command=self.apply_resize)
        self.apply_button.grid(row=5, column=0, columnspan=2, pady=10)
        self.apply_button.config(state=tk.DISABLED)

        info_frame = ttk.LabelFrame(self.master, text="Image Info", padding="10")
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.current_dims_label = ttk.Label(info_frame, text="Current Dims: N/A")
        self.current_dims_label.pack(anchor=tk.W)

        self.original_dims_label = ttk.Label(info_frame, text="Original Dims: N/A")
        self.original_dims_label.pack(anchor=tk.W)

        self.original_pixel_count_label = ttk.Label(info_frame, text="Original Pixels: N/A")
        self.original_pixel_count_label.pack(anchor=tk.W)
        
        self.current_pixel_count_label = ttk.Label(info_frame, text="Current Pixels: N/A")
        self.current_pixel_count_label.pack(anchor=tk.W)

        self.canvas_frame = ttk.Frame(self.master, borderwidth=2, relief="groove")
        self.canvas_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg="gray", borderwidth=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas_image_id = None

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if file_path:
            try:
                self.original_image_pil = Image.open(file_path).convert("RGB")
                self.original_image_np = np.array(self.original_image_pil)
                
                self.width_var.set(self.original_image_pil.width)
                self.height_var.set(self.original_image_pil.height)
                
                self.display_image(self.original_image_pil)
                self.update_info_display()
                self.apply_button.config(state=tk.NORMAL)
                self.save_button.config(state=tk.NORMAL) # Enable save button
                
                self.toggle_aspect_ratio()
                self.toggle_pixel_preserve()
                
                messagebox.showinfo("Image Loaded", f"Loaded image: {os.path.basename(file_path)}\nOriginal size: {self.original_image_pil.width}x{self.original_image_pil.height}")

            except Exception as e:
                messagebox.showerror("Error Loading Image", f"Could not load image: {e}")
                self.original_image_pil = None
                self.original_image_np = None
                self.apply_button.config(state=tk.DISABLED)
                self.save_button.config(state=tk.DISABLED) # Disable save button

    def save_image(self):
        if self.display_image_pil is None:
            messagebox.showwarning("No Image to Save", "Load or process an image first before saving.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*")
            ],
            title="Save Image As"
        )

        if file_path:
            try:
                # Ensure the image is in a format Pillow can save (e.g., RGB for JPG, RGBA for PNG)
                # We've been converting to RGB throughout, which is good for JPG/PNG
                self.display_image_pil.save(file_path)
                messagebox.showinfo("Save Successful", f"Image saved to:\n{os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save image: {e}")
                import traceback
                traceback.print_exc()

    def display_image(self, pil_image):
        if pil_image:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width == 0 or canvas_height == 0:
                self.canvas.update_idletasks()
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                if canvas_width == 0 or canvas_height == 0:
                    canvas_width = 800
                    canvas_height = 600

            img_width, img_height = pil_image.size
            
            img_aspect = img_width / img_height
            canvas_aspect = canvas_width / canvas_height

            if img_aspect > canvas_aspect:
                new_width = canvas_width
                new_height = int(new_width / img_aspect)
            else:
                new_height = canvas_height
                new_width = int(new_height * img_aspect)

            if new_width < 10 or new_height < 10:
                new_width, new_height = img_width, img_height

            try:
                display_img_resized = pil_image.resize((max(1, new_width), max(1, new_height)), Image.LANCZOS)
                self.display_image_tk = ImageTk.PhotoImage(display_img_resized)
                
                if self.canvas_image_id:
                    self.canvas.delete(self.canvas_image_id)
                
                x_center = canvas_width / 2
                y_center = canvas_height / 2
                self.canvas_image_id = self.canvas.create_image(x_center, y_center, image=self.display_image_tk, anchor=tk.CENTER)
                
                self.display_image_pil = pil_image # Update the reference to the *actual* PIL image being displayed
                self.update_info_display()

            except Exception as e:
                messagebox.showerror("Error Displaying Image", f"Could not display image: {e}")
                self.display_image_pil = None
        else:
            if self.canvas_image_id:
                self.canvas.delete(self.canvas_image_id)
            self.display_image_pil = None
            self.update_info_display()

    def update_info_display(self):
        if self.original_image_pil:
            original_w, original_h = self.original_image_pil.size
            original_pixels = original_w * original_h
            self.original_dims_label.config(text=f"Original Dims: {original_w}x{original_h} pixels")
            self.original_pixel_count_label.config(text=f"Original Pixels: {original_pixels}")
        else:
            self.original_dims_label.config(text="Original Dims: N/A")
            self.original_pixel_count_label.config(text="Original Pixels: N/A")

        if self.display_image_pil:
            current_w, current_h = self.display_image_pil.size
            current_pixels = current_w * current_h
            self.current_dims_label.config(text=f"Current Dims: {current_w}x{current_h} pixels")
            self.current_pixel_count_label.config(text=f"Current Pixels: {current_pixels}")
        else:
            self.current_dims_label.config(text="Current Dims: N/A")
            self.current_pixel_count_label.config(text="Current Pixels: N/A")

    def toggle_aspect_ratio(self):
        if self.width_trace_id:
            self.width_var.trace_remove("write", self.width_trace_id)
            self.width_trace_id = None
        if self.height_trace_id:
            self.height_var.trace_remove("write", self.height_trace_id)
            self.height_trace_id = None

        if self.maintain_aspect_ratio.get():
            self.preserve_total_pixels.set(False)
            self.preserve_total_pixels_checkbox.config(state=tk.DISABLED)
            
            self.width_trace_id = self.width_var.trace_add("write", self.on_width_change)
            self.height_trace_id = self.height_var.trace_add("write", self.on_height_change)

            if self.original_image_pil:
                current_width = self.width_var.get()
                if current_width > 0:
                    original_aspect = self.original_image_pil.width / self.original_image_pil.height
                    self.height_var.set(int(current_width / original_aspect))
        else:
            self.preserve_total_pixels_checkbox.config(state=tk.NORMAL)

    def toggle_pixel_preserve(self):
        if self.width_trace_id:
            self.width_var.trace_remove("write", self.width_trace_id)
            self.width_trace_id = None
        if self.height_trace_id:
            self.height_var.trace_remove("write", self.height_trace_id)
            self.height_trace_id = None

        if self.preserve_total_pixels.get():
            self.maintain_aspect_ratio.set(False)
            self.aspect_ratio_checkbox.config(state=tk.DISABLED)
            
            self.width_trace_id = self.width_var.trace_add("write", self.on_width_change_preserve_pixels)
            self.height_trace_id = self.height_var.trace_add("write", self.on_height_change_preserve_pixels)

            if self.original_image_pil:
                current_width = self.width_var.get()
                original_pixel_count = self.original_image_pil.width * self.original_image_pil.height
                if current_width > 0:
                    new_height = int(np.ceil(original_pixel_count / current_width))
                    self.height_var.set(new_height)
        else:
            self.aspect_ratio_checkbox.config(state=tk.NORMAL)
            if self.maintain_aspect_ratio.get():
                self.width_trace_id = self.width_var.trace_add("write", self.on_width_change)
                self.height_trace_id = self.height_var.trace_add("write", self.on_height_change)


    def on_width_change(self, *args):
        if self.maintain_aspect_ratio.get() and self.original_image_pil:
            try:
                current_width = self.width_var.get()
                if current_width > 0:
                    original_aspect = self.original_image_pil.width / self.original_image_pil.height
                    if self.height_trace_id:
                        self.height_var.trace_remove("write", self.height_trace_id)
                    self.height_var.set(int(current_width / original_aspect))
                    self.height_trace_id = self.height_var.trace_add("write", self.on_height_change)
            except tk.TclError:
                pass

    def on_height_change(self, *args):
        if self.maintain_aspect_ratio.get() and self.original_image_pil:
            try:
                current_height = self.height_var.get()
                if current_height > 0:
                    original_aspect = self.original_image_pil.width / self.original_image_pil.height
                    if self.width_trace_id:
                        self.width_var.trace_remove("write", self.width_trace_id)
                    self.width_var.set(int(current_height * original_aspect))
                    self.width_trace_id = self.width_var.trace_add("write", self.on_width_change)
            except tk.TclError:
                pass

    def on_width_change_preserve_pixels(self, *args):
        if self.preserve_total_pixels.get() and self.original_image_pil:
            try:
                current_width = self.width_var.get()
                original_pixel_count = self.original_image_pil.width * self.original_image_pil.height
                if current_width > 0:
                    new_height = int(np.ceil(original_pixel_count / current_width))
                    if self.height_trace_id:
                        self.height_var.trace_remove("write", self.height_trace_id)
                    self.height_var.set(new_height)
                    self.height_trace_id = self.height_var.trace_add("write", self.on_height_change_preserve_pixels)
            except tk.TclError:
                pass

    def on_height_change_preserve_pixels(self, *args):
        if self.preserve_total_pixels.get() and self.original_image_pil:
            try:
                current_height = self.height_var.get()
                original_pixel_count = self.original_image_pil.width * self.original_image_pil.height
                if current_height > 0:
                    new_width = int(np.ceil(original_pixel_count / current_height))
                    if self.width_trace_id:
                        self.width_var.trace_remove("write", self.width_trace_id)
                    self.width_var.set(new_width)
                    self.width_trace_id = self.width_var.trace_add("write", self.on_width_change_preserve_pixels)
            except tk.TclError:
                pass


    def apply_resize(self):
        if self.original_image_np is None:
            messagebox.showwarning("No Image", "Please load an image first.")
            return

        target_width = self.width_var.get()
        target_height = self.height_var.get()

        if target_width <= 0 or target_height <= 0:
            messagebox.showerror("Invalid Dimensions", "Width and Height must be positive integers.")
            return

        try:
            processed_image_np = None

            if self.preserve_total_pixels.get():
                print(f"Applying 'Preserve Total Pixels' mode. Target W:{target_width}, Target H:{target_height}")
                
                processed_image_np = perform_seam_carving(self.original_image_np, target_width, target_height)
                
                if processed_image_np.shape[0] < target_height:
                    print(f"Adding white padding from {processed_image_np.shape[0]} to {target_height}")
                    padded_img_np = np.full((target_height, target_width, 3), 255, dtype=np.uint8)
                    padded_img_np[0:processed_image_np.shape[0], 0:processed_image_np.shape[1]] = processed_image_np
                    processed_image_np = padded_img_np
                
                self.width_var.set(processed_image_np.shape[1])
                self.height_var.set(processed_image_np.shape[0])

            elif self.maintain_aspect_ratio.get():
                print(f"Applying 'Maintain Aspect Ratio' mode. Target W:{target_width}, Target H:{target_height}")
                processed_image_np = np.array(self.original_image_pil.resize((target_width, target_height), Image.LANCZOS))
            
            else:
                print(f"Applying Direct Resize mode. Target W:{target_width}, Target H:{target_height}")
                processed_image_np = perform_seam_carving(self.original_image_np, target_width, target_height)

            self.display_image_pil = Image.fromarray(processed_image_np)
            self.display_image(self.display_image_pil)
            self.save_button.config(state=tk.NORMAL) # Enable save button after successful resize
            messagebox.showinfo("Resize Complete", f"Image resized to {self.display_image_pil.width}x{self.display_image_pil.height} pixels.")

        except Exception as e:
            messagebox.showerror("Resize Error", f"An error occurred during resize: {e}")
            import traceback
            traceback.print_exc()

    def on_canvas_resize(self, event):
        if self.display_image_pil:
            self.display_image(self.display_image_pil)

# --- Main execution ---
if __name__ == "__main__":
    root = tk.Tk()
    
    if not check_and_install_packages(REQUIRED_PACKAGES_MAP):
        root.destroy()
        sys.exit(1)

    app = ImageResizerApp(root)
    app.canvas.bind("<Configure>", app.on_canvas_resize)
    
    root.mainloop()