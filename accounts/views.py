from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config.database import get_session

from .models import User
from .schemas import UserLogin, UserRegister
from .security import check_password, create_access_token, hash_password


async def register_user(data: UserRegister, session=Depends(get_session)):
    user = User(username=data.username, password_hash=hash_password(data.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="This username is already taken.")

    return user


async def login_user(data: UserLogin, session=Depends(get_session)):
    query = select(User).where(User.username == data.username)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if user is None or not check_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    access_token = create_access_token(user)
    return {"access_token": access_token, "token_type": "bearer"}
