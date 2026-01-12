import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Audio.BatchAudiotoad",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "BatchAudiotoad") {
            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnectionsChange) {
                    onConnectionsChange.apply(this, arguments);
                }

                // If a connection was made to the last input, add a new one
                if (connected && type === 1) { // type 1 is input
                    const lastSlot = this.inputs[this.inputs.length - 1];
                    if (lastSlot.link !== null) {
                        this.addInput(`audio_${this.inputs.length}`, "AUDIO");
                    }
                }
            };
        }
    },
});