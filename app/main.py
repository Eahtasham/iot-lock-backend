# app/main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import shutil
import os
from datetime import datetime

app = FastAPI()

# Folder to save uploaded images
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Future: call ML module here
        # result = predict_face(file_path)

        return JSONResponse({
            "status": "success",
            "filename": filename,
            "message": "Image received"
        })

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/")
def read_root():
    return {"message": "FastAPI server is running. POST images to /upload-image"}
