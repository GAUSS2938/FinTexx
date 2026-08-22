import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Inspector")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "FinTex AI Financial Companion"}

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, full_path: str):
    return {
        "status": "inspector",
        "full_path": full_path,
        "scope_path": request.scope.get("path"),
        "scope_root_path": request.scope.get("root_path"),
        "url_path": request.url.path,
        "method": request.method,
        "headers": dict(request.headers)
    }
