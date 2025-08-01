import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2 # Required for seam_carving
import seam_carving as sc
import sys
import subprocess
import os
import traceback
# from scipy.ndimage import shift # REMOVED: Reverting from scipy.ndimage.shift for offset due to misunderstanding of its "wrap" mode for this specific use case.

# --- Package Installation Check ---
REQUIRED_PACKAGES_MAP = {
    "opencv-python": "cv2",
    "numpy": "numpy",
    "Pillow": "PIL",
    "seam_carving": "seam_carving",
    # "scipy": "scipy" # Removed from required packages for now, unless needed elsewhere
}

def check_and_install_packages(packages_map):
    """
    Checks if required Python packages are installed and offers to install them if missing.
    Returns True if all packages are available (or successfully installed), False otherwise.
    """
    missing_packages_for_install = []
    
    for install_name, import_name in packages_map.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages_for_install.append(install_name)

    if missing_packages_for_install:
        response = messagebox.askyesno("Missing Packages",
                            "The following packages are missing:\n" +
                            "\n".join([f"- {pkg_name}" for pkg_name in missing_packages_for_install]) +
                            "\n\nWould you like to install them? This might require an internet connection.")

        if response:
            try:
                print(f"Attempting to install: {missing_packages_for_install} with --break-system-packages")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages"] + missing_packages_for_install)
                messagebox.showinfo("Installation Complete", "Packages installed successfully! Please restart the application.")
                return False # Indicate that restart is needed
            except subprocess.CalledCalledProcessError as e:
                print(f"First install attempt failed, trying without --break-system-packages. Error: {e}")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages_for_install)
                    messagebox.showinfo("Installation Complete", "Packages installed successfully! Please restart the application.")
                    return False # Indicate that restart is needed
                except subprocess.CalledProcessError as e:
                    messagebox.showerror("Installation Error", f"Error installing packages: {e}\nPlease try installing them manually: pip install " + " ".join(missing_packages_for_install))
                    return False
                except Exception as e:
                    messagebox.showerror("Installation Error", f"An unexpected error occurred during installation: {e}\nPlease try installing them manually: pip install " + " ".join(missing_packages_for_install))
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
    """
    Performs seam carving to resize the image while attempting to preserve content.
    """
    current_height, current_width, _ = image_np.shape

    if target_width != current_width:
        print(f"Seam Carving: Adjusting width from {current_width} to {target_width}...")
        image_np = sc.resize(image_np, size=(target_width, current_height), energy_mode="backward", order="width-first")
        current_height, current_width, _ = image_np.shape # Update dimensions after width resize

    if target_height != current_height:
        print(f"Seam Carving: Adjusting height from {current_height} to {target_height}...")
        image_np = sc.resize(image_np, size=(target_width, target_height), energy_mode="backward", order="height-first")
    
    return image_np

# --- Pixel Wrapping Logic ---
def pixel_wrap_image(image_np, target_width):
    """
    Reshapes a 2D image into a 1D pixel stream and then wraps it into a new 2D image
    of the specified target_width, padding with white if necessary.
    """
    if target_width <= 0:
        raise ValueError("Target width must be greater than 0 for pixel wrapping.")

    original_height, original_width, channels = image_np.shape
    total_pixels = original_height * original_width

    flattened_pixels = image_np.reshape(-1, channels) # Convert 2D to 1D stream

    # Calculate new height based on target width
    new_height = int(np.ceil(total_pixels / target_width))

    print(f"Pixel Wrapping: Original total pixels: {total_pixels}")
    print(f"Pixel Wrapping: New dimensions: {target_width}x{new_height}")

    # Create a new NumPy array for the wrapped image, initialized to white (255)
    # This automatically handles padding if total_pixels is not a perfect multiple
    wrapped_image_np = np.full((new_height * target_width, channels), 255, dtype=np.uint8)
    
    # Copy the flattened pixels into the new array
    num_pixels_to_copy = min(total_pixels, new_height * target_width) # Should be just total_pixels
    wrapped_image_np[:num_pixels_to_copy] = flattened_pixels[:num_pixels_to_copy]

    # Reshape the 1D array back into the new 2D dimensions
    final_image = wrapped_image_np.reshape((new_height, target_width, channels))
    
    return final_image

def apply_fractional_pixel_stream_shift(image_np, x_offset, y_offset):
    """
    Applies a fractional pixel offset to a 2D image *as if it were a 1D pixel stream*,
    and then re-wraps it. This simulates the "text flow" shift.
    
    Args:
        image_np (np.array): The original 2D image as a NumPy array (H, W, C).
        x_offset (float): Fractional horizontal offset (0.0 to 1.0).
        y_offset (float): Fractional vertical offset (0.0 to 1.0).
                           For pixel stream, Y offset means shifting entire "rows" of the stream.
    
    Returns:
        np.array: The image with the fractional pixel stream offset applied,
                  reshaped to its original dimensions.
    """
    if x_offset == 0.0 and y_offset == 0.0:
        return image_np # No offset, return original

    original_height, original_width, channels = image_np.shape
    total_pixels = original_height * original_width
    
    # Flatten the image into a 1D pixel stream
    flattened_pixels = image_np.reshape(-1, channels).astype(np.float32) # Convert to float for interpolation

    # Calculate total fractional shift in terms of 1D pixels
    # A positive x_offset shifts content right (so the "start" of the stream shifts left)
    # A positive y_offset shifts content down (so the "start" of the stream shifts up, effectively earlier in the stream)
    # Combined, this is a linear shift on the flattened array.
    # The actual shift amount for the 1D array needs to be relative to its total length.
    
    # Let's consider a simpler interpretation: The "offset" for a pixel stream
    # means that the "first pixel" of the display moves to a new (x,y) location,
    # and subsequent pixels wrap from there.
    # This is handled by the `pixel_wrap_image` function's target_width.
    
    # For *fractional* offset on the already established pixel flow, we need to
    # adjust the stream itself.
    
    # Calculate effective 1D shift. We assume x_offset and y_offset are
    # relative to the original image's dimensions.
    # A full X offset of 1.0 means shifting by 1 pixel horizontally.
    # A full Y offset of 1.0 means shifting by 1 pixel vertically.
    # In a 1D stream, a 1-pixel horizontal shift is 1 pixel.
    # A 1-pixel vertical shift is `original_width` pixels.
    
    # Total 1D pixel shift
    # Positive shift_1d means content moves to the right/down in the 1D stream.
    # So, if x_offset is 0.5, we want to shift the content right by 0.5 pixels.
    # If y_offset is 0.5, we want to shift content down by 0.5 rows.
    
    # The `np.roll` function shifts elements. A positive shift means elements move
    # from left to right (or top to bottom).
    
    # The fractional part needs interpolation.
    
    # Total fractional shift along the 1D stream.
    # The X-offset is a direct pixel shift.
    # The Y-offset needs to be scaled by the original image's width to represent
    # a shift in terms of 1D pixels.
    
    # For wrapping:
    # Let's consider the new starting point of the original stream within a "padded" stream.
    # A positive x_offset means the content moves right, so the *sampling origin* moves left.
    # A positive y_offset means the content moves down, so the *sampling origin* moves up (earlier in stream).
    
    # Calculate the total fractional shift for the 1D stream
    # A full X offset of 1.0 moves by 1 pixel.
    # A full Y offset of 1.0 moves by `original_width` pixels.
    
    total_1d_shift_fractional = x_offset + (y_offset * original_width)
    
    # If the shift is negative, normalize it to be positive within the total_pixels range
    # e.g., -0.5 shift on a 100-pixel array is equivalent to a 99.5 shift.
    # It's more robust to work with positive shifts modulo length.
    total_1d_shift_fractional = total_1d_shift_fractional % total_pixels

    if total_1d_shift_fractional < 0:
        total_1d_shift_fractional += total_pixels

    integer_shift = int(total_1d_shift_fractional)
    fractional_part = total_1d_shift_fractional - integer_shift

    # Perform integer shift using np.roll (wrap mode built-in)
    shifted_pixels_int = np.roll(flattened_pixels, integer_shift, axis=0)

    if fractional_part == 0:
        return shifted_pixels_int.reshape((original_height, original_width, channels)).astype(np.uint8)

    # Perform fractional interpolation
    # We need to blend the integer-shifted array with another array shifted by integer_shift + 1
    
    # shifted_pixels_int corresponds to the floor(total_1d_shift_fractional)
    # shifted_pixels_int_plus_1 corresponds to ceil(total_1d_shift_fractional)
    shifted_pixels_int_plus_1 = np.roll(flattened_pixels, integer_shift + 1, axis=0)

    # Linear interpolation: result = (1 - f) * value_at_floor + f * value_at_ceil
    interpolated_pixels = (1 - fractional_part) * shifted_pixels_int + fractional_part * shifted_pixels_int_plus_1
    
    # Clip and convert back to uint8
    interpolated_pixels = np.clip(interpolated_pixels, 0, 255).astype(np.uint8)

    # Reshape back to original 2D dimensions for further processing
    # Note: This function only applies the offset. The final reshape to target_width
    # will happen later in `_process_image` (via pixel_wrap_image).
    return interpolated_pixels.reshape((original_height, original_width, channels))


class ImageResizerApp:
    def __init__(self, master):
        self.master = master
        master.title("Image Resizer (Seam Carving / Pixel Wrap GUI)")

        self.original_image_pil = None # Stores the PIL image of the initially loaded image
        self.original_image_np = None  # Stores the NumPy array of the initially loaded image
        self.display_image_pil = None  # Stores the PIL image currently displayed on canvas

        # Variables for fractional pixel offset (new feature)
        self.x_offset_var = tk.DoubleVar(value=0.0)
        self.y_offset_var = tk.DoubleVar(value=0.0)

        # Trace IDs for spinbox synchronization, allowing removal
        self.width_trace_id = None
        self.height_trace_id = None

        self.create_widgets()
        self.update_info_display()

        # Set "Pixel Wrap" as default mode on startup
        self.pixel_wrap_mode.set(True) 
        self._toggle_mode() # Initialize GUI state based on default mode

    def create_widgets(self):
        # --- Controls Frame ---
        control_frame = ttk.LabelFrame(self.master, text="Controls", padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.load_button = ttk.Button(control_frame, text="Load Image", command=self.load_image)
        self.load_button.grid(row=0, column=0, columnspan=2, pady=5)

        self.save_button = ttk.Button(control_frame, text="Save Image As...", command=self.save_image)
        self.save_button.grid(row=0, column=2, columnspan=2, pady=5, padx=10)
        self.save_button.config(state=tk.DISABLED) # Disabled until an image is loaded

        # --- Dimensions Spinboxes ---
        ttk.Label(control_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.width_var = tk.IntVar(value=0)
        self.width_spinbox = ttk.Spinbox(control_frame, from_=1, to_=4000, textvariable=self.width_var, width=8)
        self.width_spinbox.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(control_frame, text="Height:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.height_var = tk.IntVar(value=0)
        self.height_spinbox = ttk.Spinbox(control_frame, from_=1, to_=4000, textvariable=self.height_var, width=8)
        self.height_spinbox.grid(row=2, column=1, sticky=tk.W, pady=2)

        # --- Resizing Mode Checkboxes (Radio-button like behavior enforced by _toggle_mode) ---
        self.maintain_aspect_ratio = tk.BooleanVar(value=False)
        self.aspect_ratio_checkbox = ttk.Checkbutton(control_frame, text="Maintain Aspect Ratio (Scale)", variable=self.maintain_aspect_ratio, command=self._toggle_mode)
        self.aspect_ratio_checkbox.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.preserve_total_pixels = tk.BooleanVar(value=False)
        self.preserve_total_pixels_checkbox = ttk.Checkbutton(control_frame, text="Preserve Total Pixels (Seam Carve)", variable=self.preserve_total_pixels, command=self._toggle_mode)
        self.preserve_total_pixels_checkbox.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.pixel_wrap_mode = tk.BooleanVar(value=False)
        self.pixel_wrap_checkbox = ttk.Checkbutton(control_frame, text="Pixel Wrap (Text Flow)", variable=self.pixel_wrap_mode, command=self._toggle_mode)
        self.pixel_wrap_checkbox.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # --- Realtime Update Checkbox ---
        self.realtime_update_enabled = tk.BooleanVar(value=False) 
        self.realtime_checkbox = ttk.Checkbutton(control_frame, text="Realtime Update", variable=self.realtime_update_enabled, command=self._toggle_realtime)
        self.realtime_checkbox.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # --- Apply Button ---
        self.apply_button = ttk.Button(control_frame, text="Apply Resize", command=self.apply_resize)
        self.apply_button.grid(row=7, column=0, columnspan=2, pady=10)
        self.apply_button.config(state=tk.DISABLED)

        # --- New: Fine Alignment / Pixel Offset Section ---
        align_frame = ttk.LabelFrame(self.master, text="Fine Pixel Offset (Interpolated)", padding="10")
        align_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(align_frame, text="X Offset:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.x_offset_spinbox = ttk.Spinbox(align_frame, from_=-1.0, to_=1.0, textvariable=self.x_offset_var, width=6, format="%.2f", increment=0.05,
                                             command=self._on_offset_change) # Calls update function on change
        self.x_offset_spinbox.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.x_offset_spinbox.config(state=tk.DISABLED) # Initially disabled

        ttk.Label(align_frame, text="Y Offset:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.y_offset_spinbox = ttk.Spinbox(align_frame, from_=-1.0, to_=1.0, textvariable=self.y_offset_var, width=6, format="%.2f", increment=0.05,
                                             command=self._on_offset_change) # Calls update function on change
        self.y_offset_spinbox.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.y_offset_spinbox.config(state=tk.DISABLED) # Initially disabled

        # --- Image Info Display Frame ---
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

        # --- Canvas for Image Display ---
        self.canvas_frame = ttk.Frame(self.master, borderwidth=2, relief="groove")
        self.canvas_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg="gray", borderwidth=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas_image_id = None # To keep track of the image drawn on canvas

    def _remove_all_traces(self):
        """Removes all currently active traces on IntVar/DoubleVar to prevent conflicts."""
        if self.width_trace_id:
            self.width_var.trace_remove("write", self.width_trace_id)
            self.width_trace_id = None
        if self.height_trace_id:
            self.height_var.trace_remove("write", self.height_trace_id)
            self.height_trace_id = None

    def _add_traces_for_current_mode(self):
        """Adds traces to dimension variables based on the currently selected resize mode and realtime setting."""
        self._remove_all_traces() # Always start clean by removing old traces

        if self.realtime_update_enabled.get():
            # If realtime is on, changes in dimensions trigger a full image update
            if self.maintain_aspect_ratio.get():
                self.width_trace_id = self.width_var.trace_add("write", self._on_spinbox_change_realtime_aspect)
                self.height_trace_id = self.height_var.trace_add("write", self._on_spinbox_change_realtime_aspect)
            elif self.preserve_total_pixels.get():
                self.width_trace_id = self.width_var.trace_add("write", self._on_spinbox_change_realtime_preserve)
                self.height_trace_id = self.height_var.trace_add("write", self._on_spinbox_change_realtime_preserve)
            elif self.pixel_wrap_mode.get():
                self.width_trace_id = self.width_var.trace_add("write", self._on_spinbox_change_realtime_pixel_wrap)
                # Height spinbox is disabled in pixel wrap mode, so no trace needed for user input
        else:
            # If realtime is off, only synchronize spinboxes, actual resize is on "Apply"
            if self.maintain_aspect_ratio.get():
                self.width_trace_id = self.width_var.trace_add("write", self._sync_spinboxes_aspect_width)
                self.height_trace_id = self.height_var.trace_add("write", self._sync_spinboxes_aspect_height)
            elif self.preserve_total_pixels.get():
                self.width_trace_id = self.width_var.trace_add("write", self._sync_spinboxes_preserve_width)
                self.height_trace_id = self.height_var.trace_add("write", self._sync_spinboxes_preserve_height)
            elif self.pixel_wrap_mode.get():
                self.width_trace_id = self.width_var.trace_add("write", self._sync_spinboxes_pixel_wrap_width)
                # Height spinbox is disabled, so no trace for user input

    def _toggle_mode(self):
        """
        Handles changes in the resize mode checkboxes, ensuring only one mode is active
        and updating the GUI elements accordingly.
        """
        # Determine which checkbox triggered the call or which is currently active
        clicked_mode = None
        if self.maintain_aspect_ratio.get():
            clicked_mode = 'aspect'
        elif self.preserve_total_pixels.get():
            clicked_mode = 'preserve'
        elif self.pixel_wrap_mode.get():
            clicked_mode = 'pixel_wrap'
        
        # If no mode is active (e.g., initial startup or user unchecks last one), default to Pixel Wrap
        if clicked_mode is None:
            self.pixel_wrap_mode.set(True)
            clicked_mode = 'pixel_wrap'

        # Deactivate all others except the clicked/determined one
        if clicked_mode != 'aspect': self.maintain_aspect_ratio.set(False)
        if clicked_mode != 'preserve': self.preserve_total_pixels.set(False)
        if clicked_mode != 'pixel_wrap': self.pixel_wrap_mode.set(False)
            
        # Configure spinbox states based on the active mode and whether an image is loaded
        if clicked_mode == 'pixel_wrap':
            self.width_spinbox.config(state=tk.NORMAL if self.original_image_pil else tk.DISABLED)
            self.height_spinbox.config(state=tk.DISABLED) # Height is derived in pixel wrap mode
        elif self.original_image_pil is not None:
            self.width_spinbox.config(state=tk.NORMAL)
            self.height_spinbox.config(state=tk.NORMAL)
        else: # No image loaded, disable all dimension controls
            self.width_spinbox.config(state=tk.DISABLED)
            self.height_spinbox.config(state=tk.DISABLED)

        # Trigger initial numerical sync for the selected mode
        if clicked_mode == 'aspect':
            self._sync_spinboxes_aspect_width()
        elif clicked_mode == 'preserve':
            self._sync_spinboxes_preserve_width()
        elif clicked_mode == 'pixel_wrap':
            self._sync_spinboxes_pixel_wrap_width()
            
        self._add_traces_for_current_mode() # Set up new traces based on the final state

    def _toggle_realtime(self):
        """Handles changes in the 'Realtime Update' checkbox."""
        if self.original_image_np is not None: 
            self._add_traces_for_current_mode() # Re-add traces based on new realtime state
            if self.realtime_update_enabled.get():
                self._process_and_display_current_values() # Perform an immediate update

    def _on_offset_change(self):
        """Called when the X or Y offset spinbox value changes."""
        # Only trigger a full image update if realtime is enabled
        if self.realtime_update_enabled.get() and self.original_image_np is not None:
            try:
                # Attempt to get values to ensure they are valid numbers
                _ = self.x_offset_var.get()
                _ = self.y_offset_var.get()
                self._process_and_display_current_values()
            except tk.TclError:
                print("Invalid value for offset. Please enter a number.")
                # Optionally, reset to last valid value or 0.0

    def load_image(self):
        """Loads an image from a file dialog."""
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if file_path:
            try:
                self.original_image_pil = Image.open(file_path).convert("RGB") # Ensure RGB format
                self.original_image_np = np.array(self.original_image_pil)
                
                # Set initial dimensions to original image's dimensions
                self.width_var.set(self.original_image_pil.width)
                self.height_var.set(self.original_image_pil.height)
                
                # Reset fractional offsets when a new image is loaded
                self.x_offset_var.set(0.0)
                self.y_offset_var.set(0.0)

                # IMPORTANT: Initial display of the original image should also go through _process_and_display_current_values
                # This ensures the image is always displayed after potential offset application (even if 0,0)
                self._process_and_display_current_values() 

                self.update_info_display() # Update info labels
                self.apply_button.config(state=tk.NORMAL) # Enable apply button
                self.save_button.config(state=tk.NORMAL) # Enable save button
                self.x_offset_spinbox.config(state=tk.NORMAL) # Enable offset controls
                self.y_offset_spinbox.config(state=tk.NORMAL)
                
                self._toggle_mode() # Update spinbox states based on loaded image

                print(f"Image Loaded: {os.path.basename(file_path)} (Original: {self.original_image_pil.width}x{self.original_image_pil.height})")

            except Exception as e:
                print(f"Error loading image: {e}")
                traceback.print_exc() # Print full traceback for debugging
                # Reset state on error
                self.original_image_pil = None
                self.original_image_np = None
                self.apply_button.config(state=tk.DISABLED)
                self.save_button.config(state=tk.DISABLED)
                self.width_spinbox.config(state=tk.DISABLED)
                self.height_spinbox.config(state=tk.DISABLED)
                self.x_offset_spinbox.config(state=tk.DISABLED)
                self.y_offset_spinbox.config(state=tk.DISABLED)

    def save_image(self):
        """Saves the currently displayed image."""
        if self.display_image_pil is None:
            messagebox.showinfo("Save Image", "No image to save.")
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
                self.display_image_pil.save(file_path)
                messagebox.showinfo("Save Image", f"Image saved to: {os.path.basename(file_path)}")
                print(f"Image saved to: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save image: {e}")
                print(f"Failed to save image: {e}")
                traceback.print_exc()

    def display_image(self, pil_image):
        """Displays a PIL image on the Tkinter canvas, scaling it to fit."""
        if pil_image:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Ensure canvas has actual dimensions if it hasn't been rendered yet
            if canvas_width == 0 or canvas_height == 0:
                self.canvas.update_idletasks() # Force update
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                # Fallback if canvas still has no dimensions (e.g., very early in startup)
                if canvas_width == 0 or canvas_height == 0:
                    canvas_width = 800
                    canvas_height = 600

            img_width, img_height = pil_image.size
            
            # Calculate scaling to fit image within canvas while maintaining aspect ratio
            img_aspect = img_width / img_height
            canvas_aspect = canvas_width / canvas_height

            if img_aspect > canvas_aspect:
                new_width = canvas_width
                new_height = int(new_width / img_aspect)
            else:
                new_height = canvas_height
                new_width = int(new_height * img_aspect)

            # Prevent extremely small resize if canvas is tiny
            if new_width < 10 or new_height < 10:
                new_width, new_height = img_width, img_height # Don't scale if it makes it too small

            try:
                # Resize image for display using high-quality LANCZOS filter
                display_img_resized = pil_image.resize((max(1, new_width), max(1, new_height)), Image.LANCZOS)
                self.display_image_tk = ImageTk.PhotoImage(display_img_resized)
                
                # Clear previous image on canvas and draw new one
                if self.canvas_image_id:
                    self.canvas.delete(self.canvas_image_id)
                
                # Center the image on the canvas
                x_center = canvas_width / 2
                y_center = canvas_height / 2
                self.canvas_image_id = self.canvas.create_image(x_center, y_center, image=self.display_image_tk, anchor=tk.CENTER)
                
                self.display_image_pil = pil_image # Store the actual (unscaled) image being displayed
                self.update_info_display()

            except Exception as e:
                print(f"Error displaying image: {e}")
                traceback.print_exc()
                self.display_image_pil = None
        else:
            # Clear canvas if no image to display
            if self.canvas_image_id:
                self.canvas.delete(self.canvas_image_id)
            self.display_image_pil = None
            self.update_info_display()

    def update_info_display(self):
        """Updates the labels displaying image dimensions and pixel counts."""
        if self.original_image_pil is not None:
            original_w, original_h = self.original_image_pil.size
            original_pixels = original_w * original_h
            self.original_dims_label.config(text=f"Original Dims: {original_w}x{original_h} pixels")
            self.original_pixel_count_label.config(text=f"Original Pixels: {original_pixels}")
        else:
            self.original_dims_label.config(text="Original Dims: N/A")
            self.original_pixel_count_label.config(text="Original Pixels: N/A")

        if self.display_image_pil is not None:
            current_w, current_h = self.display_image_pil.size
            current_pixels = current_w * current_h
            self.current_dims_label.config(text=f"Current Dims: {current_w}x{current_h} pixels")
            self.current_pixel_count_label.config(text=f"Current Pixels: {current_pixels}")
        else:
            self.current_dims_label.config(text="Current Dims: N/A")
            self.current_pixel_count_label.config(text="Current Pixels: N/A")

    # --- Spinbox Synchronization Functions (for non-realtime or initial sync) ---
    def _sync_spinboxes_aspect_width(self, *args):
        """Synchronizes height with width in aspect ratio mode."""
        if self.original_image_pil is not None:
            try:
                current_width = self.width_var.get()
                if current_width > 0:
                    original_aspect = self.original_image_pil.width / self.original_image_pil.height
                    self.height_var.set(int(current_width / original_aspect))
            except tk.TclError: # Handle invalid input in spinbox
                pass

    def _sync_spinboxes_aspect_height(self, *args):
        """Synchronizes width with height in aspect ratio mode."""
        if self.original_image_pil is not None:
            try:
                current_height = self.height_var.get()
                if current_height > 0:
                    original_aspect = self.original_image_pil.width / self.original_image_pil.height
                    self.width_var.set(int(current_height * original_aspect))
            except tk.TclError:
                pass

    def _sync_spinboxes_preserve_width(self, *args):
        """Synchronizes height with width in preserve total pixels mode."""
        if self.original_image_pil is not None:
            try:
                current_width = self.width_var.get()
                original_pixel_count = self.original_image_pil.width * self.original_image_pil.height
                if current_width > 0:
                    new_height = int(np.ceil(original_pixel_count / current_width))
                    self.height_var.set(new_height)
            except tk.TclError:
                pass

    def _sync_spinboxes_preserve_height(self, *args):
        """Synchronizes width with height in preserve total pixels mode."""
        if self.original_image_pil is not None:
            try:
                current_height = self.height_var.get()
                original_pixel_count = self.original_image_pil.width * self.original_image_pil.height
                if current_height > 0:
                    new_width = int(np.ceil(original_pixel_count / current_height))
                    self.width_var.set(new_width)
            except tk.TclError:
                pass

    def _sync_spinboxes_pixel_wrap_width(self, *args):
        """Synchronizes height with width in pixel wrap mode."""
        if self.original_image_pil is not None:
            try:
                current_width = self.width_var.get()
                original_pixel_count = self.original_image_pil.width * self.original_image_pil.height
                if current_width > 0:
                    new_height = int(np.ceil(original_pixel_count / current_width))
                    self.height_var.set(new_height)
            except tk.TclError:
                pass
    # --- End Spinbox Synchronization Functions ---

    # --- Realtime Spinbox Change Handlers (Sync + Image Redraw) ---
    def _on_spinbox_change_realtime_aspect(self, *args):
        """Handles realtime updates for aspect ratio mode."""
        if self.original_image_np is None: return

        # Temporarily remove traces to prevent infinite recursion during sync
        self._remove_all_traces() 
        self._sync_spinboxes_aspect_width()
        self._sync_spinboxes_aspect_height()
        # Re-add traces
        self.width_trace_id = self.width_var.trace_add("write", self._on_spinbox_change_realtime_aspect)
        self.height_trace_id = self.height_var.trace_add("write", self._on_spinbox_change_realtime_aspect)
        
        if self.realtime_update_enabled.get():
            self._process_and_display_current_values()

    def _on_spinbox_change_realtime_preserve(self, *args):
        """Handles realtime updates for preserve total pixels mode."""
        if self.original_image_np is None: return

        self._remove_all_traces() 
        self._sync_spinboxes_preserve_width()
        self._sync_spinboxes_preserve_height()
        
        self.width_trace_id = self.width_var.trace_add("write", self._on_spinbox_change_realtime_preserve)
        self.height_trace_id = self.height_var.trace_add("write", self._on_spinbox_change_realtime_preserve)

        if self.realtime_update_enabled.get():
            self._process_and_display_current_values()

    def _on_spinbox_change_realtime_pixel_wrap(self, *args):
        """Handles realtime updates for pixel wrap mode."""
        if self.original_image_np is None: return

        self._sync_spinboxes_pixel_wrap_width() # Only width changes height in this mode
        if self.realtime_update_enabled.get():
            self._process_and_display_current_values()
    # --- End Realtime Spinbox Change Handlers ---

    def _process_image(self, base_image_np, target_width, target_height):
        """
        Processes the image based on the currently active mode and given target dimensions.
        Takes a base NumPy array (which has already had the fractional offset applied) as input.
        Returns the processed NumPy array.
        """
        if base_image_np is None:
            print("Error: No base image to process.")
            return None
        
        # Ensure valid dimensions
        if target_width <= 0 or target_height <= 0:
            print(f"Error: Invalid dimensions ({target_width}x{target_height}) for processing.")
            # If dimensions are invalid, return the current base image (with offset, if any)
            return base_image_np 

        processed_image_np = None
        
        if self.pixel_wrap_mode.get():
            print(f"Processing 'Pixel Wrap' mode. Target W:{target_width}, Calculated H:{target_height}")
            processed_image_np = pixel_wrap_image(base_image_np, target_width)
            
        elif self.preserve_total_pixels.get():
            print(f"Processing 'Preserve Total Pixels' mode. Target W:{target_width}, Target H:{target_height}")
            processed_image_np = perform_seam_carving(base_image_np, target_width, target_height)
            
            # Add white padding if seam carving results in an image smaller than target_height
            if processed_image_np.shape[0] < target_height:
                print(f"Adding white padding from {processed_image_np.shape[0]} to {target_height}")
                padded_img_np = np.full((target_height, target_width, 3), 255, dtype=np.uint8)
                copy_height = min(processed_image_np.shape[0], target_height)
                copy_width = min(processed_image_np.shape[1], target_width)
                padded_img_np[0:copy_height, 0:copy_width] = processed_image_np[0:copy_height, 0:copy_width]
                processed_image_np = padded_img_np

        elif self.maintain_aspect_ratio.get():
            print(f"Processing 'Maintain Aspect Ratio' mode. Target W:{target_width}, Target H:{target_height}")
            base_image_pil_for_resize = Image.fromarray(base_image_np) 
            processed_image_np = np.array(base_image_pil_for_resize.resize((target_width, target_height), Image.LANCZOS))
        
        return processed_image_np


    def _process_and_display_current_values(self):
        """
        Retrieves current spinbox values, applies the fractional pixel offset,
        processes the image using the selected mode, and displays the result.
        """
        if self.original_image_np is None:
            print("Warning: No image loaded for processing.")
            return

        target_width = self.width_var.get()
        target_height = self.height_var.get()

        try:
            x_offset = self.x_offset_var.get()
            y_offset = self.y_offset_var.get()

            np_image_after_offset = self.original_image_np
            
            # --- Apply Fractional Pixel Offset with Wrapping Logic (ONLY for Pixel Wrap Mode) ---
            if self.pixel_wrap_mode.get() and (x_offset != 0.0 or y_offset != 0.0):
                print(f"Applying fractional pixel stream offset: X={x_offset:.2f}, Y={y_offset:.2f}")
                # The `apply_fractional_pixel_stream_shift` function will take care of
                # flattening, shifting, interpolating, and reshaping back to original DIMS.
                # The `pixel_wrap_image` function (called by _process_image) will then
                # re-wrap this potentially offset original-size image to the new target_width.
                np_image_after_offset = apply_fractional_pixel_stream_shift(
                    self.original_image_np, x_offset, y_offset
                )
            elif x_offset != 0.0 or y_offset != 0.0:
                 # Standard (non-wrapping) affine offset for other modes
                print(f"Applying STANDARD (non-wrapping) pixel offset: X={x_offset:.2f}, Y={y_offset:.2f}")
                pil_image_for_processing = Image.fromarray(self.original_image_np)
                pil_image_after_offset = pil_image_for_processing.transform(
                    pil_image_for_processing.size, 
                    Image.AFFINE,
                    (1, 0, x_offset, 0, 1, y_offset), # Standard affine translation
                    resample=Image.BICUBIC
                )
                np_image_after_offset = np.array(pil_image_after_offset)
            # Else: np_image_after_offset remains self.original_image_np (no offset applied)

            # --- Step 2: Process Image based on selected mode, passing the OFFSETTED NumPy array ---
            processed_image_np = self._process_image(np_image_after_offset, target_width, target_height)
            
            # --- Step 3: Display the Result ---
            if processed_image_np is not None:
                self.display_image_pil = Image.fromarray(processed_image_np)
                self.display_image(self.display_image_pil)
        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during image processing: {e}")
            print(f"Error during image processing for display: {e}")
            traceback.print_exc()

    def apply_resize(self):
        """Called when the 'Apply Resize' button is clicked."""
        self._process_and_display_current_values()
        if self.display_image_pil is not None:
            self.save_button.config(state=tk.NORMAL)
            print(f"Manual Resize Applied: Image is now {self.display_image_pil.width}x{self.display_image_pil.height} pixels.")
        else:
            print("Manual Resize failed or no image processed.")


    def on_canvas_resize(self, event):
        """Callback for when the canvas is resized, to redraw the image."""
        if self.display_image_pil is not None:
            self.display_image(self.display_image_pil)

# --- Main execution ---
if __name__ == "__main__":
    root = tk.Tk()
    
    # Check and install necessary packages before running the app
    if not check_and_install_packages(REQUIRED_PACKAGES_MAP):
        root.destroy() # Close application if package installation failed or was skipped
        sys.exit(1)

    app = ImageResizerApp(root)
    app.canvas.bind("<Configure>", app.on_canvas_resize)
    
    root.mainloop()