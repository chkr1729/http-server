import gzip
from typing import Optional, Tuple


def parse_request(
    request_data: str,
) -> Tuple[Optional[str], Optional[str], dict[str, str]]:
    """Parses the HTTP request and returns method, path, and headers."""
    lines = request_data.split("\r\n")
    if not lines or len(lines[0].split(" ")) < 3:
        return None, None, {}  # Malformed request

    method, path, _ = lines[0].split(" ")
    headers = {
        key.strip().lower(): value.strip()
        for line in lines[1:]
        if ": " in line
        for key, value in [line.split(":", 1)]
    }

    return method, path, headers


def format_response(
    status_code: str,
    body: str | bytes = "",
    content_type: str = "text/plain",
    supported_encodings: Optional[set[str]] = None,
) -> bytes:
    """Formats an HTTP response with given status, body, and headers."""

    if isinstance(body, str):
        response_body = body.encode("utf-8")  # Convert string to bytes
    else:  # body is guaranteed to be bytes here
        response_body = body

    headers = [
        f"HTTP/1.1 {status_code}",
        f"Content-Type: {content_type}",
    ]

    if "gzip" in (supported_encodings or set()):
        response_body = gzip.compress(response_body)
        headers.append("Content-Encoding: gzip")

    headers.append(f"Content-Length: {len(response_body)}")
    headers.append("\r\n")  # End of headers

    return "\r\n".join(headers).encode("utf-8") + response_body
