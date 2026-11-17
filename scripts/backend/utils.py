import os
import re
import json
import requests
from urllib.parse import urlparse, parse_qs
from modules import shared

MODEL_FILE_EXTS = (".safetensors", ".ckpt", ".pt", ".pth", ".bin")

def _dedupe_paths(paths):
    seen = set()
    result = []
    for path in paths:
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result

def _folder_has_model_files(folder):
    for root, dirs, files in os.walk(folder):
        if any(name.lower().endswith(MODEL_FILE_EXTS) for name in files):
            return True
    return False

def get_model_folder_candidates():
    """Ordered candidate folders for each model type.

    Supports both the classic A1111 folder names and ComfyUI-style names,
    e.g. models/Lora vs models/loras or models/Stable-diffusion vs
    models/checkpoints and models/diffusion_models.
    """
    lycoris_folder = getattr(shared.opts, "civitai_folder_lycoris", "Lora")
    locon_folder = getattr(shared.opts, "civitai_folder_locon", "Lora")

    def paths(*names):
        return _dedupe_paths([os.path.join("models", name) for name in names])

    return {
        "Checkpoint": paths("Stable-diffusion", "checkpoints", "diffusion_models", "unet"),
        "LORA": paths("Lora", "loras"),
        "LyCORIS": paths(lycoris_folder, "Lora", "loras"),
        "LoCon": paths(locon_folder, "Lora", "loras"),
        "LoHa": paths("Lora", "loras"),
        "DoRA": paths("Lora", "loras"),
        "Controlnet": paths("ControlNet", "controlnet"),
        "Upscaler": paths("ESRGAN", "upscale_models"),
        "VAE": paths("VAE", "vae"),
        "TextualInversion": paths("embeddings"),
        "Hypernetwork": paths("hypernetworks"),
    }

def _resolve_model_folder(candidates):
    existing = [folder for folder in candidates if os.path.isdir(folder)]
    if len(existing) == 1:
        return existing[0]
    for folder in existing:
        if _folder_has_model_files(folder):
            return folder
    if existing:
        return existing[0]
    return candidates[0]

def get_model_folders():
    """Return the preferred folder for each model type.

    The first candidate that exists and actually contains model files wins,
    so A1111 and ComfyUI-style folder layouts are both supported.
    """
    folders = {
        model_type: _resolve_model_folder(candidates)
        for model_type, candidates in get_model_folder_candidates().items()
    }
    # An explicitly configured LyCORIS/LoCon folder wins even if it does not exist yet.
    for model_type, option in (
        ("LyCORIS", "civitai_folder_lycoris"),
        ("LoCon", "civitai_folder_locon"),
    ):
        custom_folder = getattr(shared.opts, option, "Lora")
        if custom_folder and custom_folder not in ("Lora", "loras"):
            folders[model_type] = os.path.join("models", custom_folder)
    return folders

def get_all_model_folders():
    """Return every existing candidate folder for each model type.

    Used by the scanners so models are found regardless of whether the
    install uses A1111 or ComfyUI-style folder names. Folders resolving to
    the same real path (junctions/symlinks) are only returned once.
    """
    result = {}
    seen = set()
    for model_type, candidates in get_model_folder_candidates().items():
        folders = []
        for folder in candidates:
            if not os.path.isdir(folder):
                continue
            real = os.path.normcase(os.path.realpath(folder))
            if real in seen:
                continue
            seen.add(real)
            folders.append(folder)
        if folders:
            result[model_type] = folders
    return result

def get_model_folder_roots():
    """Return all model folders that can be used as download destinations."""
    roots = set(get_model_folders().values())
    for folders in get_all_model_folders().values():
        roots.update(folders)
    return sorted(roots)

def get_civitai_api_key():
    return getattr(shared.opts, "civitai_api_key", "")

def get_civitai_domains():
    """Returns [preferred_domain, fallback_domain] based on the user's setting."""
    preferred = getattr(shared.opts, "civitai_preferred_domain", "civitai.red") or "civitai.red"
    if preferred not in ("civitai.com", "civitai.red"):
        preferred = "civitai.red"
    fallback = "civitai.red" if preferred == "civitai.com" else "civitai.com"
    return [preferred, fallback]

def get_civitai_model_info(model_id, api_key=None):
    headers = {}
    params = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    last_exc = None
    for domain in get_civitai_domains():
        try:
            resp = requests.get(f"https://{domain}/api/v1/models/{model_id}", headers=headers, params=params)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_exc = e
            continue
    if last_exc:
        raise last_exc
    return None

def save_model_info_json(folder, filename, model_info, model_version=None):
    """
    Save or update the .json file used by SD WebUI to populate model info.
    Extracts trainedWords (activation words) and description from metadata.
    """
    base_path = os.path.join(folder, os.path.splitext(filename)[0])
    json_path = base_path + ".json"
    
    # Extract trainedWords from model version
    trained_words = []
    if model_version and "trainedWords" in model_version:
        trained_words = model_version.get("trainedWords", [])
    
    # Extract description from model info
    description = model_info.get("description", "")
    
    # Format activation_text: join trainedWords with commas and add trailing comma
    activation_text = ", ".join(trained_words) + "," if trained_words else ""
    
    # Load existing .json file if it exists, otherwise create default structure
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"Failed to read existing .json file: {e}, creating new one")
            existing_data = {}
    else:
        existing_data = {}
    
    # Update with new data, preserving existing fields if they exist
    existing_data["description"] = description
    existing_data["activation text"] = activation_text
    
    # Ensure required fields exist with defaults if not present
    if "sd version" not in existing_data:
        existing_data["sd version"] = model_version.get("baseModel", "") if model_version else ""
    if "preferred weight" not in existing_data:
        existing_data["preferred weight"] = 0
    if "negative text" not in existing_data:
        existing_data["negative text"] = ""
    if "notes" not in existing_data:
        existing_data["notes"] = ""
    
    # Save the updated .json file
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save .json file: {e}")


def save_preview_and_metadata(folder, filename, model_info, preview_url=None, model_version=None):
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
    
    # Save .json file with activation words and description
    save_model_info_json(folder, filename, model_info, model_version)