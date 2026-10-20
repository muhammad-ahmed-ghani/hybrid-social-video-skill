"""Write data.js for index.html from the host_assemble.py output.

    python3 gen_data.py <build dir>      # build dir holds timing.json and hf/h00001.jpg ...

Extract the host frames first:  ffmpeg -i build/host.mp4 -vf fps=30,scale=1080:1920 -q:v 3 build/hf/h%05d.jpg
Copy index.html and data.js into the same folder as hf/, then: render_html.py --page build/index.html --out build/frames
"""
import json
import sys
from pathlib import Path

b = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
t = json.loads((b / "timing.json").read_text())
n = len(list((b / "hf").glob("h*.jpg")))
(b / "data.js").write_text("window.TIMING=" + json.dumps(t) + ";window.NFRAMES=" + str(n) + ";\n")
print("data.js:", len(t["beats"]), "beats,", n, "host frames,", t["duration"], "s")
