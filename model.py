"""Cluster weighted RGB colors and reconstruct an image from the centroids."""

import numpy as np
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_limits


def sample_image():
    """Draw an original geometric landscape for the offline demo."""
    image = Image.new("RGB", (640, 400))
    draw = ImageDraw.Draw(image)
    for y in range(400):
        draw.line((0, y, 640, y), fill=(220 + y // 13, 173 + y // 7, 123 + y // 5))
    draw.ellipse((450, 48, 542, 140), fill="#fff0b3")
    draw.polygon([(0, 290), (190, 132), (400, 325), (550, 184), (640, 242),
                  (640, 400), (0, 400)], fill="#777fa1")
    draw.polygon([(0, 312), (157, 240), (300, 290), (480, 240), (640, 295),
                  (640, 400), (0, 400)], fill="#386c6b")
    draw.polygon([(0, 375), (179, 333), (340, 358), (640, 310), (640, 400),
                  (0, 400)], fill="#23464c")
    return image


def reduce_colors(image, requested_colors):
    if type(requested_colors) is not int or not 2 <= requested_colors <= 16:
        raise ValueError("Choose 2 to 16 colors.")
    preview = image.convert("RGB")
    preview.thumbnail((480, 480), Image.Resampling.LANCZOS)
    pixels = np.asarray(preview).reshape(-1, 3)
    colors, inverse, counts = np.unique(
        pixels, axis=0, return_inverse=True, return_counts=True
    )
    cluster_count = min(requested_colors, len(colors))

    if cluster_count == len(colors):
        reconstructed = pixels
    else:
        model = KMeans(n_clusters=cluster_count, random_state=42, n_init=3)
        with threadpool_limits(limits=1):
            model.fit(colors.astype(np.float64), sample_weight=counts.astype(np.float64))
        centroids = np.rint(model.cluster_centers_).clip(0, 255).astype(np.uint8)
        reconstructed = centroids[model.labels_[inverse]]

    palette, frequencies = np.unique(reconstructed, axis=0, return_counts=True)
    order = np.argsort(-frequencies, kind="stable")
    swatches = [
        {"hex": "#%02x%02x%02x" % tuple(palette[i]),
         "percent": round(100 * int(frequencies[i]) / len(pixels), 2)}
        for i in order
    ]
    difference = pixels.astype(np.float64) - reconstructed
    result = Image.fromarray(reconstructed.reshape(preview.height, preview.width, 3))
    return preview, result, swatches, float(np.sqrt(np.mean(difference ** 2)))
