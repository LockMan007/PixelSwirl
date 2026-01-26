# last_frame_extractor_node.py

import torch

# This is the main class for your custom node
class LastFrameExtractor:
    # A unique name for your node within the node selector
    @classmethod
    def INPUT_TYPES(s):
        """
        Defines the input types for the node.
        'IMAGE' is the type that comes from a VAE Decode or similar node, 
        which is usually a batch of images (a tensor).
        """
        return {
            "required": {
                # The 'IMAGE' type is a tensor of shape [B, H, W, C] 
                # where B is the batch size (number of frames).
                "image_batch": ("IMAGE", {}), 
            }
        }

    # The category where your node will appear in the ComfyUI menu
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "extract_last_frame"
    CATEGORY = "utilities/frame"

    def extract_last_frame(self, image_batch):
        """
        The main function that performs the node's logic.
        
        image_batch: A torch.Tensor of shape [B, H, W, C]
        """
        
        # 1. Check if the batch is empty
        if image_batch.nelement() == 0:
            # Return an empty tensor if the input is empty
            print("Warning: Input image batch is empty.")
            # Create a 1x1x1x3 tensor of zeros to prevent connection errors
            return (torch.zeros((1, 1, 1, 3)),)

        # 2. Get the last frame from the batch
        # The batch is a tensor where the first dimension is the batch size (B).
        # In Python/PyTorch, -1 indexes the last element of the first dimension.
        last_frame = image_batch[-1]
        
        # 3. Reshape the single frame back into a batch of size 1
        # ComfyUI expects an output of shape [B, H, W, C], so we add 
        # the batch dimension back (size 1).
        last_frame_batch = last_frame.unsqueeze(0)

        # Return the output as a tuple, which is the ComfyUI standard
        return (last_frame_batch,)

# A list of classes to expose to ComfyUI
NODE_CLASS_MAPPINGS = {
    "LastFrameExtractor": LastFrameExtractor
}

# A dictionary to set friendly names for the nodes in the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "LastFrameExtractor": "Last Frame Extractor"
}