def generate_curl(swagger_json: dict, operation: dict) -> str:
    servers = swagger_json.get("servers", [])
    base_url = servers[0].get("url", "https://example.com") if servers else "https://example.com"
    base_url = base_url.rstrip("/")

    path = operation.get("path", "")
    method = operation.get("method", "GET").upper()
    params = operation.get("parameters", [])

    for param in params:
        if param.get("in") == "path":
            name = param.get("name", "")
            path = path.replace(f"{{{name}}}", f"{{{name}}}")

    url = f"{base_url}{path}"
    lines = [f"curl -X {method} '{url}'"]

    has_json_body = bool(operation.get("requestBodyRequiredFields")) or method in (
        "POST",
        "PUT",
        "PATCH",
    )
    if has_json_body:
        lines.append("  -H 'Content-Type: application/json'")
        lines.append("  -d '{}'")

    query_params = [p for p in params if p.get("in") == "query"]
    if query_params:
        query_parts = []
        for param in query_params:
            name = param.get("name", "")
            query_parts.append(f"{name}={{value}}")
        separator = "&" if "?" in url else "?"
        lines[0] = f"curl -X {method} '{url}{separator}{'&'.join(query_parts)}'"

    return " \\\n".join(lines)
