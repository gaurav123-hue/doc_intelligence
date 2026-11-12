from fastapi import FastAPI
from backend.routers.questions import router as questions_router
from backend.routers.documents import router as documents_router

app = FastAPI(title="AI Document Intelligence API")

app.include_router(questions_router, prefix="/questions")
app.include_router(documents_router)


@app.get("/")
def read_root():
    return {"message": "AI Document Intelligence API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}