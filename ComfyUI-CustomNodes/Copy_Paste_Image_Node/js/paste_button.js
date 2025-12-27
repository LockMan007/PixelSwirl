import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.EnhancedLoadImage",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "EnhancedLoadImage") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // Add the Paste Button at the bottom
                const btn = this.addWidget("button", "📋 Paste from Clipboard", null, () => {
                    this.handlePaste();
                });
                
                // Keep the button visually distinct
                btn.serialize = false; 
            };

            nodeType.prototype.handlePaste = async function() {
                try {
                    const items = await navigator.clipboard.read();
                    for (const item of items) {
                        if (item.types.some(type => type.startsWith("image/"))) {
                            const blob = await item.getType(item.types.find(t => t.startsWith("image/")));
                            
                            // Upload to ComfyUI server
                            const formData = new FormData();
                            formData.append("image", blob, `pasted_${Date.now()}.png`);
                            
                            const resp = await fetch("/upload/image", {
                                method: "POST",
                                body: formData,
                            });
                            
                            const result = await resp.json();
                            
                            // Update the widget and trigger the preview
                            const imageWidget = this.widgets.find(w => w.name === "image");
                            imageWidget.value = result.name;
                            
                            // This is the critical part that fixes the "No Preview" issue:
                            if (imageWidget.callback) {
                                imageWidget.callback(result.name);
                            }
                        }
                    }
                } catch (err) {
                    alert("Clipboard access denied or empty. Ensure you are on localhost or HTTPS.");
                }
            };
        }
    }
});