import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.EnhancedSaveImage",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "EnhancedSaveImage") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                this.addWidget("button", "📋 Copy Image to Clipboard", null, () => {
                    this.handleCopy();
                });
            };

            nodeType.prototype.handleCopy = async function() {
                if (this.imgs && this.imgs.length > 0) {
                    const imgCanvas = this.imgs[0];
                    const src = imgCanvas.src;

                    try {
                        const data = await fetch(src);
                        const blob = await data.blob();
                        await navigator.clipboard.write([
                            new ClipboardItem({ [blob.type]: blob })
                        ]);
                        console.log("Copied!");
                    } catch (err) {
                        alert("Copy failed. Use localhost or HTTPS.");
                    }
                } else {
                    alert("Run the workflow first to generate an image!");
                }
            };
        }
    }
});