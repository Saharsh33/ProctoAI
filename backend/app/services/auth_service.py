from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token

def signup_user(db: Session, name, email, password, user_type):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        user_type=user_type,
        user_image="default.png",
        user_login=0
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db: Session, email, password):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        return None

    token = create_access_token({"sub": user.email, "uid": user.uid, "role": user.user_type})
    return token