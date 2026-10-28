# Third-party files

Nothing below is stored in this skill. `scripts/fx_assets.py` downloads each file on first use into `~/.cache/hybrid-social-video` (override with `HSV_CACHE`), checks its size
and sha256 against `data/assets.json`, and refuses anything that does not match. Every one is optional: offline, the effects fall back to system fonts and a rougher matte.

| File | What it is | Licence | Source |
|---|---|---|---|
| `models/modnet.onnx` | MODNet portrait matting, ONNX export | Apache-2.0 | https://huggingface.co/Xenova/modnet |
| `models/yunet.onnx` | YuNet face detector for OpenCV (2023 Mar) | MIT | https://github.com/opencv/opencv_zoo |
| Anton, Archivo Black, Instrument Serif, Space Mono, Playfair Display, Montserrat, Inter, Caveat | fonts for rendered text | SIL OFL 1.1 | https://github.com/google/fonts |
| Permanent Marker | handwriting font | Apache-2.0 | https://github.com/google/fonts |

Python packages used by the scripts are installed by the user, not bundled: numpy, opencv-python, Pillow, onnxruntime (optional), faster-whisper (optional), Playwright (the HTML
route). The font licences allow use in rendered video; the font files are not redistributed by this skill.
