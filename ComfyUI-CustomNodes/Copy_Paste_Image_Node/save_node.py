import os
import torch
import folder_paths
from nodes import SaveImage
from datetime import datetime

class EnhancedSaveImage(SaveImage):
    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(s):
        return {"required": 
                    {"images": ("IMAGE", ),
                     "filename_prefix": ("STRING", {"default": "%date:yyyy%/%date:yyyy-MM-dd%/ComfyUI_%date:yyyy-MM-dd-hhmmss%"})},
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }

    RETURN_TYPES = ()
    FUNCTION = "save_images_enhanced"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def save_images_enhanced(self, images, filename_prefix, prompt=None, extra_pnginfo=None):
        # 1. Manually replace the %date% tokens to avoid the WinError 123
        now = datetime.now()
        filename_prefix = filename_prefix.replace("%date:yyyy%", now.strftime("%Y"))
        filename_prefix = filename_prefix.replace("%date:yyyy-MM-dd%", now.strftime("%Y-%m-%d"))
        filename_prefix = filename_prefix.replace("%date:yyyy-MM-dd-hhmmss%", now.strftime("%Y-%m-%d-%H%M%S"))

        # 2. Get the official output directory
        output_dir = folder_paths.get_output_directory()
        full_path = os.path.join(output_dir, filename_prefix)
        
        # 3. Ensure the directories exist before saving
        dirname = os.path.dirname(full_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

        # 4. Now that the path is "real", let the standard saver do its work
        return self.save_images(images, filename_prefix, prompt, extra_pnginfo)