import cv2
import face_recognition
import os
import numpy as np

BASE_DIR = "known_faces"
encodings = []
names = []

FRAME_SKIP = 5  # process every 5th frame

for person in os.listdir(BASE_DIR):
    person_path = os.path.join(BASE_DIR, person)
    if not os.path.isdir(person_path):
        continue

    print(f"Processing: {person}")

    for file in os.listdir(person_path):
        if not file.lower().endswith((".mp4", ".mov", ".avi")):
            continue

        video_path = os.path.join(person_path, file)
        cap = cv2.VideoCapture(video_path)

        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % FRAME_SKIP != 0:
                continue

            small = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
            rgb = small[:, :, ::-1]

            locations = face_recognition.face_locations(rgb, model="hog")
            encs = face_recognition.face_encodings(rgb, locations)

            if len(encs) == 1:  # only accept clean single-face frames
                encodings.append(encs[0])
                names.append(person)
        
        cap.release()

np.save("encodings.npy", encodings)
np.save("names.npy", names)

print("✅ Training complete")
print(f"Total encodings: {len(encodings)}")
