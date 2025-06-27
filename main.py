from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from database.connection import get_db_connection, init_db
from routers import auth, restaurants, admin, superadmin
from utils.auth import verify_token

security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    init_db()
    yield

app = FastAPI(
    title="Menuzy API",
    description="Restaurant Management System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(restaurants.router, prefix="/restaurants", tags=["Restaurants"])
app.include_router(admin.router, prefix="/admin", tags=["Restaurant Admin"])
app.include_router(superadmin.router, prefix="/superadmin", tags=["Super Admin"])

@app.get("/")
async def root():
    return {"message": "Welcome to Menuzy API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
