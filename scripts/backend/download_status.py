import threading
import time

from fastapi import APIRouter

router = APIRouter()

_LOCK = threading.Lock()

_DEFAULT_STATUS = {
    "active": False,
    "phase": "idle",
    "message": "",
    "filename": "",
    "model_type": "",
    "folder": "",
    "downloaded": 0,
    "total": 0,
    "percent": 0.0,
    "speed": 0.0,
    "eta": 0.0,
    "updated_at": 0.0,
}

_STATUS = dict(_DEFAULT_STATUS)


def reset_status(**fields):
    with _LOCK:
        _STATUS.clear()
        _STATUS.update(_DEFAULT_STATUS)
        _STATUS["updated_at"] = time.time()
        _STATUS.update(fields)


def set_status(**fields):
    with _LOCK:
        _STATUS.update(fields)
        _STATUS["updated_at"] = time.time()


def get_status():
    with _LOCK:
        return dict(_STATUS)


@router.get("/sd-webui-model-downloader/api/download_status")
async def download_status():
    return get_status()


def on_app_started(demo, app):
    app.include_router(router)
