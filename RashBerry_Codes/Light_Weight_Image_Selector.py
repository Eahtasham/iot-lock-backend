import os
import cv2
import numpy as np
import shutil
import requests

# ==========================================================
# ⚡ Lightweight Hybrid Image Quality Selector
# Author: GPT-5
# ==========================================================

IMAGE_DIR = "photos"    # folder with input images
SELECT_DIR = "select"   # folder to store best image
API_URL = "https://iot-lock-backend.onrender.com/upload/upload-image"

# ==========================================================
# Quality Metric Functions
# ==========================================================

def focus_score(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def brightness_score(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return np.mean(hsv[:, :, 2])

def contrast_score(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return np.std(gray)

def face_size_score(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return 0
    (x, y, w, h) = max(faces, key=lambda b: b[2] * b[3])
    return (w * h) / (image.shape[0] * image.shape[1])

def hybrid_score(image):
    f = focus_score(image)
    b = brightness_score(image)
    c = contrast_score(image)
    fs = face_size_score(image)

    metrics = np.array([f, b, c, fs])
    metrics = np.nan_to_num(metrics)
    normalized = (metrics - np.min(metrics)) / (np.ptp(metrics) + 1e-9)
    weights = np.array([0.35, 0.15, 0.30, 0.20])
    return np.dot(normalized, weights)

# ==========================================================
# Upload Function
# ==========================================================

API_KEY = "supersecret123"  # <-- replace with your actual key

def upload_image(filepath):
    headers = {"x-api-key": API_KEY}  # add the required header
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "image/jpeg")}
        try:
            response = requests.post(API_URL, headers=headers, files=files)
            if response.status_code == 200:
                print(f"✅ Image uploaded successfully: {filepath}")
                print(f"📤 Server response: {response.text}")
            else:
                print(f"❌ Upload failed ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"❌ Error uploading: {e}")

# ==========================================================
# Main Function
# ==========================================================

def select_best_image():
    os.makedirs(SELECT_DIR, exist_ok=True)
    best_score, best_filename = -1, None

    for filename in os.listdir(IMAGE_DIR):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        path = os.path.join(IMAGE_DIR, filename)
        img = cv2.imread(path)
        if img is None:
            continue

        score = hybrid_score(img)
        print(f"{filename}: {score:.4f}")

        if score > best_score:
            best_score = score
            best_filename = filename

    if best_filename:
        selected_path = os.path.join(SELECT_DIR, best_filename)
        shutil.copy(os.path.join(IMAGE_DIR, best_filename), selected_path)
        print(f"\n✅ Best image selected: {best_filename} (score={best_score:.4f})")
        print(f"📁 Saved to: {selected_path}")

        # Upload the image
        upload_image(selected_path)
    else:
        print("❌ No valid images found.")

# ==========================================================
# Run
# ==========================================================

if __name__ == "__main__":
    select_best_image()
