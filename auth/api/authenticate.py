import requests
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from gotrue.types import AuthResponse
from gotrue.errors import AuthApiError

from auth.services.supabase import supabase
from auth.settings import SUPABASE_URL, SUPABASE_KEY
from auth.api.router import AuthRouter
from auth.schemas.auth import LoginRequest, LoginResponse
from auth.schemas.auth import TokenValidateRequest, TokenValidateResponse
from auth.schemas.auth import LogoutRequest, LogoutResponse
from auth.schemas.auth import SignUpRequest, SignUpResponse

from auth.schemas.user import UserCreate

from auth.managers.user import users_manager

from auth.api.deps.db import get_db

authenticate_router = AuthRouter()

async def _login(email: str, password: str):
    response: AuthResponse = supabase.auth.sign_in_with_password({ "email": email, "password": password })
    return response.session.access_token, response.user.id


async def _logout(token: str) -> bool:
    url = f"{SUPABASE_URL}/auth/v1/logout"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)
    print(response)
    if response.status_code != 200:
        return False
    return True

async def _validate_token(access_token: str) -> bool:
    response = supabase.auth.get_user(access_token)
    return response.user.aud == 'authenticated'

async def _sign_up(email: str, password: str):
    response = supabase.auth.sign_up(
        credentials={"email": f"{email}", "password": "{password}"}
    )
    if response.user.id:
        return response.user.id

    


@authenticate_router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db_session: Session = Depends(get_db)
) -> LoginResponse:
    access_token, supabase_user_id = await _login(
        email=request.email, 
        password=request.password
    )
    
    _obj_in = UserCreate(name=supabase_user_id)

    user = users_manager.create_or_update(
        db_session=db_session,
        obj_in=_obj_in
    )

    return LoginResponse(
        access_token=access_token
    )

@authenticate_router.post("/validate-token", response_model=TokenValidateResponse)
async def validate_token(request: TokenValidateRequest) -> TokenValidateResponse:
    # print(test)
    try:
        is_token_valid: bool = await _validate_token(access_token=request.access_token)
        return TokenValidateResponse(user_is_valid=is_token_valid)
    except AuthApiError as e:
        return TokenValidateResponse(user_is_valid=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@authenticate_router.post("/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest) -> LogoutResponse:
    try:
        await _logout(token=request.access_token)
        return LogoutResponse()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@authenticate_router.post("/sign-up", response_model=SignUpResponse)
async def sign_up(
    request: SignUpRequest,
    db_session: Session = Depends(get_db)
) -> SignUpResponse:
    try:

        supabase_user_id = await _sign_up(
            email=request.email,
            password=request.password
        )

        # just supabase_user_id as name for now
        _obj_in = UserCreate(name=supabase_user_id)

        user = users_manager.create_or_update(
            db_session=db_session,
            obj_in=_obj_in
        )

        return SignUpResponse(
            message="Successfully created user.",
            user=user.id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))