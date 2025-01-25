import os
import re
import logging
from app.utils import format_response


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
