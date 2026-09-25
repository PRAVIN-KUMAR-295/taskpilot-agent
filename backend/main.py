from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import ChatRequest, ChatResponse
from agent import run_agent


app = FastAPI(
    title="TaskPilot AI Agent",
    description="Autonomous AI Agent for Everyday Apps",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "TaskPilot AI Agent is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    result = run_agent(request.message)

    return {
        "response": result
    }