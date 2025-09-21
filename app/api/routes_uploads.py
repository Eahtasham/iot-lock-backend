# app/api/routes_device.py
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
import os
import shutil
from datetime import datetime

router = APIRouter()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Later: call ML prediction
        # result = predict_face(file_path)

        return JSONResponse({
            "status": "success",
            "filename": filename,
            "message": "Image received"
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
