from app.db.session import SessionLocal
from app.db import models

def init():
    db = SessionLocal()
    try:
        if not db.query(models.InviteCode).first():
            code = models.InviteCode(
                code="TEST1234", 
                exchange="bitget", 
                exchange_uid="12345678"
            )
            db.add(code)
            db.commit()
            print("Created test invite code: TEST1234")
    except Exception as e:
        print(f"Init DB error: {e}")
    finally:
        db.close()
