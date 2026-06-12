# backend/app/api/routes/nvidia.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.auth import get_current_user
from app.db.models import User
from app.services.nvidia import nvidia_service

router = APIRouter()

@router.get("/nvidia/test")
async def test_nvidia_connection(_user: User = Depends(get_current_user)):
    """
    Verifies connection to the NVIDIA AI Inference API catalog
    by performing a simple model call.
    """
    if not nvidia_service.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NVIDIA_API_KEY environment variable is not configured. Please add it to your .env file."
        )

    test_messages = [
        {"role": "system", "content": "You are a boardroom assistant. Respond with exactly the word 'OK' to verify connectivity."},
        {"role": "user", "content": "Hello"}
    ]

    try:
        response_text = await nvidia_service.chat_completion(
            messages=test_messages,
            temperature=0.0,
            max_tokens=10
        )
        return {
            "status": "success",
            "message": "NVIDIA AI Inference catalog connection verified successfully!",
            "model_configured": nvidia_service.model_name,
            "response": response_text.strip()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NVIDIA API Catalog verification failed: {str(e)}"
        )
