from app import app


def test_api_routes_expose_auth_schemes_in_openapi():
    schema = app.openapi()
    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    assert "HTTPBearer" in security_schemes
    assert "APIKeyHeader" in security_schemes

    operation_security = schema["paths"]["/api/link"]["get"].get("security", [])
    assert {"HTTPBearer": []} in operation_security
    assert {"APIKeyHeader": []} in operation_security
