import torch
import torch.nn.functional as F

class SmartResizeAndPad:
    """
    Resizes an image to a target side length, maintaining aspect ratio.
    If the result is not a multiple of the specified number:
    - True: Adds black bars (padding) to reach the multiple.
    - False: Stretches the image slightly to reach the multiple.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                
                # The target size for the primary side (e.g. 336, 512, 1024)
                "target_side_length": ("INT", {"default": 512, "min": 16, "max": 8192, "step": 16}),
                
                # The snap value (e.g. 8, 16, 64)
                "multiple_of": ("INT", {"default": 16, "min": 1, "max": 128, "step": 1}),
                
                # "shortest": The smallest side becomes 'target_side_length'
                # "longest": The largest side becomes 'target_side_length'
                "fit_mode": (["shortest", "longest"],),
                
                # THE NEW OPTION
                "add_black_bars": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "width", "height")
    FUNCTION = "resize_and_pad"
    CATEGORY = "utils/image"

    def resize_and_pad(self, image, target_side_length, multiple_of, fit_mode, add_black_bars):
        # 1. Get current dimensions (ComfyUI images are [Batch, Height, Width, Channels])
        # We assume batch size of 1 for simplicity in calculation, but handle the tensor correctly
        b, h, w, c = image.shape
        aspect_ratio = w / h

        # 2. Calculate the "Content" dimensions (Aspect Ratio Safe)
        new_w = 0
        new_h = 0
        
        if fit_mode == "shortest":
            if w < h: # Width is shortest
                new_w = target_side_length
                new_h = int(target_side_length / aspect_ratio)
            else: # Height is shortest
                new_h = target_side_length
                new_w = int(target_side_length * aspect_ratio)
                
        elif fit_mode == "longest":
            if w > h: # Width is longest
                new_w = target_side_length
                new_h = int(target_side_length / aspect_ratio)
            else: # Height is longest
                new_h = target_side_length
                new_w = int(target_side_length * aspect_ratio)

        # 3. Calculate the "Container" dimensions (Snapped to Multiple)
        # We round the content dimensions to the nearest multiple to get the "Box" size
        container_w = int(round(new_w / multiple_of) * multiple_of)
        container_h = int(round(new_h / multiple_of) * multiple_of)

        # Safety check: dimensions must be at least the multiple
        if container_w < multiple_of: container_w = multiple_of
        if container_h < multiple_of: container_h = multiple_of

        # 4. Perform the Resize
        # PyTorch interpolate needs [Batch, Channels, Height, Width]
        img_permuted = image.permute(0, 3, 1, 2)
        
        if add_black_bars:
            # MODE A: LETTERBOX (PAD)
            # First, resize image to the "Content" size (keeping aspect ratio)
            # We explicitly use the exact calculated aspect-safe dims here
            resized = F.interpolate(img_permuted, size=(new_h, new_w), mode="bilinear", align_corners=False)
            
            # Calculate padding needed to reach the "Container" size
            pad_w = container_w - new_w
            pad_h = container_h - new_h
            
            # Padding format in torch is (Left, Right, Top, Bottom)
            pad_left = pad_w // 2
            pad_right = pad_w - pad_left
            pad_top = pad_h // 2
            pad_bottom = pad_h - pad_top
            
            # Apply padding (default value is 0 which is black)
            final_img = F.pad(resized, (pad_left, pad_right, pad_top, pad_bottom), value=0)
            
        else:
            # MODE B: STRETCH (No Padding)
            # Directly resize to the "Container" size (Slightly distorts AR to fit multiple)
            final_img = F.interpolate(img_permuted, size=(container_h, container_w), mode="bilinear", align_corners=False)

        # 5. Convert back to ComfyUI format [Batch, Height, Width, Channels]
        output_image = final_img.permute(0, 2, 3, 1)

        return (output_image, container_w, container_h)

# Register the node
NODE_CLASS_MAPPINGS = {
    "SmartResizeAndPad": SmartResizeAndPad
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SmartResizeAndPad": "Smart Resize (Pad to Multiple)"
}