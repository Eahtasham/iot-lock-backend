# app/main.py
from fastapi import FastAPI
# Import all route modules
from app.api.routes_auth import router as auth_router
from app.api.routes_visits import router as visits_router
from app.api.routes_device import router as device_router
from app.api.routes_notify import router as notify_router
from app.api.routes_visitors import router as visitors_router
from app.api import routes_uploads as routes_uploads


app = FastAPI(
    title="IoT Lock API",
    description="API for IoT Lock system. Mobile app or Raspberry Pi can upload images and check status.",
    version="1.0.0"
)

app.include_router(routes_uploads.router, prefix="/upload", tags=["Upload Image"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(visits_router, prefix="/api/visits", tags=["Visits"])
app.include_router(device_router, prefix="/api/device", tags=["Device Management"])
app.include_router(notify_router, prefix="/api/notify", tags=["Notifications"])
app.include_router(visitors_router, prefix="/api/visitors", tags=["Visitors"])


@app.get("/")
def read_root():
    return {"message": "FastAPI server is running on the port 8000"}
