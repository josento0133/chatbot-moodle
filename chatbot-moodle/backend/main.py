from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routers import chat, history, exercise, progress

app = FastAPI(title="Chatbot Académico API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()


app.include_router(chat.router)
app.include_router(history.router)
app.include_router(exercise.router)
app.include_router(progress.router)
