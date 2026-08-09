import uuid


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID")
        try:
            request.request_id = uuid.UUID(supplied) if supplied else uuid.uuid4()
        except ValueError:
            request.request_id = uuid.uuid4()
        response = self.get_response(request)
        response["X-Request-ID"] = str(request.request_id)
        return response
