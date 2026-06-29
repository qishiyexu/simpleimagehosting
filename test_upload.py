import argparse
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def clean_filename(name):
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name or "file"


def upload(upload_url, api_key, file_path):
    path = Path(file_path)
    data = path.read_bytes()
    request = Request(
        upload_url,
        data=data,
        headers={
            "X-API-Key": api_key,
            "X-Filename": clean_filename(path.name),
            "Content-Type": "application/octet-stream",
        },
        method="POST",
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Upload one file and print its URL.")
    parser.add_argument("file", help="file to upload")
    parser.add_argument(
        "--url",
        default=os.environ.get("UPLOAD_URL", "http://127.0.0.1:8000/upload"),
        help="upload endpoint, default: %(default)s",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY"),
        help="upload API key, or set API_KEY",
    )
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("missing --api-key or API_KEY")

    try:
        result = upload(args.url, args.api_key, args.file)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit("upload failed: HTTP {} {}".format(exc.code, body))

    print(result["url"])


if __name__ == "__main__":
    main()
