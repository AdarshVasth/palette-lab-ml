# Palette Lab

Extract the dominant colors in a photo, compare the original and reduced-color
previews, and download the resulting PNG. Palette Lab fits an unsupervised
K-means model locally for each image. It needs no API key, GPU, or paid service.

## Run locally

Use Python 3.12. Run these commands from the repository root on Linux or macOS.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Leave the image blank and
click **Extract palette** to use the bundled example. Try four colors, then
twelve. You can also select a still PNG or JPEG. Use Ctrl+C to stop the server.

Run `python -m unittest -v` using the same virtual environment's Python to
check exact palette recovery, real model fitting, the sample flow, PNG decoding,
transparency handling, and invalid input.

## Architecture

1. **Browser** (HTML, CSS, JavaScript) posts image bytes and the color count to
   the loopback server. The server returns previews, swatch percentages, and
   RGB root mean square error (RMSE).
2. **HTTP adapter** (`app.py`) checks input limits, handles EXIF orientation,
   and composites transparency over white.
3. **Model** (`model.py`) resizes the preview to fit 480 × 480 pixels,
   groups identical RGB values, and fits weighted K-means to those values.
   Each color's weight is its pixel count. It reconstructs the image by
   replacing each pixel with its cluster's centroid and counts the resulting
   colors. If the number of unique input colors is already low enough, it
   returns them directly.

See the [scikit-learn KMeans reference](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)
and [Pillow image reference](https://pillow.readthedocs.io/en/stable/reference/Image.html).

The original geometric landscape in `sample_image()` is dedicated to the
public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
The demo generates it locally at runtime.

## Limitations

- Accepts still PNG and JPEG files up to 5 MiB and 6 megapixels. Both previews
  and the export are downscaled, and transparent pixels are flattened onto white.
- K-means uses Euclidean distances in RGB, which can disagree with human color
  perception. It favors common colors, so a small bright detail may disappear.
  The reported RMSE is measured on the preview in RGB units and says nothing
  about how people judge the result or how small the exported PNG will be.
- The server binds to localhost. It processes images in memory and is intended
  for one local user. The HTTP server has no authentication or production deployment setup.

## Internship learning guide

1. Trace one request from the HTML form through `do_POST()` to
   `reduce_colors()`. Explain why the request carries bytes and the response
   carries data URLs.
2. Compare palettes for 2, 6, and 12 colors. Explain how assignment and centroid
   updates reduce the clustering objective, and why counts preserve repeated
   pixels without fitting every duplicate.
3. In an interview, explain the tradeoff between runtime, preview resolution,
   and fidelity. Try an image with a small accent color and describe why the
   model can miss it even when the overall RGB error is low.
