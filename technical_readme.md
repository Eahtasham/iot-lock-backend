# 🔐 IoT Lock System - Technical Deep Dive

> **Document Purpose**: This is a technical reference designed for engineering interviews and architectural review. It explains the *why* and *how* behind the IoT Lock system, going beyond simple usage instructions to cover design decisions, trade-offs, and core algorithms.

---

## 🏗️ System Architecture

The IoT Lock system is a distributed application spanning three distinct tiers: **Edge (IoT)**, **Cloud Backend**, and **Mobile Client**.

### High-Level Data Flow

1.  **Edge Detection**: A Raspberry Pi constantly monitors a video feed. When a person is detected, it runs a **Hybrid Image Quality Selection** algorithm to pick the best frame.
2.  **Local Recognition**: To minimize latency and bandwidth, face recognition happens *locally* on the Pi using `face_recognition` (dlib) and a trained KNN/SVM model.
3.  **Cloud Sync**:
    *   The best image is uploaded to **AWS S3** directly.
    *   Metadata (Who? When? Image URL?) is sent to the **FastAPI Backend**.
4.  **Notification Dispatch**: The backend logs the visit in **PostgreSQL** and triggers a push notification via **Expo (FCM)** to the owner's mobile device.
5.  **User Action**: The mobile app (React Native) receives the alert, showing the visitor's face. The user can remotely unlock the door (future scope) or talk to the visitor.

---

## 🛠️ Technology Stack & Rationale

| Layer | Technology | Why this choice? |
| :--- | :--- | :--- |
| **Backend** | **FastAPI (Python)** | High performance (ASGI), native async support for handling concurrent I/O (S3 uploads, DB writes), and automatic OpenAPI documentation. |
| **Database** | **PostgreSQL** | robust relational integrity. We use **Raw SQL** (`asyncpg`) instead of an ORM for maximum query performance and explicit control over complex joins (e.g., visit analytics). |
| **Edge AI** | **OpenCV + Dlib** | Run on Raspberry Pi. `dlib` is the industry standard for 99% accuracy face encodings. OpenCV handles the video feed and image preprocessing. |
| **Storage** | **AWS S3** | Scalable, durable object storage for images. Pre-signed URLs or public buckets offload bandwidth from the API server. |
| **Notifications** | **Expo Push API** | Abstracts FCM (Android) and APNs (iOS) complexities, allowing a single API call to reach any device. |

---

## 🧠 Core Algorithmic Details

### 1. Hybrid Image Quality Selector (`iotgrp6.py`)
**Problem**: Sending every frame to the server wastes bandwidth. Sending a blurry frame makes recognition impossible.
**Solution**: A lightweight scoring algorithm running on the Pi to select the *single best frame* from a burst.

The algorithm computes a weighted score based on four metrics:

```python
Score = (0.35 * Focus) + (0.15 * Brightness) + (0.30 * Contrast) + (0.20 * FaceSize)
```

1.  **Focus Score (Laplacian Variance)**:
    *   `cv2.Laplacian(gray, cv2.CV_64F).var()`
    *   High variance = sharp edges (in focus). Low variance = blurry.
    *   *Why?* Blurry faces are the #1 cause of recognition failure.
2.  **Brightness (HSV - V channel)**:
    *   Ensures the face isn't too dark (underexposed) or washed out (overexposed).
3.  **Contrast (Std Dev of Grayscale)**:
    *   `np.std(gray)`
    *   Higher contrast usually means better defined features for the HOG (Histogram of Oriented Gradients) face detector.
4.  **Face Size**:
    *   Larger faces contain more pixels, leading to more accurate 128-d face encodings.

### 2. Local Face Recognition
Instead of sending images to a cloud API (slow, privacy risk), we use:
*   **HOG (Histogram of Oriented Gradients)** to find face locations.
*   **ResNet-34** (via `dlib`) to map the face pixels to a 128-dimensional vector space.
*   **Euclidean Distance**: We compare the live vector against known encodings (`face_trained.yml`). If distance < 0.6 (threshold), it's a match.

---

## 🔌 API Route Deep Dive

The backend handles orchestration. Here is the breakdown of key endpoints in `app/api/`.

### 1. Notification & Detection (`routes_notify.py`)

This is the "heartbeat" of the system, connecting the Pi to the User.

#### `POST /api/notify/raspberry-pi/visitor-detected`
*   **Called By**: Raspberry Pi (after selecting the best image).
*   **Payload**: `owner_id`, `visitor_name`, `image_url`, `detected_label`.
*   **Logic**:
    1.  **Immediate Notification**: Queues a background task (`BackgroundTasks`) to send a push notification immediately. This ensures the Pi gets a `200 OK` response instantly (low latency) while the heavy lifting happens asynchronously.
    2.  **Data Recording**: calls `insert_visit` (Raw SQL) to log the event in the `visits` table.
*   **Interview Tip**: Mention the use of `BackgroundTasks`. It prevents the Pi from "hanging" while waiting for the notification service (Expo) to respond.

#### `POST /api/notify/detect-visitor`
*   **Purpose**: An alternative endpoint that double-checks the visitor ID against the database.
*   **Logic**:
    *   Takes a clean `user_name` (e.g., "John_Doe").
    *   Queries `visitors` table to find their ID.
    *   If ID found -> Status "Known". Else -> Status "Unknown".
    *   Logs the visit and triggers the alert.

### 2. File Uploads (`routes_uploads.py`)

#### `POST /upload/upload-image`
*   **Security**: Protected by a custom header `x-api-key`. This is a lightweight security measure suitable for the Pi.
*   **Logic**:
    *   Accepts a raw file stream (`UploadFile`).
    *   Generates a unique filename: `timestamp + uuid`.
    *   Streams the file *directly* to AWS S3 using `boto3`.
    *   **Optimization**: It uses `s3_client.upload_fileobj` which streams data, rather than loading the whole file into RAM. This keeps the backend memory footprint low.

### 3. Database Layer (`app/db/crud.py`)

We deliberately avoided an ORM like SQLAlchemy for the *operations* (though we might define models for migration).
**Why Raw SQL (`asyncpg`)?**
*   **Performance**: `asyncpg` is significantly faster than `psycopg2` or ORMs because it uses the native PostgreSQL binary protocol.
*   **Complex Aggregation**: The `get_visit_statistics` function helps us build the dashboard:
    ```sql
    SELECT
        COUNT(*) as total_visits,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_visits,
        ...
    FROM visits WHERE owner_id = $1
    ```
    Writing this in an ORM is often verbose and generates inefficient subqueries. Raw SQL is clean and readable.

### 4. Device Management (`routes_device.py`)

#### `POST /api/device/register`
*   **Purpose**: Registers the mobile app's `ExpoPushToken`.
*   **Logic**: Uses "Upsert" logic (Check if exists -> Update, else -> Insert). This ensures one user doesn't end up with duplicate tokens for the same device.

---

## 💾 Database Schema Design

*   **`owners`**: System users (Login info).
*   **`visitors`**: Known people directory (Name, Profile Pic).
*   **`visits`**: The core event log.
    *   `visitor_id` (FK to visitors, Nullable for strangers).
    *   `owner_id` (FK).
    *   `image_url` (S3 link).
    *   `status` (pending/granted/denied).
    *   `timestamp`.
*   **`device_tokens`**: Stores FCM tokens for push notifications.

---

## 🚀 Key Interview Questions & Answers

**Q: Why do face recognition on the Pi instead of the server?**
**A:** Privacy and Latency. Creating a 128-d vector on the Pi is fast. Sending a heavy image to the server for processing adds 1-2 seconds of network lag. We want the door to open *instantly*. Also, sending only metadata protects privacy better than streaming raw video to the cloud.

**Q: How do you handle network failures on the Pi?**
**A:** Currently, the Pi attempts to upload. In a production version, we would implement a **local queue (SQLite/Redis)** on the Pi. If the internet is down, it saves the event locally and pushes it when connectivity is restored.

**Q: Why `async` FastAPI?**
**A:** The backend is I/O bound (waiting for S3, waiting for Database, waiting for Expo). Python's `asyncio` allows a single thread to handle thousands of these waiting connections concurrently, making it much more scalable than Flask/Django for this use case.

