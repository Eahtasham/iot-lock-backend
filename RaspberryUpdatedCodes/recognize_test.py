import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime


def run():
    # Load trained encodings
    data = np.load("face_data.npy", allow_pickle=True).item()
    known_encodings = data["encodings"]
    known_names = data["names"]

    THRESHOLD = 0.5  

    CAPTURE_FOLDER = "captured_faces"
    os.makedirs(CAPTURE_FOLDER, exist_ok=True)

    cap = cv2.VideoCapture(0)
    process_this_frame = True

    screenshot_count = 0           # <-- counter
    MAX_SCREENSHOTS = 30           # <-- limit screenshots

    last_detected_name = "Unknown"

    print("📷 Running face detection... (Auto-stop after 30 screenshots)")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for faster face processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = []
        face_names = []

        if process_this_frame:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for face_encoding in face_encodings:
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                name = "Unknown"
                if len(distances) > 0:
                    min_distance = np.min(distances)
                    if min_distance < THRESHOLD:
                        index = np.argmin(distances)
                        name = known_names[index]

                face_names.append(name)
                last_detected_name = name  # store last person detected

            # -------------------------------
            # Save screenshot ONLY if a face is found
            # -------------------------------
            if face_locations:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(CAPTURE_FOLDER, f"screenshot_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                screenshot_count += 1
                print(f"📸 Screenshot {screenshot_count}/30 saved: {filename}")

                # AUTO STOP WHEN LIMIT REACHED
                if screenshot_count >= MAX_SCREENSHOTS:
                    print("⏹ Auto-stop: Reached 30 screenshots.")
                    break

        process_this_frame = not process_this_frame

        # Drawing boxes + names
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4; right *= 4; bottom *= 4; left *= 4
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Face Recognition", frame)

        # OPTIONAL: Allow manual exit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("⏹ Manual stop by user.")
            break

    cap.release()
    cv2.destroyAllWindows()

    return last_detected_name
