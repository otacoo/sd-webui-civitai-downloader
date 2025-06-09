from fastapi import APIRouter, Request, HTTPException
import os
import json

router = APIRouter()

@router.post('/sd-webui-model-downloader/api/delete_model')
async def delete_model(request: Request):
    data = await request.json()
    model_path = data.get('model_path')
    if not model_path:
        raise HTTPException(status_code=400, detail='No model_path provided')

    # Security: Only allow deletion within the models directory
    if '..' in model_path or not model_path.startswith('models/'):
        raise HTTPException(status_code=403, detail='Forbidden')
    abs_model_path = os.path.abspath(model_path)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../models'))

    # Resolve real paths to support symlinks/junctions
    abs_model_real = os.path.realpath(abs_model_path)
    base_dir_real = os.path.realpath(base_dir)

    print(f"[delete_model] model_path: {model_path}")
    print(f"[delete_model] abs_model_path: {abs_model_path}")
    print(f"[delete_model] abs_model_real: {abs_model_real}")
    print(f"[delete_model] base_dir: {base_dir}")
    print(f"[delete_model] base_dir_real: {base_dir_real}")

    # Allow if the real path contains /models/ or \models\ after the drive letter
    norm_real = abs_model_real.replace('\\', '/').lower()
    if '/models/' not in norm_real:
        raise HTTPException(status_code=403, detail='Invalid model path')

    try:
        if os.path.exists(abs_model_path):
            os.remove(abs_model_path)
            # Delete related files
            related_exts = [
                '.metadata.json', '.civitai.info', '.webp', '.jpg', '.jpeg', '.png',
                '.preview.jpg', '.preview.jpeg', '.preview.png', '.preview.webp'
            ]
            base_no_ext = os.path.splitext(abs_model_path)[0]
            for ext in related_exts:
                related_file = base_no_ext + ext
                if os.path.exists(related_file):
                    os.remove(related_file)
            return {"success": True, "message": f"Model and related files deleted: {abs_model_path}"}
        else:
            raise HTTPException(status_code=404, detail='File does not exist')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# In your extension's setup code:
def on_app_started(demo, app):
    app.include_router(router)
