import os
import uuid
import asyncio
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from fastapi import APIRouter, File, UploadFile, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
print("AWS_DEFAULT_REGION", os.getenv("AWS_DEFAULT_REGION"))


s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_DEFAULT_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def require_api_key(x_api_key: str = Header(...)):
    expected = os.getenv("API_KEY")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return x_api_key


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), api_key: str = Depends(require_api_key)):
    """
    Uploads the received file to S3 and returns a permanent public URL.
    - Protects the route with a simple API key in header `x-api-key`.
    """
    try:
        # Validate input
        if not file.content_type or not file.content_type.startswith("image/"):
            return JSONResponse({"status": "error", "message": "Only image files are allowed"}, status_code=400)

        bucket = os.environ.get("S3_BUCKET_NAME")
        region = os.environ.get("AWS_DEFAULT_REGION")
        if not bucket or not region:
            return JSONResponse({"status": "error", "message": "S3_BUCKET_NAME or AWS_DEFAULT_REGION not configured"}, status_code=500)

        # Build a unique object key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(file.filename)[1] or ""
        key = f"uploads/{timestamp}_{uuid.uuid4().hex}{ext}"

        # Reset file pointer
        file.file.seek(0)

        # Upload with public-read ACL so link is permanent
        extra_args = {"ContentType": file.content_type}
        await asyncio.to_thread(
            s3_client.upload_fileobj,
            file.file,
            bucket,
            key,
            ExtraArgs=extra_args
        )

        # Construct the permanent URL
        file_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

        return JSONResponse({
            "status": "success",
            "filename": key,
            "url": file_url,
            "message": "Image uploaded successfully"
        })
    except ClientError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
