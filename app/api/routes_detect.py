from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
import numpy as np
import cv2
import os
import requests
from datetime import datetime

app = FastAPI()

# Paths to ML model and labels
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
DATA_DIR = os.path.join(BASE_DIR, "ml", "data")  # adjust if needed

recognizer_path = os.path.join(DATA_DIR, "face_train.yml")
people_path = os.path.join(DATA_DIR, "people.npy")

# Load face recognizer and labels
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(recognizer_path)
people = np.load(people_path, allow_pickle=True)

# Load Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Confidence threshold
CONFIDENCE_THRESHOLD = 40

class DetectRequest(BaseModel):
    images: List[str]  # list of S3 URLs

# Replace this with the actual URL of your notification endpoint
NOTIFICATION_ENDPOINT = "http://127.0.0.1:8000/raspberry-pi/visitor-detected"

@app.post("/detect-visitor")
def detect_visitor(
    req: DetectRequest,
    owner_id: int = Query(..., description="Owner ID to send notification to")
):
    detected_names = []
    representative_image_url = None

    for url in req.images:
        try:
            # Download image from S3 directly in memory
            img_data = requests.get(url, timeout=10).content
            img_array = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=8,
                minSize=(80, 80)
            )

            for (x, y, w, h) in faces:
                face_roi = gray[y:y+h, x:x+w]
                label, confidence = recognizer.predict(face_roi)

                if confidence < CONFIDENCE_THRESHOLD:
                    label_text = people[label]
                else:
                    label_text = "Unknown visitor"

                detected_names.append(label_text)

                # Use the first detected face as representative
                if not representative_image_url:
                    representative_image_url = url

        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Decide final visitor name by majority vote
    final_name = max(set(detected_names), key=detected_names.count) if detected_names else "Unknown visitor"

    # Prepare payload for Raspberry Pi notification
    payload = {
        "owner_id": owner_id,
        "visitor_name": final_name,
        "image_url": representative_image_url or "",
        "detected_label": final_name
    }

    try:
        # Trigger the visitor notification
        requests.post(NOTIFICATION_ENDPOINT, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send visitor notification: {e}")

    # Return response
    return payload
