import logging
import sys
import argparse
from pathlib import Path
from app.server import start_server

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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

    base_directory = Path(args.directory).resolve()

    if not base_directory.is_dir():
        logging.error("Invalid directory: %s", base_directory)
        sys.exit(1)

    logging.info("Serving files from: %s", base_directory)

    try:
        start_server(str(base_directory))  # Convert Path object back to string
    except KeyboardInterrupt:
        logging.info("Server shutting down gracefully...")
        sys.exit(0)
