import base64
from pathlib import Path

png = Path(r"C:\Users\simon\AppData\Local\Temp\cyd-farm-pack.png").read_bytes()
b64 = base64.b64encode(png).decode("ascii")
html = """<div id="cyd-farm-now" class="vis-section-stack">
  <p class="vis-sr-only">Current farm: red-roofed house, cobble path, fenced dirt plots, maple trees, a chest, two chickens, and the farmer.</p>
  <img id="cyd-farm-now-img" alt="Farm screen with the 16 by 16 asset pack" src="data:image/png;base64,%s">
</div>
<style>
  #cyd-farm-now img {
    display: block;
    width: 100%%;
    max-width: 640px;
    height: auto;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }
</style>
""" % b64
out = Path(r"C:\Users\simon\AppData\Local\Cursor\AgentStores\cursor_agent_stores\7fb77068-4b60-42fb-a90b-afbbc3a8d7a9\files\visualizations\cyd-farm-now.html")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print(out.stat().st_size)
