from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.db import models
from app import schemas

router = APIRouter()

@router.post("/credentials", response_model=Any)
def save_api_credentials(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    creds_in: schemas.APICredentialCreate
) -> Any:
    """
    Save encrypted API credentials
    """
    # Check if exists
    creds = db.query(models.APICredential).filter(models.APICredential.user_id == current_user.id).first()
    
    encrypted_key = security.encrypt_data(creds_in.api_key)
    encrypted_secret = security.encrypt_data(creds_in.api_secret)
    encrypted_passphrase = security.encrypt_data(creds_in.passphrase)
    
    if creds:
        creds.api_key_encrypted = encrypted_key
        creds.api_secret_encrypted = encrypted_secret
        creds.passphrase_encrypted = encrypted_passphrase
    else:
        creds = models.APICredential(
            user_id=current_user.id,
            api_key_encrypted=encrypted_key,
            api_secret_encrypted=encrypted_secret,
            passphrase_encrypted=encrypted_passphrase,
            exchange="bitget"
        )
        db.add(creds)
    
    db.commit()
    return {"status": "saved"}

@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user
    """
    return current_user

@router.post("/bind_node", response_model=schemas.User)
def bind_node(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    data: schemas.UserUpdate
) -> Any:
    """
    Bind Zeabur Node URL
    """
    current_user.zeabur_url = data.zeabur_url
    db.commit()
    db.refresh(current_user)
    return current_user
