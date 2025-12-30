import modules.scripts as scripts
import gradio as gr
import os
import re
import requests
import time
import json
from urllib.parse import urlparse, parse_qs
from modules import script_callbacks, shared as _shared
from scripts.backend.utils import get_model_folders, get_civitai_api_key, get_civitai_model_info, save_preview_and_metadata
from scripts.backend import metadata, delete_model
from scripts.settings import on_ui_settings
from scripts.backend.check_missing_info import check_missing_info
from scripts.backend.check_model_updates import check_model_updates
from scripts.backend.process_control import is_running, get_type, cancel_process


def get_package_version():
    pkg_path = os.path.join(os.path.dirname(__file__), '..', 'package.json')
    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            pkg = json.load(f)
            return pkg.get('version', 'unknown')
    except Exception:
        return 'unknown'

VERSION = get_package_version()

def parse_civitai_model_and_version_id(input_str):
    if input_str.strip().isdigit():
        return input_str.strip(), None
    try:
        parsed = urlparse(input_str)
        if parsed.netloc in [
            "civitai.com",
            "www.civitai.com",
            "civitai.green",
            "www.civitai.green",
        ]:
            match = re.match(r"^/models/(\d+)", parsed.path)
            model_id = match.group(1) if match else None
            qs = parse_qs(parsed.query)
            model_version_id = qs.get("modelVersionId", [None])[0]
            return model_id, model_version_id
    except Exception:
        pass
    match = re.search(r"civitai\.(?:com|green)/models/(\d+)", input_str)
    model_id = match.group(1) if match else None
    match_version = re.search(r"modelVersionId=(\d+)", input_str)
    model_version_id = match_version.group(1) if match_version else None
    return model_id, model_version_id


def get_civitai_first_image_url_from_model_info(model_info, model_version_id=None):
    """
    Returns the first image URL from the specified model version that has a supported image extension,
    skipping video files. Supported types: jpg, jpeg, png, webp
    """
    model_versions = model_info.get("modelVersions", [])
    version = None

    if model_version_id:
        for v in model_versions:
            if str(v.get("id")) == str(model_version_id):
                version = v
                break

    if not version and model_versions:
        version = model_versions[0]

    if version and "images" in version:
        for image in version.get("images", []):
            url = image.get("url")
            if not url:
                continue

            # Extract file extension from URL path
            parsed = urlparse(url)
            path = parsed.path
            ext = path.split(".")[-1].lower() if "." in path else ""

            if ext in {"jpg", "jpeg", "png", "webp"}:
                return url

    return None


def check_model(model_url):
    model_id, model_version_id = parse_civitai_model_and_version_id(model_url)
    if not model_id:
        return None, None, None, "Could not parse model ID from URL or input."
    api_key = get_civitai_api_key()
    try:
        model_info = get_civitai_model_info(model_id, api_key=api_key)
        image_url = get_civitai_first_image_url_from_model_info(
            model_info, model_version_id
        )
        model_name = model_info.get("name", f"Model {model_id}")
        model_type = model_info.get("type", "Unknown")
        tags = model_info.get("tags", [])
        tags_str = ", ".join(tags) if tags else "None"
        info_text = f"Model: {model_name}\nType: {model_type}\nTags: {tags_str}"
        if model_version_id:
            info_text += f"\nVersion ID: {model_version_id}"
        return image_url, model_id, model_version_id, info_text
    except Exception as e:
        return None, None, None, f"Error checking model: {str(e)}"


def get_first_valid_preview_image(model_info, preview_url=None):
    SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

    def is_supported_image(url):
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        return ext in SUPPORTED_IMAGE_EXTS

    if preview_url and is_supported_image(preview_url):
        return preview_url
    for version in model_info.get("modelVersions", []):
        for image in version.get("images", []):
            url = image.get("url")
            if url and is_supported_image(url):
                return url
    return None

def robust_get(url, headers=None, stream=False, timeout=15, max_retries=5):
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, stream=stream, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"Attempt {attempt} failed for {url}: {e}")
            last_exc = e
            time.sleep(2)  # Wait before retrying
    raise last_exc


# Global dictionary to track cancellation flags per model_id
DOWNLOAD_CANCEL_FLAGS = {}


def cancel_download(model_id):
    """Set the cancellation flag for a given model_id."""
    DOWNLOAD_CANCEL_FLAGS[model_id] = True


def download_civitai_model_with_progress(
    model_id, model_version_id=None, progress=gr.Progress(), selected_preview_url=None
):
    """
    The cancel button should set DOWNLOAD_CANCEL_FLAGS[model_id] = True.
    """
    # Clear output at the start of a new download
    yield gr.Label.update(value="Starting..."), gr.Textbox.update(value="")
    api_key = get_civitai_api_key()
    # Reset cancellation flag at the start
    DOWNLOAD_CANCEL_FLAGS[model_id] = False

    try:
        data = get_civitai_model_info(model_id, api_key=api_key)
    except Exception as e:
        # Clean up flag on error
        DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
        yield gr.Label.update(value="Error"), gr.Textbox.update(
            value=f"Error: {str(e)}"
        )
        return

    model_versions = data.get("modelVersions", [])
    version = None
    if model_version_id:
        for v in model_versions:
            if str(v.get("id")) == str(model_version_id):
                version = v
                break
        if not version:
            DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
            yield (
                gr.Label.update(value="Error"),
                gr.Textbox.update(
                    value=f"Model version ID {model_version_id} not found for model {model_id}."
                ),
            )
            return
    else:
        if model_versions:
            version = model_versions[0]
        else:
            DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
            yield gr.Label.update(value="Error"), gr.Textbox.update(
                value="No versions found for this model."
            )
            return

    model_type = data.get("type", "Checkpoint")
    valid_extensions = {".safetensors", ".pth", ".ckpt"}
    model_files = [
        f for f in version["files"]
        if any(f["name"].lower().endswith(ext) for ext in valid_extensions)
    ]

    if not model_files:
        DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
        yield gr.Label.update(value="Error"), gr.Textbox.update(
            value="No valid model file found for this version."
        )
        return

    file_info = model_files[0]
    download_url = file_info["downloadUrl"]
    filename = file_info["name"]

    # Sanitize filename: keep only a-z, A-Z, 0-9, - and _
    def sanitize_filename(filename):
        base, ext = os.path.splitext(filename)
        base = re.sub(r"\s+", "-", base)
        base = re.sub(r"[^a-zA-Z0-9\-_]", "", base)
        return base + ext

    filename = sanitize_filename(filename)

    MODEL_FOLDERS = get_model_folders()
    folder = MODEL_FOLDERS.get(model_type, os.path.join("models", "Stable-diffusion"))
    os.makedirs(folder, exist_ok=True)
    dest_path = os.path.join(folder, filename)

    if os.path.exists(dest_path):
        msg = f"Model already exists: {dest_path}"
        print(msg)
        # Still save metadata and preview if missing
        # Use selected preview URL if provided, otherwise fall back to first image
        preview_url = selected_preview_url
        if not preview_url and "images" in version and version["images"]:
            preview_url = version["images"][0]["url"]
        save_preview_and_metadata(folder, filename, data, preview_url)
        DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
        yield gr.Label.update(value=msg), gr.Textbox.update(value=msg)
        return

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with robust_get(download_url, headers=headers, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            chunk_size = 8192 * 4  # 32KB
            update_interval = 1024 * 1024 * 10  # 10MB

            print(f"\nDownloading {filename} ({model_type}) from {download_url}")
            print(f"Total size: {total // 1024 // 1024}MB")

            with open(dest_path, "wb") as f:
                downloaded = 0
                last_update = 0
                last_progress = 0
                start_time = time.time()

                while True:
                    chunk = r.raw.read(chunk_size)
                    if not chunk:
                        break

                    # Check for cancellation frequently
                    if DOWNLOAD_CANCEL_FLAGS.get(model_id, False):
                        f.close()
                        try:
                            os.remove(dest_path)
                        except Exception as cleanup_err:
                            print(f"Failed to remove partial file: {cleanup_err}")
                        DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
                        yield (
                            gr.Label.update(value="Cancelled"),
                            gr.Textbox.update(
                                value=f"Download cancelled and partial files deleted for: {filename}"
                            ),
                        )
                        return

                    f.write(chunk)
                    downloaded += len(chunk)

                    # Terminal progress bar
                    now = time.time()
                    if now - last_update > 0.5 or downloaded == total:
                        mb_downloaded = downloaded / 1024 / 1024
                        mb_total = total / 1024 / 1024 if total else 0
                        percent = (downloaded / total * 100) if total else 0
                        elapsed = now - start_time
                        speed = mb_downloaded / elapsed if elapsed > 0 else 0
                        eta = (
                            ((total - downloaded) / (speed * 1024 * 1024))
                            if speed > 0 and total
                            else 0
                        )
                        bar_len = 30
                        filled_len = int(bar_len * downloaded // total) if total else 0
                        bar = "=" * filled_len + "-" * (bar_len - filled_len)
                        print(
                            f"\r[{bar}] {mb_downloaded:.1f}/{mb_total:.1f}MB "
                            f"({percent:.1f}%) | {speed:.2f}MB/s | ETA: {eta:.1f}s",
                            end="",
                            flush=True,
                        )
                        last_update = now

                    # Gradio progress
                    progress_str = "Downloading..."
                    if (
                        downloaded - last_progress > update_interval
                        or downloaded == total
                    ):
                        progress((downloaded / total) if total else 0)
                        yield (
                            gr.Label.update(
                                value=(
                                    f"Downloading: {downloaded//1024}KB/{total//1024 if total else '?'}KB "
                                    f"({downloaded/total*100:.1f}%)"
                                    if total
                                    else ""
                                )
                            ),
                            gr.Textbox.update(value=progress_str),
                        )
                        last_progress = downloaded

                print()  # Newline after terminal progress
            print(f"\nDownloaded to {dest_path}")

        # After download, save preview and metadata
        # Use selected preview URL if provided, otherwise fall back to first image
        preview_url = selected_preview_url
        if not preview_url and "images" in version and version["images"]:
            preview_url = version["images"][0]["url"]
        save_preview_and_metadata(folder, filename, data, preview_url)
        DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
        yield gr.Label.update(value="Done"), gr.Textbox.update(
            value=f"Downloaded Civitai {model_type} model to: {dest_path}"
        )
        time.sleep(0.2)
    except Exception as e:
        DOWNLOAD_CANCEL_FLAGS.pop(model_id, None)
        yield gr.Label.update(value="Error"), gr.Textbox.update(
            value=f"Error downloading from Civitai: {str(e)}"
        )


def download_model(model_state, preview_urls_state, preview_selection, progress=gr.Progress()):
    # model_state: (model_id, model_version_id)
    # preview_urls_state: (preview1_url, preview2_url)
    if not model_state or not model_state[0]:
        yield gr.Label.update(value="Error"), gr.Textbox.update(
            value="No model checked. Please check the model first."
        )
        return
    model_id, model_version_id = model_state
    # Determine which preview URL to use
    selected_preview_url = None
    if preview_urls_state:
        preview1_url, preview2_url = preview_urls_state
        if preview_selection == "Preview 1" and preview1_url:
            selected_preview_url = preview1_url
        elif preview_selection == "Preview 2" and preview2_url:
            selected_preview_url = preview2_url
        # Fallback to preview1 if preview2 is selected but not available
        elif preview_selection == "Preview 2" and preview1_url:
            selected_preview_url = preview1_url
        elif preview1_url:
            selected_preview_url = preview1_url
    
    yield from download_civitai_model_with_progress(
        model_id, model_version_id, progress, selected_preview_url
    )


def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as ui_component:
        # Hidden components for JS-triggered alerts
        js_alert_box = gr.Textbox(visible=False, elem_id="js_alert_box")
        js_alert_btn = gr.Button(visible=False, elem_id="js_alert_btn")

        def js_alert_py(msg_and_type):
            try:
                data = json.loads(msg_and_type)
                msg = data.get("message", "")
                level = data.get("level", "info")
            except Exception:
                msg = str(msg_and_type)
                level = "info"
            if level == "info":
                return gr.Info(msg)
            elif level == "warning":
                return gr.Warning(msg)
            else:
                return gr.Info(msg)

        js_alert_btn.click(js_alert_py, inputs=[js_alert_box], outputs=[])
        extra_css = ""
        if getattr(_shared.opts, "civitai_disable_card_description", False):
            extra_css = """
            <style>
            .actions .description {
                display: none !important;
            }
            </style>
            """
        gr.HTML(
            f"""
        <style>
        /* Remove the glowing border and animation from the Output gr.Textbox */
        #ota_textbox > .generating,
        #ota_progress > .generating,
        #ota_progress > .wrap.full {{
            display: none !important;
        }}
        #ota_textbox {{
            border: var(--input-border-width) solid var(--input-border-color);
            border-radius: var(--input-radius);
            padding: 5px 0 5px 10px;
        }}
        </style>
        {extra_css}
        """
        )
        with gr.Row():
            with gr.Column(variant="panel"):
                gr.Markdown("#### Model Selection")
                model_url = gr.Textbox(
                    label="Civitai Model URL or ID",
                    placeholder="e.g. 12345 or https://civitai.com/models/12345/...",
                    scale=4,
                    elem_id="model_url_input",
                )
                with gr.Row():
                    check_btn = gr.Button("Check Model", variant="secondary")
                gr.Markdown("#### Info Tools")
                with gr.Row():
                    check_missing_btn = gr.Button("Check models for missing info (preview, metadata)", variant="secondary")
                    check_updates_btn = gr.Button("Check for model updates", variant="secondary")

                gr.Markdown("#### Download Controls")
                with gr.Row():
                    cancel_btn = gr.Button("Cancel", variant="stop", scale=1)
                    download_btn = gr.Button(
                        "Download", interactive=False, variant="primary", scale=2
                    )

                progress_label = gr.Label(label="Progress", elem_id="ota_progress")
                output = gr.Markdown(label="Output", elem_id="ota_textbox")

            with gr.Column(variant="panel"):
                gr.Markdown("#### Model Preview & Info")
                with gr.Row():
                    preview1 = gr.Image(
                        label="Preview 1", interactive=False, height=512, fill_width=True
                    )
                    preview2 = gr.Image(
                        label="Preview 2", interactive=False, height=512, fill_width=True
                    )
                preview_selection = gr.Radio(
                    label="Select Thumbnail Preview",
                    choices=["Preview 1", "Preview 2"],
                    value="Preview 1",
                    interactive=True,
                    info="Choose which preview image to use as the thumbnail when downloading"
                )
                info = gr.Textbox(label="Model Info", interactive=False, lines=6)

        model_state = gr.State(value=None)
        preview_urls_state = gr.State(value=None)  # Store (preview1_url, preview2_url)
        gr.Markdown(
            f"<div style='text-align:center; color:gray;'>"
            f"<center><b>Civitai Model Downloader — v{VERSION} — otacoo</b></center>"
            f"</div>"
        )

        # --- Logic functions ---
        def get_first_two_preview_images(model_url):
            model_id, model_version_id = parse_civitai_model_and_version_id(model_url)
            if not model_id:
                return None, None, None, None, "Could not parse model ID from URL or input."
            api_key = get_civitai_api_key()
            try:
                model_info = get_civitai_model_info(model_id, api_key=api_key)
                SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
                def is_supported_image(url):
                    ext = os.path.splitext(url.split("?")[0])[1].lower()
                    return ext in SUPPORTED_IMAGE_EXTS
                urls = []
                # Find the correct version
                model_versions = model_info.get("modelVersions", [])
                version = None
                if model_version_id:
                    for v in model_versions:
                        if str(v.get("id")) == str(model_version_id):
                            version = v
                            break
                if not version and model_versions:
                    version = model_versions[0]
                # Only collect images from the selected version
                if version and "images" in version:
                    for image in version.get("images", []):
                        url = image.get("url")
                        if url and is_supported_image(url) and url not in urls:
                            urls.append(url)
                img1 = urls[0] if len(urls) > 0 else None
                img2 = urls[1] if len(urls) > 1 else None
                model_name = model_info.get("name", f"Model {model_id}")
                model_type = model_info.get("type", "Unknown")
                tags = model_info.get("tags", [])
                tags_str = ", ".join(tags) if tags else "None"
                info_text = f"Model: {model_name}\nType: {model_type}\nTags: {tags_str}"
                if model_version_id:
                    info_text += f"\nVersion ID: {model_version_id}"
                return img1, img2, model_id, model_version_id, info_text
            except Exception as e:
                return None, None, None, None, f"Error checking model: {str(e)}"

        def check_and_update(url):
            img1, img2, model_id, model_version_id, info_text = get_first_two_preview_images(url)
            state = (model_id, model_version_id) if model_id else None
            preview_urls = (img1, img2) if model_id else None
            download_enabled = bool(model_id)
            return img1, img2, info_text, state, preview_urls, gr.update(interactive=download_enabled)

        def cancel_download(state):
            cancelled = False
            # Cancel model download if running
            if state and state[0] and not DOWNLOAD_CANCEL_FLAGS.get(state[0], False):
                DOWNLOAD_CANCEL_FLAGS[state[0]] = True
                cancelled = True
            # Cancel any backend process if running
            try:
                if is_running():
                    cancel_process()
                    cancelled = True
            except Exception:
                pass
            if cancelled:
                return gr.Label.update(value=""), "Cancelling..."
            else:
                return gr.Label.update(value=""), "Nothing to cancel."

        # --- Button bindings ---
        check_btn.click(
            fn=check_and_update,
            inputs=[model_url],
            outputs=[preview1, preview2, info, model_state, preview_urls_state, download_btn],
        )
        def check_missing_info_or_cancel():
            if is_running():
                cancel_process()
                yield "Stopping current process..."
                return
            yield from check_missing_info()

        def check_model_updates_or_cancel():
            if is_running():
                cancel_process()
                yield "Stopping current process..."
                return
            yield from check_model_updates()

        check_missing_btn.click(
            fn=check_missing_info_or_cancel,
            inputs=[],
            outputs=[output],
        )
        check_updates_btn.click(
            fn=check_model_updates_or_cancel,
            inputs=[],
            outputs=[output],
        )
        download_btn.click(
            fn=download_model,
            inputs=[model_state, preview_urls_state, preview_selection],
            outputs=[progress_label, output],
        )
        cancel_btn.click(
            fn=cancel_download,
            inputs=[model_state],
            outputs=[progress_label, output],
        )

    return [(ui_component, "Model Downloader", "extension_model_dl_tab")]


script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_app_started(metadata.on_app_started)
script_callbacks.on_app_started(delete_model.on_app_started)
