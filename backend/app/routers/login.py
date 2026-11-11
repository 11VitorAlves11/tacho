from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.authentication import Strategy
from fastapi_users.router.common import ErrorCode

from app.auth import UserManager, auth_backend, fastapi_users, get_user_manager
from app.rate_limit import TOO_MANY_ATTEMPTS_DETAIL, RateLimiter, client_ip, get_rate_limiter, login_limits

# Router de login local do fastapi-users (montado em /auth/cookie) com a rota
# de login trocada por uma equivalente com limite de tentativas falhadas. O
# `/logout` continua a ser o original; o caminho, o formulário
# (`username`/`password`) e as respostas 204/400 do login não mudam.
LOGIN_ROUTE_NAME = f"auth:{auth_backend.name}.login"

router = fastapi_users.get_auth_router(auth_backend)
router.routes = [route for route in router.routes if getattr(route, "name", None) != LOGIN_ROUTE_NAME]


@router.post(
    "/login",
    name=LOGIN_ROUTE_NAME,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad credentials or the user is inactive."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": TOO_MANY_ATTEMPTS_DETAIL},
        **auth_backend.transport.get_openapi_login_responses_success(),
    },
)
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
    strategy: Strategy = Depends(auth_backend.get_strategy),
    limiter: RateLimiter = Depends(get_rate_limiter),
):
    ip_limit, email_limit = login_limits(client_ip(request), credentials.username)
    await limiter.enforce([ip_limit, email_limit])

    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        await limiter.record_failure([ip_limit, email_limit])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorCode.LOGIN_BAD_CREDENTIALS)

    await limiter.reset([email_limit])
    response = await auth_backend.login(strategy, user)
    await user_manager.on_after_login(user, request, response)
    return response
