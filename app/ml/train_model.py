# import os
# import psycopg2
# import requests
# import cv2 as cv
# import numpy as np

# # =========================
# # PostgreSQL connection details
# # =========================
# DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
# DB_PORT = "6543"
# DB_NAME = "postgres"
# DB_USER = "postgres.nqurgqrqauaxboujobca"
# DB_PASS = "Iot@12345"

# # Base folder to store faces
# BASE_FOLDER = "faces"
# os.makedirs(BASE_FOLDER, exist_ok=True)

# # =========================
# # Step 1: Fetch and download images
# # =========================
# conn = psycopg2.connect(
#     host=DB_HOST,
#     port=DB_PORT,
#     database=DB_NAME,
#     user=DB_USER,
#     password=DB_PASS
# )
# cur = conn.cursor()

# # Fetch all visitor entries
# cur.execute("SELECT name, profile_Image_url FROM public.visitors")
# rows = cur.fetchall()

# for row in rows:
#     name, links = row
#     person_folder = os.path.join(BASE_FOLDER, name.replace(" ", "_"))
#     os.makedirs(person_folder, exist_ok=True)
    
#     urls = links.split("=@#*#@=")
    
#     for idx, url in enumerate(urls, start=1):
#         filename = os.path.join(person_folder, f"{name.split()[0]}_{idx}.jpg")
#         if os.path.exists(filename):
#             print(f"Already exists, skipping: {filename}")
#             continue
#         try:
#             response = requests.get(url, timeout=10)
#             if response.status_code == 200:
#                 with open(filename, "wb") as f:
#                     f.write(response.content)
#                 print(f"Downloaded: {filename}")
#             else:
#                 print(f"Failed to download ({response.status_code}): {url}")
#         except Exception as e:
#             print(f"Error downloading {url}: {e}")

# cur.close()
# conn.close()

# # =========================
# # Step 2: Prepare dataset for training
# # =========================
# haar_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")

# people = []    # list of person names (folder names)
# features = []  # face ROIs
# labels = []    # numeric labels
# skipped_images = []  # log images where no face detected

# for label, person in enumerate(os.listdir(BASE_FOLDER)):
#     person_path = os.path.join(BASE_FOLDER, person)
#     people.append(person)
    
#     for img_name in os.listdir(person_path):
#         img_path = os.path.join(person_path, img_name)
#         img_array = cv.imread(img_path)
#         if img_array is None:
#             print(f"Unable to read image, skipping: {img_path}")
#             continue
#         gray = cv.cvtColor(img_array, cv.COLOR_BGR2GRAY)
#         faces_rect = haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)

#         if len(faces_rect) == 0:
#             skipped_images.append(img_path)
#             continue

#         for (x, y, w, h) in faces_rect:
#             faces_roi = gray[y:y+h, x:x+w]
#             features.append(faces_roi)
#             labels.append(label)

# # =========================
# # Step 3: Train LBPH recognizer
# # =========================
# if len(features) == 0:
#     print("No faces detected. Cannot train recognizer.")
# else:
#     features = np.array(features, dtype=object)
#     labels = np.array(labels)

#     face_recognizer = cv.face.LBPHFaceRecognizer_create()
#     face_recognizer.train(features, labels)

#     os.makedirs("data", exist_ok=True)
#     face_recognizer.save("data/face_trained.yml")
#     np.save("data/people.npy", np.array(people))

#     print("Training complete. face_trained.yml and people.npy saved.")
#     if skipped_images:
#         print("Skipped images (no face detected):")
#         for img in skipped_images:
#             print(img)
import os
import psycopg2
import requests
import cv2 as cv
import numpy as np

# =========================
# PostgreSQL connection details
# =========================
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.nqurgqrqauaxboujobca"
DB_PASS = "Iot@12345"

# Base folder to store faces
BASE_FOLDER = "faces"
os.makedirs(BASE_FOLDER, exist_ok=True)

# =========================
# Step 1: Fetch and download images
# =========================
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)
cur = conn.cursor()

cur.execute("SELECT name, profile_Image_url FROM public.visitors")
rows = cur.fetchall()

for row in rows:
    name, links = row
    person_folder = os.path.join(BASE_FOLDER, name.replace(" ", "_"))
    os.makedirs(person_folder, exist_ok=True)
    
    urls = links.split("=@#*#@=")
    
    for idx, url in enumerate(urls, start=1):
        filename = os.path.join(person_folder, f"{name.split()[0]}_{idx}.jpg")
        if os.path.exists(filename):
            print(f"Already exists, skipping: {filename}")
            continue
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded: {filename}")
            else:
                print(f"Failed to download ({response.status_code}): {url}")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

cur.close()
conn.close()

# =========================
# Step 2: Prepare dataset using DNN face detector
# =========================

# Load OpenCV DNN model
MODEL = "res10_300x300_ssd_iter_140000.caffemodel"
CONFIG = "deploy.prototxt"
net = cv.dnn.readNetFromCaffe(CONFIG, MODEL)

people = []
features = []
labels = []
skipped_images = []

def detect_face_dnn(image):
    """Detect faces using OpenCV DNN SSD model."""
    h, w = image.shape[:2]
    blob = cv.dnn.blobFromImage(cv.resize(image, (300, 300)), 1.0,
                                (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    faces = []
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            faces.append((x1, y1, x2 - x1, y2 - y1))
    return faces

for label, person in enumerate(os.listdir(BASE_FOLDER)):
    person_path = os.path.join(BASE_FOLDER, person)
    people.append(person)
    
    for img_name in os.listdir(person_path):
        img_path = os.path.join(person_path, img_name)
        img_array = cv.imread(img_path)
        if img_array is None:
            print(f"Unable to read image, skipping: {img_path}")
            continue

        gray = cv.cvtColor(img_array, cv.COLOR_BGR2GRAY)
        faces_rect = detect_face_dnn(img_array)

        if len(faces_rect) == 0:
            skipped_images.append(img_path)
            continue

        for (x, y, w, h) in faces_rect:
            faces_roi = gray[y:y+h, x:x+w]
            features.append(faces_roi)
            labels.append(label)

# =========================
# Step 3: Train LBPH recognizer
# =========================
if len(features) == 0:
    print("No faces detected. Cannot train recognizer.")
else:
    features = np.array(features, dtype=object)
    labels = np.array(labels)

    face_recognizer = cv.face.LBPHFaceRecognizer_create()
    face_recognizer.train(features, labels)

    os.makedirs("data", exist_ok=True)
    face_recognizer.save("data/face_trained.yml")
    np.save("data/people.npy", np.array(people))

    print("✅ Training complete. face_trained.yml and people.npy saved.")
    if skipped_images:
        print("⚠️ Skipped images (no face detected):")
        for img in skipped_images:
            print(img)
