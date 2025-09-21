# 🔐 IoT-Lock Backend

This is the backend service for the **IoT-Lock system**, acting as the middle layer between:

* **Raspberry Pi (IoT device)** → captures faces / events
* **Mobile App (React Native)** → receives notifications, manages access
* **Backend (FastAPI + PostgreSQL)** → handles APIs, face recognition, notifications, and database

---

## 📂 Project Structure

```
IOT-LOCK-BACKEND/
│── .gitignore
│── requirements.txt
│── README.md
│── alembic.ini             # (if using migrations)
│
├── app/
│   ├── main.py             # FastAPI entrypoint (server)
│   │
│   ├── api/                # REST API endpoints
│   ├── core/               # configs, logger, security
│   ├── db/                 # database models + session
│   ├── ml/                 # ML models (face detection)
│   │   ├── face_recog.py   # prediction functions
│   │   ├── train_faces.py  # training script
│   │   └── data/           # trained models (face_trained.yml, people.npy)
│   ├── notifications/      # push notification logic
│   └── schemas/            # Pydantic request/response models
│
├── migrations/             # Alembic migration scripts
├── tests/                  # Unit tests
└── venv/                   # Local virtual environment (not pushed to git)
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-org/iot-lock-backend.git
cd iot-lock-backend
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

* **Windows (PowerShell)**

  ```bash
  .\venv\Scripts\activate
  ```
* **Linux/Mac**

  ```bash
  source venv/bin/activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

👉 Server will start at: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📸 Face Recognition Model

* Training script: `app/ml/train_faces.py`
* Trained data: stored in `app/ml/data/face_trained.yml` and `people.npy`
* Prediction: handled by `app/ml/face_recog.py`

To train model:

```bash
python app/ml/train_faces.py
```

---

## 🗄 Database (Postgres on Neon)

* ORM: SQLAlchemy + Alembic
* Connection settings are inside `app/core/config.py`
* Run migrations:

  ```bash
  alembic upgrade head
  ```

---

## 📲 Notifications

* Located in `app/notifications/`
* Will use **Firebase Cloud Messaging (FCM)** to push alerts to the mobile app

---

## 🧪 Testing

Run unit tests with:

```bash
pytest
```

---

## 🚀 Roadmap

* [ ] REST API endpoints for device, auth, visits, notifications
* [ ] Face detection pipeline integration
* [ ] Push notification triggers
* [ ] DB migrations with Alembic
* [ ] Deployment (Docker + server)

---

✅ With this setup, any team member can:

1. Clone repo
2. Setup venv + install requirements
3. Train ML model (optional)
4. Run FastAPI with `uvicorn`
5. Start contributing 🚀
