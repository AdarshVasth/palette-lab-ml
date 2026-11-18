"""Loopback-only web demo for Palette Lab."""

import base64
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image, ImageOps, UnidentifiedImageError

from model import reduce_colors, sample_image

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 6_000_000
ASSETS = {"/": ("index.html", "text/html"), "/style.css": ("style.css", "text/css"),
          "/app.js": ("app.js", "text/javascript")}


def png_bytes(image):
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def png_url(image):
    return "data:image/png;base64," + base64.b64encode(png_bytes(image)).decode("ascii")


def read_image(data):
    with Image.open(io.BytesIO(data), formats=["PNG", "JPEG"]) as image:
        if image.width * image.height > MAX_PIXELS:
            raise ValueError("Image exceeds 6 megapixels.")
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("Choose a still image.")
        oriented = ImageOps.exif_transpose(image).convert("RGBA")
        background = Image.new("RGBA", oriented.size, "white")
        return Image.alpha_composite(background, oriented).convert("RGB")


class PaletteHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def respond(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def json_response(self, status, payload):
        self.respond(status, "application/json", json.dumps(payload).encode())

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ASSETS:
            filename, media_type = ASSETS[path]
            self.respond(200, media_type + "; charset=utf-8", (ROOT / filename).read_bytes())
        elif path == "/sample":
            self.respond(200, "image/png", png_bytes(sample_image()))
        else:
            self.json_response(404, {"error": "Page not found."})

    def do_POST(self):
        url = urlsplit(self.path)
        if url.path != "/api/palette":
            self.json_response(404, {"error": "Page not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BYTES:
                raise ValueError("Choose an image up to 5 MiB.")
            colors = int(parse_qs(url.query).get("colors", ["6"])[0])
            if not 2 <= colors <= 16:
                raise ValueError("Choose 2 to 16 colors.")
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError("Image upload was incomplete.")
            image = read_image(data)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            self.json_response(400, {"error": "Choose a readable PNG or JPEG within the size limits."})
            return
        except ValueError as error:
            self.json_response(400, {"error": str(error)})
            return

        original, reduced, swatches, rmse = reduce_colors(image, colors)
        self.json_response(200, {"original": png_url(original), "reduced": png_url(reduced),
                                 "palette": swatches, "rgb_rmse": round(rmse, 2),
                                 "width": reduced.width, "height": reduced.height})


if __name__ == "__main__":
    print("Open http://127.0.0.1:8000")
    with HTTPServer(("127.0.0.1", 8000), PaletteHandler) as server:
        server.serve_forever()
