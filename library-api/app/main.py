from fastapi import FastAPI
from app.presentation.api import app as api_app
from app.infrastructure.metrics import router as metrics_router

app = api_app
app.include_router(metrics_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
