from .paste_node import EnhancedLoadImage
from .save_node import EnhancedSaveImage

NODE_CLASS_MAPPINGS = {
    "EnhancedLoadImage": EnhancedLoadImage,
    "EnhancedSaveImage": EnhancedSaveImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EnhancedLoadImage": "Load Image (with Paste)",
    "EnhancedSaveImage": "Save Image (with Copy)"
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]