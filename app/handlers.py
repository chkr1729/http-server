import socket
import re
import logging
from app.utils import parse_request, format_response
from app.files import handle_file_request, handle_file_upload


def handle_request(client_socket: socket.socket, base_directory: str) -> None:
    """Handles an incoming HTTP request (GET/POST) and sends an appropriate response."""
    try:
        request_data = client_socket.recv(4096).decode("utf-8")
        if not request_data:
            return

        method, path, headers = parse_request(request_data)
        headers = headers or {}

        accept_encoding = headers.get("accept-encoding", "").lower()
        supported_encodings = set(accept_encoding.replace(" ", "").split(","))

        # Handle GET requests
        if method == "GET":
            if path == "/":
                response = format_response(
                    "200 OK", "", "text/plain", supported_encodings
                )
            elif match := re.match(r"^/echo/(.+)$", path or ""):
                response = format_response(
                    "200 OK", match.group(1), "text/plain", supported_encodings
                )
            elif path == "/user-agent":
                response = format_response(
                    "200 OK",
                    headers.get("user-agent", "Unknown"),
                    "text/plain",
                    supported_encodings,
                )
            elif path and path.startswith("/files/"):
                response = handle_file_request(
                    path, base_directory, supported_encodings
                )
            else:
                response = format_response(
                    "404 Not Found", "Not Found", "text/plain", supported_encodings
                )

        # Handle POST requests
        elif method == "POST" and path and path.startswith("/files/"):
            response = handle_file_upload(request_data, path, base_directory, headers)
        else:
            response = format_response(
                "405 Method Not Allowed", "Only GET and POST supported"
            )

        client_socket.sendall(response)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Unexpected error handling request: %s", e, exc_info=True)
        response = format_response("500 Internal Server Error", "Server Error")
        client_socket.sendall(response)
    finally:
        client_socket.close()
