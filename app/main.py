import socket  # noqa: F401

def handle_request(client_socket):
    """Handles an incoming HTTP request and sends an appropriate response."""
    request_data = client_socket.recv(1024).decode("utf-8")  # Read the request
    if not request_data:
        client_socket.close()
        return

    # Extract the request path from the first line (Request-Line)
    request_line = request_data.split("\r\n")[0]  # First line of the request
    method, path, _ = request_line.split(" ")  # Extract method and path

    # Determine response based on path
    if method == "GET" and path == "/":
        response = "HTTP/1.1 200 OK\r\n\r\n"
    else:
        response = "HTTP/1.1 404 Not Found\r\n\r\n"

    client_socket.sendall(response.encode("utf-8"))
    client_socket.close()

def start_server():
    """Starts the HTTP server on localhost:4221."""
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    server_socket.listen(5)
    print("Server listening on http://localhost:4221")

    while True:
        client_socket, _ = server_socket.accept()
        handle_request(client_socket)

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")
    start_server()


if __name__ == "__main__":
    main()
