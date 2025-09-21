# app/main.py
from fastapi import FastAPI
from app.api import routes_device, routes_auth, routes_visits, routes_notify, routes_uploads

app = FastAPI(
    title="IoT Lock API",
    description="API for IoT Lock system. Mobile app or Raspberry Pi can upload images and check status.",
    version="1.0.0"
)

# Upload endpoints
app.include_router(routes_uploads.router, prefix="/upload", tags=["Upload Image"])

# Device endpoints
app.include_router(routes_device.router, prefix="/device", tags=["Device"])

# Auth endpoints
app.include_router(routes_auth.router, prefix="/auth", tags=["Auth"])

# Visits endpoints
app.include_router(routes_visits.router, prefix="/visits", tags=["Visits"])

# Notifications endpoints
app.include_router(routes_notify.router, prefix="/notify", tags=["Notifications"])


@app.get("/")
def read_root():
    return {"message": "FastAPI server is running on the port 8000"}
