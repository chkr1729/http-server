import socket
import logging
import re
import sys
import os
import argparse
import gzip
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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


def handle_file_upload(
    request_data: str, path: str, base_directory: str, headers: dict[str, str]
) -> bytes:
    """Handles file upload via POST request to `/files/{filename}`."""

    match = re.match(r"^/files/([^/]+)$", path)
    if not match:
        return format_response("400 Bad Request", "Invalid file request")

    filename = match.group(1)
    file_path = os.path.abspath(os.path.join(base_directory, filename))

    # Prevent directory traversal attacks
    if not file_path.startswith(os.path.abspath(base_directory)):
        return format_response("403 Forbidden", "Access Denied")

    # Validate Content-Length header
    content_length = headers.get("content-length")
    if content_length is None or not content_length.isdigit():
        return format_response(
            "411 Length Required", "Content-Length header missing or invalid"
        )

    content_length = int(content_length)

    # Extract request body (POST data)
    request_parts = request_data.split("\r\n\r\n", 1)
    if len(request_parts) < 2:
        return format_response("400 Bad Request", "Missing request body")

    request_body = request_parts[1][
        :content_length
    ]  # Ensure we only take the expected length

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request_body)
        return format_response("201 Created")  # Success response
    except OSError as e:
        logging.error("Error writing file %s: %s", filename, e)
        return format_response("500 Internal Server Error", "File write error")


def handle_file_request(
    path: str, base_directory: str, supported_encodings: set[str]
) -> bytes:
    """Handles file retrieval from the specified directory securely with optional compression."""

    match = re.match(r"^/files/([^/]+)$", path)
    response = None

    if not match:
        response = format_response(
            "400 Bad Request", "Invalid file request", "text/plain", supported_encodings
        )
    else:
        filename = match.group(1)
        file_path = os.path.abspath(os.path.join(base_directory, filename))

        if not file_path.startswith(os.path.abspath(base_directory)):
            response = format_response(
                "403 Forbidden", "Access Denied", "text/plain", supported_encodings
            )
        elif not os.path.isfile(file_path):
            response = format_response(
                "404 Not Found", "File Not Found", "text/plain", supported_encodings
            )
        else:
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                response = format_response(
                    "200 OK",
                    file_content,
                    "application/octet-stream",
                    supported_encodings,
                )
            except FileNotFoundError:
                response = format_response(
                    "404 Not Found",
                    "File not found Error",
                    "text/plain",
                    supported_encodings,
                )
            except PermissionError:
                response = format_response(
                    "403 Forbidden",
                    "Permission Denied",
                    "text/plain",
                    supported_encodings,
                )
            except OSError as e:
                logging.error("OS error reading file %s: %s", filename, e)
                response = format_response(
                    "500 Internal Server Error",
                    "OS Error",
                    "text/plain",
                    supported_encodings,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.critical(
                    "Unexpected error reading file %s: %s", filename, e, exc_info=True
                )
                response = format_response(
                    "500 Internal Server Error",
                    "Server Error",
                    "text/plain",
                    supported_encodings,
                )
    return response


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


def start_server(base_directory: str) -> None:
    """Starts the HTTP server on localhost:4221 with multithreading support."""
    try:
        with socket.create_server(
            ("localhost", 4221), reuse_port=True
        ) as server_socket:
            server_socket.listen(5)
            logging.info("Server listening on http://localhost:4221")

            with ThreadPoolExecutor(max_workers=10) as executor:
                while True:
                    client_socket, client_address = server_socket.accept()
                    logging.info("New connection from %s", client_address)
                    executor.submit(handle_request, client_socket, base_directory)

    except (PermissionError, OSError, socket.error) as e:
        logging.error("Server failed to start due to a system error: %s", e)
    except KeyboardInterrupt:
        logging.info("Server shutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simple HTTP server with file serving support."
    )
    parser.add_argument(
        "--directory",
        default="/tmp",
        help="Directory to serve files from (default: /tmp)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        logging.error("Invalid directory: %s", args.directory)
        sys.exit(1)

    start_server(args.directory)
