import torch
import numpy as np
from PIL import Image
import torch.nn.functional as F

class SmartResizeAndPad:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "target_side_length": ("INT", {"default": 512, "min": 16, "max": 8192, "step": 16}),
                "multiple_of": ("INT", {"default": 16, "min": 1, "max": 128, "step": 1}),
                "fit_mode": (["shortest", "longest"],),
                "add_black_bars": ("BOOLEAN", {"default": True}),
                "interpolation": ([
                    "AUTO_Bicubic_Lanczos",
                    "AUTO_Bicubic_Area",
                    "Bicubic (Upscale)",
                    "Area (Downscale)",
                    "Lanczos (Downscale Sharper)",
                    "Nearest (pixel art)",
                    "Nearest Exact (pixel art)",
                    "Bilinear"
                ], {"default": "AUTO_Bicubic_Lanczos"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "width", "height")
    FUNCTION = "resize_and_pad"
    CATEGORY = "utils/image"

    def resize_and_pad(self, image, target_side_length, multiple_of, fit_mode, add_black_bars, interpolation):
        # 1. Get current dimensions [Batch, Height, Width, Channels]
        b, h, w, c = image.shape
        aspect_ratio = w / h

        # 2. Calculate Content dimensions (Aspect Ratio Safe)
        if fit_mode == "shortest":
            if w < h:
                new_w, new_h = target_side_length, int(target_side_length / aspect_ratio)
            else:
                new_h, new_w = target_side_length, int(target_side_length * aspect_ratio)
        else: # longest
            if w > h:
                new_w, new_h = target_side_length, int(target_side_length / aspect_ratio)
            else:
                new_h, new_w = target_side_length, int(target_side_length * aspect_ratio)

        # 3. Calculate Container dimensions
        container_w = max(int(round(new_w / multiple_of) * multiple_of), multiple_of)
        container_h = max(int(round(new_h / multiple_of) * multiple_of), multiple_of)

        # 4. Determine Interpolation Method
        is_upscaling = new_w > w or new_h > h
        
        method_map = {
            "Bicubic (Upscale)": Image.BICUBIC,
            "Area (Downscale)": Image.BOX, # PIL's BOX is equivalent to Area
            "Lanczos (Downscale Sharper)": Image.LANCZOS,
            "Nearest (pixel art)": Image.NEAREST,
            "Nearest Exact (pixel art)": Image.NEAREST,
            "Bilinear": Image.BILINEAR
        }

        if interpolation == "AUTO_Bicubic_Lanczos":
            pil_filter = Image.BICUBIC if is_upscaling else Image.LANCZOS
        elif interpolation == "AUTO_Bicubic_Area":
            pil_filter = Image.BICUBIC if is_upscaling else Image.BOX
        else:
            pil_filter = method_map.get(interpolation, Image.BICUBIC)

        # 5. Process Batch
        output_images = []
        for i in range(b):
            # Convert torch tensor to PIL
            img_np = (image[i].cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np)
            
            if add_black_bars:
                # Resize to aspect-safe content size
                resized_pil = pil_img.resize((new_w, new_h), resample=pil_filter)
                
                # Create black canvas for container
                final_pil = Image.new("RGB", (container_w, container_h), (0, 0, 0))
                
                # Paste centered
                paste_x = (container_w - new_w) // 2
                paste_y = (container_h - new_h) // 2
                final_pil.paste(resized_pil, (paste_x, paste_y))
            else:
                # Stretch to container
                final_pil = pil_img.resize((container_w, container_h), resample=pil_filter)
            
            # Convert back to torch
            output_images.append(torch.from_numpy(np.array(final_pil).astype(np.float32) / 255.0))

        return (torch.stack(output_images), container_w, container_h)

NODE_CLASS_MAPPINGS = {"SmartResizeAndPad": SmartResizeAndPad}
NODE_DISPLAY_NAME_MAPPINGS = {"SmartResizeAndPad": "Smart Resize (Pad to Multiple)"}
