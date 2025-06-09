// extension_ui.js
// Highlights all text in the model_url_input textbox when user clicks inside, robust to Gradio re-renders

function attachSelectAllOnClick() {
    var container = document.getElementById('model_url_input');
    if (container) {
        var textarea = container.querySelector('textarea');
        if (textarea && !textarea._selectAllHandlerAttached) {
            textarea.addEventListener('mouseup', function(e) {
                if (textarea.selectionStart === textarea.selectionEnd) {
                    textarea.select();
                }
            });
            textarea._selectAllHandlerAttached = true;
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    attachSelectAllOnClick();
    // Observe for dynamic changes (Gradio re-renders)
    const observer = new MutationObserver(attachSelectAllOnClick);
    observer.observe(document.body, { childList: true, subtree: true });
});
