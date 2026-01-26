import numpy as np
import torch
import cv2

class VideoFrameRGBJoiner:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "red_channel": ("IMAGE",),
                "green_channel": ("IMAGE",),
                "blue_channel": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("combined_image",)
    FUNCTION = "join_rgb_channels"
    CATEGORY = "Video Manipulation"

    def join_rgb_channels(self, red_channel, green_channel, blue_channel):
        device = red_channel.device  # Get the device from the input tensor

        red_channel = red_channel.cpu().numpy()
        green_channel = green_channel.cpu().numpy()
        blue_channel = blue_channel.cpu().numpy()

        # Ensure all channels are 3D arrays with the same shape
        assert red_channel.shape == green_channel.shape == blue_channel.shape

        batch_size, height, width = red_channel.shape

        combined_images = []

        for i in range(batch_size):
            r = red_channel[i]
            g = green_channel[i]
            b = blue_channel[i]

            # Merge the channels
            combined_image = np.stack((r, g, b), axis=-1)
            combined_images.append(combined_image)

        combined_images = np.array(combined_images)
        return torch.from_numpy(combined_images).to(device)

NODE_CLASS_MAPPINGS = {
    "VideoFrameRGBJoiner": VideoFrameRGBJoiner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoFrameRGBJoiner": "Toad nodes: Video Frame RGB Joiner",
}
