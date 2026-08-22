from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.middleware("http")
async def log_middleware(request: Request, call_next):
    # Print or inspect
    return JSONResponse({
        "received_path": request.scope.get("path"),
        "raw_path": str(request.scope.get("raw_path")),
        "root_path": request.scope.get("root_path"),
        "headers": dict(request.headers),
        "url": str(request.url)
    })

@app.get("/")
def root():
    return {"message": "root"}
