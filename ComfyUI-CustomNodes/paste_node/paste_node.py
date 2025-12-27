import os
import folder_paths
from nodes import LoadImage

class EnhancedLoadImage:
    @classmethod
    def INPUT_TYPES(s):
        # We use the exact same input types as the standard Load Image
        # This ensures the 'Choose file' dropdown and upload logic stay intact
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {"required": {"image": (sorted(files), {"image_upload": True})}}

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"
    CATEGORY = "image"

    def load_image(self, image):
        # We leverage the existing LoadImage logic for consistency
        return LoadImage().load_image(image)

NODE_CLASS_MAPPINGS = {"EnhancedLoadImage": EnhancedLoadImage}
NODE_DISPLAY_NAME_MAPPINGS = {"EnhancedLoadImage": "Load Image (with Paste)"}