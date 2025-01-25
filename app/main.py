import socket
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def parse_request(request_data):
    """Parses the HTTP request and returns method, path, and headers."""
    lines = request_data.split("\r\n")
    if not lines or len(lines[0].split(" ")) < 3:
        return None, None, None  # Malformed request

    method, path, _ = lines[0].split(" ")
    headers = {
        key.strip().lower(): value.strip()
        for line in lines[1:]
        if ": " in line
        for key, value in [line.split(":", 1)]
    }

    return method, path, headers


def format_response(status_code, body="", content_type="text/plain"):
    """Formats an HTTP response with given status, body, and headers."""
    response_body = body.encode("utf-8")
    headers = (
        f"HTTP/1.1 {status_code}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        "\r\n"
    )
    return headers.encode("utf-8") + response_body


def handle_request(client_socket):
    """Handles an incoming HTTP request and sends an appropriate response."""
    try:
        request_data = client_socket.recv(1024).decode("utf-8")
        if not request_data:
            return  # Empty request, do nothing

        method, path, headers = parse_request(request_data)
        headers = headers or {}  # Ensure headers is always a dictionary

        if not method or not path:
            response = format_response("400 Bad Request", "Invalid Request")
        elif method != "GET":
            response = format_response("405 Method Not Allowed", "Only GET supported")
        elif path == "/":
            response = format_response("200 OK")
        elif match := re.match(r"^/echo/(.+)$", path):  # Using the walrus operator
            response = format_response("200 OK", match.group(1))
        elif path == "/user-agent":
            response = format_response("200 OK", headers.get("user-agent", "Unknown"))
        else:
            response = format_response("404 Not Found", "Not Found")

        client_socket.sendall(response)
    except (ValueError, KeyError, TypeError, socket.error) as e:
        logging.error("Error handling request: %s", e)
        response = format_response("500 Internal Server Error", "Server Error")
        client_socket.sendall(response)
    finally:
        client_socket.close()  # Ensure the connection is closed


def start_server():
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
                    executor.submit(handle_request, client_socket)

    except (PermissionError, OSError, socket.error) as e:
        logging.error("Server failed to start due to a system error: %s", e)
    except KeyboardInterrupt:
        logging.info("Server shutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    start_server()
