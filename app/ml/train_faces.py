import os
import cv2 as cv
import numpy as np

# Folder where images are stored
DATA_DIR = "faces"

# Haar Cascade for face detection
haar_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")

people = []    # list of person names (folder names)
features = []  # face ROIs
labels = []    # numeric labels

# Iterate over each person's folder
for label, person in enumerate(os.listdir(DATA_DIR)):
    person_path = os.path.join(DATA_DIR, person)
    people.append(person)
    
    for img_name in os.listdir(person_path):
        img_path = os.path.join(person_path, img_name)
        img_array = cv.imread(img_path)
        if img_array is None:
            continue
        gray = cv.cvtColor(img_array, cv.COLOR_BGR2GRAY)
        faces_rect = haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)

        for (x, y, w, h) in faces_rect:
            faces_roi = gray[y:y+h, x:x+w]
            features.append(faces_roi)
            labels.append(label)

# Convert to NumPy arrays
features = np.array(features, dtype=object)
labels = np.array(labels)

# Create LBPH recognizer and train
face_recognizer = cv.face.LBPHFaceRecognizer_create()
face_recognizer.train(features, labels)

# Save trained model
face_recognizer.save("face_trained.yml")

# Save names mapping
np.save("people.npy", np.array(people))

print("Training complete. face_trained.yml and people.npy saved.")
