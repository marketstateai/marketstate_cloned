import asyncio
from urllib.parse import urlencode

import httpx
from flask import Response

from app.main import app


async def _dispatch(method: str, path: str, query: str, headers: dict, body: bytes):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        target = path
        if query:
            target = f"{path}?{query}"
        return await client.request(method, target, headers=headers, content=body)


def currency_api(request):
    query = urlencode(request.args, doseq=True)
    upstream = asyncio.run(
        _dispatch(
            method=request.method,
            path=request.path,
            query=query,
            headers={k: v for k, v in request.headers.items()},
            body=request.get_data(),
        )
    )

    passthrough_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in {"content-length", "transfer-encoding", "connection"}
    }
    return Response(
        upstream.content, status=upstream.status_code, headers=passthrough_headers
    )
