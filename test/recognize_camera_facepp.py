# recognize_camera_facepp.py
import cv2
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# ---------- HARD-CODED CREDENTIALS (as requested) ----------
API_KEY = "OMvDsiDN-dObDPZYbo6zsutTIdbpPqzA"
API_SECRET = "gpk5pUDZNBPBqIE8dkScvpILzK_Redxe"
# ----------------------------------------------------------

FACEPP_SEARCH = "https://api-us.faceplusplus.com/facepp/v3/search"
OUTER_ID = "iot_door_faces"
TOKEN_MAP_FILE = "data/face_tokens_map.json"

# Backend notify endpoint
NOTIFY_URL = "https://iot-lock-backend.onrender.com/api/notify/raspberry-pi/visitor-detected"

# Tunables
CAM_INDEX = 0                 # change if you have multiple cameras
PROCESS_EVERY_N_FRAMES = 5    # only run recognition every N frames (reduce API calls)
CONFIDENCE_THRESHOLD = 65.0   # Face++ confidence threshold (tune 65-90)
COOLDOWN_SECONDS = 20         # don't notify again for same person within this many seconds
API_DELAY = 0.35              # small delay after each Face++ call

# load token->name map
def load_token_map():
    p = Path(TOKEN_MAP_FILE)
    if not p.exists():
        print("Token map not found at", TOKEN_MAP_FILE)
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        print("Failed to read token map:", e)
        return {}

def facepp_search(image_bytes):
    files = {"image_file": ("probe.jpg", image_bytes)}
    data = {"api_key": API_KEY, "api_secret": API_SECRET, "outer_id": OUTER_ID}
    r = requests.post(FACEPP_SEARCH, data=data, files=files, timeout=12)
    r.raise_for_status()
    return r.json()

def notify_owner(owner_id, visitor_name, detected_label="Known"):
    payload = {
        "visitor_name": visitor_name,
        "detected_label": detected_label
    }
    try:
        r = requests.post(NOTIFY_URL, params={"owner_id": owner_id}, json=payload, timeout=6)
        print(f"[NOTIFY] owner={owner_id} visitor='{visitor_name}' status={r.status_code}")
    except Exception as e:
        print("[NOTIFY ERROR]", e)

def main():
    token_map = load_token_map()
    if not token_map:
        print("Token map empty - run enrollment first.")
        return

    # Prepare local Haar cascade for cheap face detection
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("Cannot open camera index", CAM_INDEX)
        return

    frame_idx = 0
    last_seen = {"_cooldown": COOLDOWN_SECONDS}
    owner_id = 12  # default owner id; change if needed

    print("Starting camera. Press 'q' to quit.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame from camera")
                break
            frame_idx += 1

            # Show frame immediately (will overlay boxes later)
            display = frame.copy()

            # Only process every Nth frame
            if frame_idx % PROCESS_EVERY_N_FRAMES == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # detect faces (returns x,y,w,h)
                rects = cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80,80))
                if len(rects) > 0:
                    # pick largest face (likely the person in front)
                    rects = sorted(rects, key=lambda r: r[2]*r[3], reverse=True)
                    x,y,w,h = rects[0]
                    # add small margin
                    margin = int(0.2 * max(w, h))
                    x1 = max(0, x - margin)
                    y1 = max(0, y - margin)
                    x2 = min(frame.shape[1], x + w + margin)
                    y2 = min(frame.shape[0], y + h + margin)
                    face_crop = frame[y1:y2, x1:x2].copy()
                    # encode to jpg bytes
                    ret2, jpg = cv2.imencode(".jpg", face_crop)
                    if ret2:
                        try:
                            res = facepp_search(jpg.tobytes())
                        except requests.HTTPError as he:
                            print("Face++ HTTP error:", he)
                            res = {}
                        except Exception as e:
                            print("Face++ request failed:", e)
                            res = {}

                        # draw the detection rectangle
                        cv2.rectangle(display, (x1, y1), (x2, y2), (0,255,0), 2)

                        results = res.get("results", [])
                        if results:
                            top = results[0]
                            face_token = top.get("face_token")
                            confidence = float(top.get("confidence", 0.0))
                            mapped_name = token_map.get(face_token)
                            label = f"{mapped_name or 'Unknown'} {confidence:.1f}"
                            cv2.putText(display, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
                            print(f"[{datetime.now().isoformat()}] token={face_token} conf={confidence:.2f} mapped={mapped_name}")
                            now = time.time()
                            if confidence >= CONFIDENCE_THRESHOLD and mapped_name:
                                last = last_seen.get(mapped_name, 0)
                                if now - last > last_seen["_cooldown"]:
                                    print(f"Recognized {mapped_name} — notifying owner {owner_id}")
                                    notify_owner(owner_id, mapped_name, "Known")
                                    last_seen[mapped_name] = now
                                else:
                                    print(f"Recognized {mapped_name} — but in cooldown ({now-last:.1f}s)")
                            else:
                                # unknown / low confidence
                                last = last_seen.get("Unknown", 0)
                                if now - last > last_seen["_cooldown"]:
                                    print("Unknown or low confidence — notifying as Unknown")
                                    notify_owner(owner_id, "Unknown", "Unknown")
                                    last_seen["Unknown"] = now
                                else:
                                    print(f"Unknown in cooldown ({now-last:.1f}s)")
                        else:
                            # no match returned by face++ (no candidates)
                            cv2.putText(display, "No match", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
                            print("Face++ returned no results.")
                        time.sleep(API_DELAY)

            # show frame
            cv2.imshow("DoorCam - press q to quit", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera stopped.")

if __name__ == "__main__":
    main()
