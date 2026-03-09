from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Request,
    Response,
    Security,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from link_shortener.models import (
    LinkCreateRequest,
    LinkRecord,
    LinkUpdateRequest,
    is_valid_code,
    is_valid_redirect_link,
)
from link_shortener.service import (
    LinkAlreadyExistsError,
    LinkNotFoundError,
    create_link,
    delete_link,
    get_link,
    list_links,
    update_link,
)

CodePath = Annotated[str, Path(pattern=r"^[a-z0-9]{1,12}$", max_length=12)]

app = FastAPI(title="Shortlink API")
api = APIRouter(prefix="/api")
bearer_auth = HTTPBearer(auto_error=False)
x_access_token_auth = APIKeyHeader(name="X-Access-Token", auto_error=False)


@app.middleware("http")
async def inject_env_from_state(request: Request, call_next):
    if "env" not in request.scope and getattr(app.state, "env", None) is not None:
        request.scope["env"] = app.state.env
    return await call_next(request)


def get_env(request: Request) -> Any:
    env = request.scope.get("env")
    if env is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudflare env bindings are unavailable",
        )
    return env


def get_domain_name(env: Any) -> str:
    domain = str(getattr(env, "DOMAIN_NAME", "")).strip()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DOMAIN_NAME is not configured",
        )
    return domain.removeprefix("https://").removeprefix("http://").strip("/")


async def require_api_access(
    request: Request,
    bearer_credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(bearer_auth)
    ] = None,
    x_access_token: Annotated[str | None, Security(x_access_token_auth)] = None,
) -> None:
    env = get_env(request)
    expected_token = str(getattr(env, "STATIC_ACCESS_TOKEN", "")).strip()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STATIC_ACCESS_TOKEN is not configured",
        )

    supplied_token = ""
    if bearer_credentials is not None:
        supplied_token = bearer_credentials.credentials.strip()
    elif x_access_token is not None:
        supplied_token = x_access_token.strip()

    if supplied_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


@api.get("/link", response_model=list[LinkRecord], dependencies=[Depends(require_api_access)])
async def list_shortlinks(request: Request) -> list[LinkRecord]:
    env = get_env(request)
    return await list_links(env.LINKS)


@api.get(
    "/link/{code}",
    response_model=LinkRecord,
    dependencies=[Depends(require_api_access)],
)
async def get_shortlink(code: CodePath, request: Request) -> LinkRecord:
    env = get_env(request)
    try:
        return await get_link(env.LINKS, code)
    except LinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shortlink not found"
        ) from None


@api.post(
    "/link",
    response_model=LinkRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_access)],
)
async def create_shortlink(
    request: Request, payload: LinkCreateRequest, response: Response
) -> LinkRecord:
    env = get_env(request)

    try:
        created = await create_link(env.LINKS, link=payload.link, code=payload.code)
    except LinkAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shortlink code already exists",
        ) from None

    response.headers["Location"] = f"https://{get_domain_name(env)}/{created.code}"
    return created


@api.put(
    "/link/{code}",
    response_model=LinkRecord,
    dependencies=[Depends(require_api_access)],
)
async def update_shortlink(
    code: CodePath, request: Request, payload: LinkUpdateRequest
) -> LinkRecord:
    env = get_env(request)
    try:
        return await update_link(env.LINKS, code=code, link=payload.link)
    except LinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shortlink not found"
        ) from None


@api.delete(
    "/link/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_access)],
)
async def delete_shortlink(code: CodePath, request: Request) -> Response:
    env = get_env(request)
    try:
        await delete_link(env.LINKS, code=code)
    except LinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shortlink not found"
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app.include_router(api)


@app.api_route(
    "/{code_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def resolve_shortlink(code_path: str, request: Request):
    code = code_path.strip("/")
    if not code or "/" in code or not is_valid_code(code):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    env = get_env(request)
    link = await env.LINKS.get(code)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_valid_redirect_link(str(link)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return RedirectResponse(url=str(link), status_code=status.HTTP_302_FOUND)
