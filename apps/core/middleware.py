class ContentSecurityPolicyMiddleware:
    """Adds frame-src to allow Power BI iframes on our pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = (
            "frame-src 'self' https://app.powerbi.com https://*.powerbi.com"
        )
        return response
