import os
import requests
import psycopg2
import numpy as np
import face_recognition

# ==============================
# Database Credentials
# ==============================
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.nqurgqrqauaxboujobca"
DB_PASS = "Iot@12345"

# ==============================
# Folder to store downloaded images
# ==============================
BASE_FOLDER = "faces"
os.makedirs(BASE_FOLDER, exist_ok=True)

print("======================================")
print(" STEP 1: Fetching & Downloading Images ")
print("======================================")

# ==============================
# Step 1: Fetch & Download Images
# ==============================
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
    name, urls_raw = row
    person_name = name.replace(" ", "_")
    person_folder = os.path.join(BASE_FOLDER, person_name)
    os.makedirs(person_folder, exist_ok=True)

    urls = urls_raw.split("=@#*#@=")

    for idx, url in enumerate(urls, start=1):
        filename = os.path.join(person_folder, f"{person_name}_{idx}.jpg")

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
                print(f"Failed ({response.status_code}) => {url}")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

cur.close()
conn.close()

print("\n======================================")
print(" STEP 2: Creating Face Encodings")
print("======================================")

# ==============================
# Step 2: Create face encodings
# ==============================
known_encodings = []
known_names = []

for person_name in os.listdir(BASE_FOLDER):
    person_folder = os.path.join(BASE_FOLDER, person_name)
    if not os.path.isdir(person_folder):
        continue

    print(f"\nProcessing person: {person_name}")

    for img_file in os.listdir(person_folder):
        img_path = os.path.join(person_folder, img_file)

        try:
            image = face_recognition.load_image_file(img_path)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) == 0:
                print(f"  ⚠ No face found in {img_file}, skipping.")
                continue

            known_encodings.append(encodings[0])
            known_names.append(person_name)
            print(f"  ✓ Encoded: {img_file}")

        except Exception as e:
            print(f"  ⚠ Error processing {img_file}: {e}")

# Save the trained data
data = {
    "encodings": known_encodings,
    "names": known_names
}

np.save("face_data.npy", data)

print("\n======================================")
print(" Training Complete!")
print(" Saved encodings to face_data.npy")
print("======================================")
