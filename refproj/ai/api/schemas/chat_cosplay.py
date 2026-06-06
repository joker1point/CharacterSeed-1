from pydantic import BaseModel

class ChatCosplayRequest(BaseModel):
    session_id: str
    user_input: str
    script_path: str 

class ChatCosplayResponse(BaseModel):
    response: str