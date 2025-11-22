# enroll_images_facepp.py (robust version)
import os
import json
import time
import requests
import sys
from pathlib import Path

# ---------- HARD-CODED CREDENTIALS (as requested) ----------
API_KEY = "OMvDsiDN-dObDPZYbo6zsutTIdbpPqzA"
API_SECRET = "gpk5pUDZNBPBqIE8dkScvpILzK_Redxe"
# ----------------------------------------------------------

FACEPP_DETECT = "https://api-us.faceplusplus.com/facepp/v3/detect"
FACEPP_FACESET_CREATE = "https://api-us.faceplusplus.com/facepp/v3/faceset/create"
FACEPP_FACESET_ADD = "https://api-us.faceplusplus.com/facepp/v3/faceset/addface"

OUTER_ID = "iot_door_faces"
DEFAULT_KNOW_DIR = "known_faces"
DATA_MAP = "data/face_tokens_map.json"

# safety params
BATCH_SIZE = 10
API_SLEEP = 0.30

os.makedirs("data", exist_ok=True)

# allow passing custom folder path: python enroll_images_facepp.py path/to/folder
if len(sys.argv) > 1:
    KNOW_DIR = sys.argv[1]
else:
    KNOW_DIR = DEFAULT_KNOW_DIR

if not os.path.exists(KNOW_DIR):
    print(f"'{KNOW_DIR}' not found. Creating it now. Please add subfolders named after persons, each containing images.")
    os.makedirs(KNOW_DIR, exist_ok=True)
    print("Created folder. Add folders like 'known_faces/Anupam' with images, then rerun the script.")
    sys.exit(0)

# load existing token map if present
def load_token_map():
    if os.path.exists(DATA_MAP):
        try:
            with open(DATA_MAP, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Warning: failed to load existing token map:", e)
    return {}

def save_token_map(token_map):
    with open(DATA_MAP, "w") as f:
        json.dump(token_map, f, indent=2)

def call_detect(image_bytes):
    files = {"image_file": ("img.jpg", image_bytes)}
    data = {"api_key": API_KEY, "api_secret": API_SECRET}
    r = requests.post(FACEPP_DETECT, data=data, files=files, timeout=20)
    r.raise_for_status()
    return r.json()

def ensure_faceset():
    data = {"api_key": API_KEY, "api_secret": API_SECRET, "outer_id": OUTER_ID, "display_name": OUTER_ID}
    r = requests.post(FACEPP_FACESET_CREATE, data=data, timeout=10)
    # if faceset exists, Face++ returns 400 with error_message "FACESET_EXIST" — that's fine
    try:
        j = r.json()
    except Exception:
        j = {}
    if r.status_code == 200:
        print("Faceset created.")
    else:
        msg = j.get("error_message") or r.text
        print("Faceset create response:", r.status_code, msg)

def add_tokens_batch(tokens):
    """Try adding tokens in one batch. Return JSON or raise requests.HTTPError."""
    data = {"api_key": API_KEY, "api_secret": API_SECRET, "outer_id": OUTER_ID, "face_tokens": ",".join(tokens)}
    r = requests.post(FACEPP_FACESET_ADD, data=data, timeout=20)
    # do not raise here; caller will inspect
    return r

def add_tokens_safely(tokens, token_map, person_name):
    """Add tokens but handle errors. Update token_map for tokens that end up added/known."""
    if not tokens:
        return

    # First try batch add
    print(f"  Trying to add batch of {len(tokens)} tokens for {person_name}")
    r = add_tokens_batch(tokens)
    try:
        j = r.json()
    except Exception:
        j = {}
    if r.status_code == 200:
        # success: update map
        added = j.get("face_added", [])
        if added is None:
            added = []
        for t in added:
            token_map[t] = person_name
        # Face++ may return 'face_existed' list too
        existed = j.get("face_existed", [])
        for t in existed:
            token_map[t] = person_name
        print(f"  Batch add success. added={len(added)} existed={len(existed)}")
        time.sleep(API_SLEEP)
        return
    else:
        # Batch failed; print error and try per-token to detect bad ones
        err_msg = j.get("error_message") or r.text
        print(f"  Batch add failed (status={r.status_code}): {err_msg}")
        # Try individual adds to detect which tokens are problematic
        for t in tokens:
            if t in token_map:
                print(f"    token {t} already in local map; skipping")
                continue
            print(f"    Trying single token add: {t} ...")
            r2 = add_tokens_batch([t])  # faceset/addface accepts single token as comma-separated with one item
            try:
                j2 = r2.json()
            except Exception:
                j2 = {}
            if r2.status_code == 200:
                added = j2.get("face_added", [])
                existed = j2.get("face_existed", [])
                if added:
                    token_map[t] = person_name
                    print(f"      added {t}")
                elif existed:
                    token_map[t] = person_name
                    print(f"      already existed {t}")
                else:
                    # no useful info, but consider it added
                    token_map[t] = person_name
                    print(f"      added (no explicit list) {t}")
            else:
                em = j2.get("error_message") or r2.text
                print(f"      failed to add token {t}: status={r2.status_code} error={em}")
                # if error indicates token invalid or expired, skip permanently
                # continue for others
            time.sleep(API_SLEEP)

def process_person_folder(path, token_map):
    tokens_for_person = []
    for fn in sorted(os.listdir(path)):
        fpath = os.path.join(path, fn)
        if not os.path.isfile(fpath):
            continue
        if not fn.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            print(f"  skipping non-image file: {fn}")
            continue
        with open(fpath, "rb") as f:
            img_bytes = f.read()
        try:
            res = call_detect(img_bytes)
            faces = res.get("faces", [])
            if not faces:
                print(f"  {fn}: no face detected")
                continue
            face_token = faces[0].get("face_token")
            if face_token:
                if face_token in token_map:
                    print(f"  {fn}: token already in map, skipping add: {face_token}")
                else:
                    tokens_for_person.append(face_token)
                    print(f"  {fn}: token={face_token}")
            time.sleep(API_SLEEP)
        except Exception as e:
            print(f"  {fn}: detect error: {e}")
    return tokens_for_person

def main():
    print("Loading existing token map (if any)...")
    token_map = load_token_map()
    print("Loaded", len(token_map), "existing tokens")

    print("Ensuring faceset exists (may return 400 if already created)...")
    try:
        ensure_faceset()
    except Exception as e:
        print("Faceset create warning:", e)

    people_folders = sorted([d for d in os.listdir(KNOW_DIR) if os.path.isdir(os.path.join(KNOW_DIR, d))])
    if not people_folders:
        print(f"No subfolders found in '{KNOW_DIR}'. Add person folders (each containing images) and rerun.")
        return

    for person_name in people_folders:
        folder = os.path.join(KNOW_DIR, person_name)
        print("Processing person:", person_name)
        tokens = process_person_folder(folder, token_map)
        # Remove tokens already in token_map (defensive)
        tokens_to_add = [t for t in tokens if t not in token_map]
        if not tokens_to_add:
            print(f"  No new tokens to add for {person_name}")
            continue
        # Add tokens with safe method
        add_tokens_safely(tokens_to_add, token_map, person_name)
        # Save token map after each person so progress is persisted
        save_token_map(token_map)
        print(f"  After {person_name}, total tokens stored locally: {len(token_map)}")

    # final save
    save_token_map(token_map)
    print("Saved face_token -> person map to", DATA_MAP)
    print("Done.")

if __name__ == "__main__":
    main()
