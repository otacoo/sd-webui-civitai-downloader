import os
import requests
import json
from .utils import get_model_folders, get_civitai_api_key
from .process_control import is_running, set_running, clear_running, cancel_process, is_cancelled, get_type

def get_latest_model_info(model_id, api_key=None):
    url = f"https://civitai.com/api/v1/models/{model_id}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def cancel_check_model_updates():
    cancel_process()

def check_model_updates():
    if is_running():
        yield f"Another process is already running: {get_type()}"
        return
    set_running('updates')
    try:
        MODEL_FOLDERS = get_model_folders()
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
        # Only process files with .metadata.json
        for abs_folder in unique_folders:
            for file in os.listdir(abs_folder):
                if not (file.lower().endswith(('.safetensors', '.ckpt', '.pt'))):
                    continue
                base = os.path.splitext(file)[0]
                metadata_path = os.path.join(abs_folder, base + '.metadata.json')
                if not os.path.exists(metadata_path):
                    continue
                files_to_check.append((abs_folder, file, metadata_path))
        total = len(files_to_check)
        if total == 0:
            yield "No models found to check for updates."
            return
        api_key = get_civitai_api_key()
        updates = []
        errors = []
        for idx, (abs_folder, file, metadata_path) in enumerate(files_to_check, 1):
            if is_cancelled():
                yield '\n\n'.join(updates + errors + [f"Cancelled after {idx-1} of {total} files."])
                return
            base = os.path.splitext(file)[0]
            status = f"[{idx}/{total}] Checking: {file}"
            yield '\n\n'.join(updates + errors + [status])
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                # Try standard Civitai format first
                model_id = meta.get('id')
                current_version_id = None
                if 'modelVersions' in meta and meta['modelVersions']:
                    mv = meta['modelVersions'][0]
                    current_version_id = mv.get('id')
                # If not found, try Civitai Helper format
                if (not model_id or not current_version_id) and 'civitai' in meta:
                    civ = meta['civitai']
                    model_id = civ.get('modelId')
                    current_version_id = civ.get('id')
                if not model_id or not current_version_id:
                    msg = f"Could not determine model id or version for {file}"
                    errors.append(msg)
                    yield '\n\n'.join(updates + errors)
                    continue
                # Get latest model info from Civitai
                latest_info = get_latest_model_info(model_id, api_key=api_key)
                latest_versions = latest_info.get('modelVersions', [])
                if not latest_versions:
                    msg = f"No versions found for model {model_id} ({file})"
                    errors.append(msg)
                    yield msg
                    continue
                latest_version = latest_versions[0]
                latest_version_id = latest_version.get('id')
                if str(current_version_id) == str(latest_version_id):
                    # Up to date
                    continue
                # New version available (Markdown link)
                model_name = latest_info.get('name', f'Model {model_id}')
                url = f"https://civitai.com/models/{model_id}?modelVersionId={latest_version_id}"
                update_msg = f"NEW VERSION of {model_name} available: [Open in browser]({url})"
                updates.append(update_msg)
                yield '\n\n'.join(updates + errors)
            except Exception as e:
                msg = f"Failed to check {file}: {str(e)}"
                errors.append(msg)
                yield '\n\n'.join(updates + errors)
        # Final summary
        if not updates and not errors:
            yield "All models are up to date."
        elif updates:
            yield '\n\n'.join(updates + errors + [f"Check complete. {len(updates)} model(s) have updates available."])
        elif errors and not updates:
            yield '\n\n'.join(errors + [f"Check complete. No updates found. {len(errors)} error(s) occurred."])
    finally:
        clear_running()
