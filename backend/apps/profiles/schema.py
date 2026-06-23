from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CsrfExemptSessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.profiles.authentication.CsrfExemptSessionAuthentication"
    name = "sessionAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
            "description": "Django session cookie. 로그인 API 호출 뒤 같은 브라우저 세션으로 인증됩니다.",
        }
