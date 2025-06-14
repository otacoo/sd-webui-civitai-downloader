import os
import hashlib
import requests
from .utils import get_model_folders, get_civitai_api_key, save_preview_and_metadata
from .process_control import is_running, set_running, clear_running, cancel_process, is_cancelled, get_type

def sha256_of_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def get_model_info_by_hash(file_hash, api_key=None):
    url = f"https://civitai.com/api/v1/model-versions/by-hash/{file_hash}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 404:
        return None  # Not found
    resp.raise_for_status()
    return resp.json()

def cancel_check_missing_info():
    cancel_process()

def check_missing_info():
    if is_running():
        yield f"Another process is already running: {get_type()}"
        return
    set_running('missing_info')
    try:
        MODEL_FOLDERS = get_model_folders()
        summary = []
        skip_types = {"Controlnet", "Upscaler", "VAE"}
        files_to_check = []
        # Deduplicate folders to avoid scanning the same folder multiple times
        unique_folders = set()
        for model_type, folder in MODEL_FOLDERS.items():
            if model_type in skip_types:
                continue
            abs_folder = os.path.abspath(folder)
            if not os.path.exists(abs_folder):
                continue
            unique_folders.add(abs_folder)
        # First pass: build a list of files with any missing info
        for abs_folder in unique_folders:
            for file in os.listdir(abs_folder):
                if not (file.lower().endswith(('.safetensors', '.ckpt', '.pt'))):
                    continue
                base = os.path.splitext(file)[0]
                metadata_path = os.path.join(abs_folder, base + '.metadata.json')
                preview_found = False
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    if os.path.exists(os.path.join(abs_folder, base + f'.preview{ext}')):
                        preview_found = True
                        break
                missing = []
                if not os.path.exists(metadata_path):
                    missing.append('metadata')
                if not preview_found:
                    missing.append('preview')
                if missing:
                    files_to_check.append((abs_folder, file, missing))
        total = len(files_to_check)
        if total == 0:
            yield "All models have metadata and preview."
            return
        # Second pass: process each file only once
        for idx, (abs_folder, file, missing) in enumerate(files_to_check, 1):
            if is_cancelled():
                yield f"Cancelled after {idx-1} of {total} files."
                return
            processed = idx
            status = f"[{processed}/{total}] Processing: {file} (missing: {', '.join(missing)})"
            print(status)
            yield '\n'.join(summary + [status])
            try:
                base = os.path.splitext(file)[0]
                file_path = os.path.join(abs_folder, file)
                hash_path = os.path.join(abs_folder, base + '.sha256')
                # Use cached hash if available, else calculate and save
                if os.path.exists(hash_path):
                    with open(hash_path, 'r', encoding='utf-8') as hf:
                        file_hash = hf.read().strip()
                else:
                    file_hash = sha256_of_file(file_path)
                    with open(hash_path, 'w', encoding='utf-8') as hf:
                        hf.write(file_hash)
                api_key = get_civitai_api_key()
                model_version_info = get_model_info_by_hash(file_hash, api_key=api_key)
                if not model_version_info:
                    msg = f"Skipped: {file} ({', '.join(missing)}) - No Civitai match for SHA256"
                    print(msg)
                    summary.append(msg)
                    yield '\n'.join(summary + [f"[{processed}/{total}] ..."])
                    continue
                # Break circular reference before saving
                if 'model' in model_version_info:
                    del model_version_info['model']
                model_info = model_version_info.get('model', {})
                model_info['modelVersions'] = [model_version_info]
                # Ensure model id is present in metadata
                model_info['id'] = model_version_info.get('modelId')
                preview_url = None
                if model_version_info.get('images'):
                    preview_url = model_version_info['images'][0]['url']
                save_preview_and_metadata(abs_folder, file, model_info, preview_url)
                msg = f"Fixed: {file} ({', '.join(missing)})"
                print(msg)
                summary.append(msg)
                yield '\n\n'.join(summary + [f"[{processed}/{total}] ..."])
            except Exception as e:
                msg = f"Failed: {file} ({', '.join(missing)}) - {str(e)}"
                print(msg)
                summary.append(msg)
                yield '\n\n'.join(summary + [f"[{processed}/{total}] ..."])
        yield '\n\n'.join(summary)
    finally:
        clear_running()
