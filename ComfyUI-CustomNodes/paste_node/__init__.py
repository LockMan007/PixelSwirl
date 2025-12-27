from .paste_node import EnhancedLoadImage

NODE_CLASS_MAPPINGS = {
    "EnhancedLoadImage": EnhancedLoadImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EnhancedLoadImage": "Load Image (with Paste)"
}

# This is the "magic" line that makes ComfyUI load your JS
WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]