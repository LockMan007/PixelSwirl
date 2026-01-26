class MultiLaneGlobalController:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "n_index": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "mult_8": ("INT", {"default": 8, "min": 0, "max": 10000, "step": 8}),
                "ltx_8n_plus_1": ("INT", {"default": 97, "min": 1, "max": 10000, "step": 8}),
                "mult_16": ("INT", {"default": 16, "min": 0, "max": 10000, "step": 16}),
                "res_32_width": ("INT", {"default": 512, "min": 0, "max": 10000, "step": 32}),
                "res_32_height": ("INT", {"default": 512, "min": 0, "max": 10000, "step": 32}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("1_index", "8_multiple", "8n_plus_1", "16_multiple", "32_width", "32_height")
    FUNCTION = "output_values"
    CATEGORY = "Toad nodes/Logic"

    def output_values(self, n_index, mult_8, ltx_8n_plus_1, mult_16, res_32_width, res_32_height):
        # This node acts as a pass-through hub with built-in step logic
        return (n_index, mult_8, ltx_8n_plus_1, mult_16, res_32_width, res_32_height)

NODE_CLASS_MAPPINGS = {
    "MultiLaneGlobalController": MultiLaneGlobalController
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultiLaneGlobalController": "Toad nodes: Global Integer Hub"
}