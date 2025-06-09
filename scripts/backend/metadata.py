from fastapi import APIRouter, Request, HTTPException
import os
import json

router = APIRouter()

@router.get('/sd-webui-model-downloader/api/metadata')
async def get_metadata(path: str):
    # Security: Only allow access to .metadata.json files in models/
    if not path.endswith('.metadata.json') or '..' in path or not path.startswith('models/'):
        raise HTTPException(status_code=403, detail="Forbidden")
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(abs_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# In your extension's setup code:
def on_app_started(demo, app):
    app.include_router(router)