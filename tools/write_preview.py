import base64
from pathlib import Path

png = Path(r"C:\Users\simon\AppData\Local\Temp\cyd-farm-cute.png").read_bytes()
b64 = base64.b64encode(png).decode("ascii")
html = """<div id="cyd-farm-cute" class="vis-section-stack">
  <p class="vis-sr-only">Farm with a blue-roofed house, oak tree, pond, cow, sheep, pig, chickens, chest, and fenced crops.</p>
  <img id="cyd-farm-cute-img" alt="Farm screen using the Cute Fantasy sprites" src="data:image/png;base64,%s">
</div>
<style>
  #cyd-farm-cute img {
    display: block;
    width: 100%%;
    max-width: 640px;
    height: auto;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }
</style>
""" % b64
out = Path(r"C:\Users\simon\AppData\Local\Cursor\AgentStores\cursor_agent_stores\7fb77068-4b60-42fb-a90b-afbbc3a8d7a9\files\visualizations\cyd-farm-cute.html")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print(out.stat().st_size)
