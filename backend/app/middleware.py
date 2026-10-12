from starlette.responses import JSONResponse

MAX_BODY_BYTES = 64 * 1024  # all JSON bodies in this API are tiny


class BodySizeLimitMiddleware:
    """Rejects oversized bodies, by Content-Length and while streaming."""

    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            return await self._reject(scope, receive, send)

        seen = 0
        too_big = False

        async def limited_receive():
            nonlocal seen, too_big
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    too_big = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        started = False

        async def guarded_send(message):
            nonlocal started
            if too_big and not started:
                started = True
                return await self._reject(scope, receive, send)
            if not too_big:
                await send(message)

        await self.app(scope, limited_receive, guarded_send)

    async def _reject(self, scope, receive, send):
        response = JSONResponse({"detail": "Request body too large"}, status_code=413)
        await response(scope, receive, send)
