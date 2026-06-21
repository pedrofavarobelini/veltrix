from fastapi import APIRouter

from app.modules.chat.schemas import ChatRequest, ChatResponse, ProviderInfo
from app.modules.chat.service import ChatService

router = APIRouter(tags=["Chat"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    return await chat_service.send_message(payload)


@router.get("/providers", response_model=list[ProviderInfo])
def providers():
    return chat_service.list_providers()
