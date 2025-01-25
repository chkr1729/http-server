import socket
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from app.handlers import handle_request


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
