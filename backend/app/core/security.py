import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status

from app.core.config import settings

_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


async def _fetch_jwks() -> dict[str, Any]:
    if not settings.CLERK_JWKS_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_JWKS_URL is not configured",
        )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        return response.json()


async def get_jwks() -> dict[str, Any]:
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _jwks_cache["keys"]
    keys = await _fetch_jwks()
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def _get_signing_key(jwks: dict[str, Any], kid: str) -> Any:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    return None


async def verify_clerk_token(token: str) -> dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing key id",
        )

    jwks = await get_jwks()
    signing_key = _get_signing_key(jwks, kid)
    if signing_key is None:
        _jwks_cache["keys"] = None
        jwks = await get_jwks()
        signing_key = _get_signing_key(jwks, kid)
        if signing_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find signing key",
            )

    options = {"verify_aud": bool(settings.CLERK_AUDIENCE)}
    decode_kwargs: dict[str, Any] = {
        "algorithms": ["RS256"],
        "options": options,
    }
    if settings.CLERK_ISSUER:
        decode_kwargs["issuer"] = settings.CLERK_ISSUER
    if settings.CLERK_AUDIENCE:
        decode_kwargs["audience"] = settings.CLERK_AUDIENCE

    try:
        return jwt.decode(token, signing_key, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except jwt.PyJWTError as exc:
        print(f"Token validation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
