// card_buttons.js
(function () {
    "use strict";

    // Button HTML as a <ul>
    function getButtonsHtml() {
        let html = '<ul class="custom-card-buttons" style="display:none;gap:0.5em;list-style:none;padding:0;margin:0;">';
        if (typeof opts === 'undefined' || opts.civitai_card_button_open_url !== false) {
            html += '<li><button class="open-url-btn" title="Open URL" style="cursor:pointer;">🌐</button></li>';
        }
        if (typeof opts === 'undefined' || opts.civitai_card_button_delete !== false) {
            html += '<li><button class="delete-btn" title="Delete" style="cursor:pointer;">❌</button></li>';
        }
        html += '</ul>';
        return html;
    }

    function stopEvent(e) {
        e.stopPropagation();
        e.preventDefault();
    }

    function getModelPath(card) {
        const searchTerm = card.querySelector('.actions .additional .search_terms');
        if (searchTerm) return searchTerm.textContent.trim();
        const searchTerm2 = card.querySelector('.actions .additional .search_term');
        if (searchTerm2) return searchTerm2.textContent.trim();
        return null;
    }

    function notifySDWebUI(message, type = "info") {
        const app = gradioApp();
        const alertBox = app.querySelector('#js_alert_box input, #js_alert_box textarea');
        const alertBtn = app.querySelector('#js_alert_btn button, #js_alert_btn');
        if (alertBox && alertBtn) {
            alertBox.value = JSON.stringify({ message, level: type });
            alertBox.dispatchEvent(new Event("input", { bubbles: true }));
            alertBtn.click();
        } else {
            alert(message);
        }
    }

    function processCard(card) {
        if (card.querySelector('.custom-card-buttons')) return;
        const actions = card.querySelector('.actions');
        const BUTTONS_HTML = getButtonsHtml();
        if (actions) {
            actions.insertAdjacentHTML('beforebegin', BUTTONS_HTML);
        } else {
            card.insertAdjacentHTML('beforeend', BUTTONS_HTML);
        }
        const btns = card.querySelector('.custom-card-buttons');

        const urlBtn = btns.querySelector('.open-url-btn');
        const delBtn = btns.querySelector('.delete-btn');

        if (urlBtn) {
            urlBtn.onclick = async function (e) {
                e.stopPropagation();
                e.preventDefault();
                const searchTerm = card.querySelector('.actions .additional .search_terms');
                let modelPath = searchTerm ? searchTerm.textContent.trim() : null;
                if (!modelPath) {
                    notifySDWebUI("Could not determine model path for info page.", "error");
                    return;
                }
                let metadataPath = modelPath.replace(/\.[^/.]+$/, '.metadata.json').replace(/\\/g, '/');
                // Ensure the path starts with 'models/'
                if (!metadataPath.startsWith('models/')) {
                    metadataPath = 'models/' + metadataPath;
                }
                let metadataUrl = `/sd-webui-model-downloader/api/metadata?path=${encodeURIComponent(metadataPath)}`;
                try {
                    let resp = await fetch(metadataUrl);
                    if (!resp.ok) throw new Error("Metadata not found");
                    let metadata = await resp.json();
                    let domain = "civitai.com";
                    let modelId = null;
                    if (metadata.civitai && metadata.civitai.modelId) {
                        modelId = metadata.civitai.modelId; // Old format (Civitai Helper)
                    } else if (metadata.civitai && metadata.civitai.id) {
                        modelId = metadata.civitai.id; // New format, but this is version/file ID
                    } else if (metadata.id) {
                        modelId = metadata.id;
                    }
                    if (!modelId) throw new Error("No model id in metadata");
                    // Optionally extract domain from downloadUrl if present and desired
                    if (metadata.downloadUrl) {
                        let m = metadata.downloadUrl.match(/^https?:\/\/([^/]+)/);
                        if (m) {
                            // Only allow civitai.com or civitai.green
                            if (m[1] === "civitai.com" || m[1] === "civitai.green") {
                                domain = m[1];
                            } else {
                                domain = "civitai.com";
                            }
                        }
                    }
                    let infoUrl = `https://${domain}/models/${modelId}/`;
                    window.open(infoUrl, "_blank");
                } catch (err) {
                    notifySDWebUI("Failed to open model info page: " + err.message, "error");
                }
            };
        }
        if (delBtn) {
            delBtn.onclick = async function (e) {
                stopEvent(e);
                let rm_confirm = "\nDo you really want to remove this model and all related files? This process is irreversible.";
                if (!confirm(rm_confirm)) {
                    return false;
                }
                const modelPath = getModelPath(card);
                if (!modelPath) {
                    notifySDWebUI("Could not determine model path for deletion.", "error");
                    return false;
                }
                // Ensure the path starts with 'models/'
                let apiModelPath = modelPath.replace(/\\/g, '/');
                if (!apiModelPath.startsWith('models/')) {
                    apiModelPath = 'models/' + apiModelPath;
                }
                try {
                    const resp = await fetch('/sd-webui-model-downloader/api/delete_model', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ model_path: apiModelPath })
                    });
                    const result = await resp.json();
                    if (resp.ok && result.success) {
                        notifySDWebUI(result.message || 'Model deleted successfully.', 'info');
                        // Remove the card from the UI
                        card.remove();
                    } else {
                        notifySDWebUI(result.error || 'Failed to delete model.', 'error');
                    }
                } catch (err) {
                    notifySDWebUI('Failed to delete model: ' + err.message, 'error');
                }
                return false;
            };
        }
    }

    function processVisibleCards() {
        const containers = gradioApp().querySelectorAll('.extra-network-cards');
        containers.forEach(container => {
            if (container.offsetParent !== null) {
                const cards = container.querySelectorAll('.card');
                cards.forEach(processCard);
            }
        });
    }

    function setupCardButtonUI() {
        processVisibleCards();
        gradioApp().addEventListener('click', function () {
            setTimeout(processVisibleCards, 100);
        }, true);

        const style = document.createElement('style');
        style.textContent = `
            .card {
                position: relative;
            }
            .card .custom-card-buttons {
                position: absolute;
                right: 34%;
                bottom: 15%;
                z-index: 2;
                padding: 0.2em 0.6em;
                display: none;
                justify-content: center;
                align-items: center;
            }
            .card:hover .custom-card-buttons {
                display: flex !important;
            }
            .custom-card-buttons li {
                display: inline-block;
            }
            .custom-card-buttons button {
                background: var(--button-secondary-background, #eee);
                border: 1px solid var(--button-border-color, #ccc);
                border-radius: 6px;
                padding: 0.2em 0.6em;
                font-size: 1.1em;
                transition: background 0.2s;
                opacity: 0.8;
            }
            .custom-card-buttons button:hover {
                background: var(--button-primary-background, #ccc);
                opacity: 1;
            }
        `;
        document.head.appendChild(style);
    }

    function waitForUiLoadedAndSetup() {
        if (window.onUiLoaded) {
            onUiLoaded(setupCardButtonUI);
        } else {
            setTimeout(waitForUiLoadedAndSetup, 500);
        }
    }

    waitForUiLoadedAndSetup();
})();