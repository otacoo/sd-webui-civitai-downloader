import os
import re
import json
import requests
from urllib.parse import urlparse, parse_qs
from modules import shared

def get_model_folders():
    return {
        "Checkpoint": os.path.join("models", "Stable-diffusion"),
        "LORA": os.path.join("models", "Lora"),
        "LyCORIS": os.path.join("models", getattr(shared.opts, "civitai_folder_lycoris", "Lora")),
        "LoCon": os.path.join("models", getattr(shared.opts, "civitai_folder_locon", "Lora")),
        "LoHa": os.path.join("models", "Lora"),
        "DoRA": os.path.join("models", "Lora"),
        "Controlnet": os.path.join("models", "ControlNet"),
        "Upscaler": os.path.join("models", "ESRGAN"),
        "VAE": os.path.join("models", "VAE"),
        "TextualInversion": os.path.join("models", "embeddings"),
        "Hypernetwork": os.path.join("models", "hypernetworks"),
    }

def get_civitai_api_key():
    return getattr(shared.opts, "civitai_api_key", "")

def get_civitai_model_info(model_id, api_key=None):
    api_url = f"https://civitai.com/api/v1/models/{model_id}"
    headers = {}
    params = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(api_url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def save_preview_and_metadata(folder, filename, model_info, preview_url=None):
    """
    Save the preview image (only jpg, jpeg, png, webp) and model metadata JSON next to the model file.
    If preview_url is not provided or is not a supported image, will try to find the first valid image from model_info.
    """
    # Save metadata
    base_path = os.path.join(folder, os.path.splitext(filename)[0])
    metadata_path = base_path + ".metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(model_info, f, ensure_ascii=False, indent=2)

    SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    def is_supported_image(url):
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        return ext in SUPPORTED_IMAGE_EXTS

    # Use helper to find valid preview image
    image_url = None
    if preview_url and is_supported_image(preview_url):
        image_url = preview_url
    else:
        for version in model_info.get("modelVersions", []):
            for image in version.get("images", []):
                url = image.get("url")
                if url and is_supported_image(url):
                    image_url = url
                    break
            if image_url:
                break
    # Save preview image if found
    if image_url:
        ext = os.path.splitext(image_url.split("?")[0])[1]
        if not ext or len(ext) > 5:
            ext = ".jpg"
        preview_path = base_path + f".preview{ext}"
        try:
            resp = requests.get(image_url, stream=True)
            resp.raise_for_status()
            with open(preview_path, "wb") as imgf:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        imgf.write(chunk)
        except Exception as e:
            print(f"Failed to download preview image: {e}")
    else:
        print("No valid preview image found; skipping preview download.")
