import base64
import io
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer

from PIL import Image

from app import PaletteHandler, png_bytes, read_image
from model import reduce_colors, sample_image


class ModelTests(unittest.TestCase):
    def test_recovers_exact_two_color_palette(self):
        image = Image.new("RGB", (4, 4), (255, 0, 0))
        image.paste((0, 0, 255), (0, 0, 1, 4))
        _, reduced, palette, error = reduce_colors(image, 6)
        self.assertEqual(reduced.tobytes(), image.tobytes())
        self.assertEqual(palette, [{"hex": "#ff0000", "percent": 75.0},
                                   {"hex": "#0000ff", "percent": 25.0}])
        self.assertEqual(error, 0)

    def test_clusters_original_sample(self):
        original, reduced, palette, error = reduce_colors(sample_image(), 6)
        self.assertEqual(original.size, (480, 300))
        self.assertEqual(reduced.size, original.size)
        self.assertEqual(len(reduced.getcolors(16)), 6)
        self.assertAlmostEqual(sum(item["percent"] for item in palette), 100, delta=0.05)
        self.assertGreater(error, 0)
        self.assertEqual(reduce_colors(sample_image(), 6)[2], palette)

    def test_transparent_pixels_are_composited_over_white(self):
        image = Image.new("RGBA", (2, 2), (255, 0, 0, 0))
        self.assertEqual(read_image(png_bytes(image)).getpixel((0, 0)), (255, 255, 255))


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), PaletteHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        try:
            conn.request(method, path, body)
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_demo_routes_and_download_payload(self):
        status, html = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Extract palette", html)
        for asset in ("/app.js", "/style.css"):
            self.assertEqual(self.request("GET", asset)[0], 200)
        status, sample = self.request("GET", "/sample")
        self.assertEqual(status, 200)
        status, body = self.request("POST", "/api/palette?colors=4", sample)
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(len(data["palette"]), 4)
        png = base64.b64decode(data["reduced"].split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(png)) as image:
            image.load()
            self.assertEqual(image.size, (480, 300))

    def test_bad_inputs_and_unknown_paths(self):
        for path, body in (("/api/palette", b""), ("/api/palette", b"bad"),
                           ("/api/palette?colors=20", b"bad")):
            with self.subTest(path=path, body=body):
                status, payload = self.request("POST", path, body)
                self.assertEqual(status, 400)
                self.assertIn("error", json.loads(payload))
        self.assertEqual(self.request("GET", "/requirements.txt")[0], 404)
