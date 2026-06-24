import json

# Load your generated flowchart data
with open("cedarlink_flow.json", "r") as f:
    data = json.load(f)

page = data["pages"][0]
shapes = {s["id"]: s for s in page["shapes"]}
lines = page["lines"]
svg_el = []

# Process nodes and custom hex color fills
for s in shapes.values():
    bbox = s["boundingBox"]
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    txt = s["text"]
    bg = s.get("style", {}).get("fill", {}).get("color", "none")
    
    if s["type"] == "text":
        svg_el.append(f'<text x="{x+w/2}" y="{y+h/2}" font-family="sans-serif" font-size="16" font-weight="bold" fill="#111" text-anchor="middle">{txt}</text>')
    elif s["type"] == "decision":
        cx, cy = x + w/2, y + h/2
        pts = f"{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}"
        svg_el.append(f'<polygon points="{pts}" fill="{bg}" stroke="#4B5563" stroke-width="1.5"/>')
        svg_el.append(f'<text x="{cx}" y="{cy+4}" font-family="sans-serif" font-size="10" fill="#374151" text-anchor="middle">{txt[:35]}</text>')
    else:
        rx = 20 if s["type"] == "terminator" else 6
        svg_el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" fill="{bg}" stroke="#4B5563" stroke-width="1.5"/>')
        svg_el.append(f'<text x="{x+w/2}" y="{y+h/2+4}" font-family="sans-serif" font-size="11" fill="#374151" text-anchor="middle">{txt}</text>')

# Process structural connectors
for l in lines:
    id1, id2 = l["endpoint1"]["shapeId"], l["endpoint2"]["shapeId"]
    if id1 in shapes and id2 in shapes:
        b1, b2 = shapes[id1]["boundingBox"], shapes[id2]["boundingBox"]
        # Determine if it's a vertical or cross-column link
        if abs(b1["x"] - b2["x"]) < 50:
            x1, y1 = b1["x"] + b1["w"]/2, b1["y"] + b1["h"]
            x2, y2 = b2["x"] + b2["w"]/2, b2["y"]
        else:
            x1, y1 = b1["x"] + b1["w"]/2, b1["y"] + b1["h"]/2
            x2, y2 = b2["x"] + b2["w"]/2, b2["y"] + b2["h"]/2
        svg_el.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#4B5563" stroke-width="1.5" marker-end="url(#arrow)"/>')

# Output fully composed vector web file
html_frame = f"""<!DOCTYPE html><html><body style="background:#F9FAFB;"><svg width="1100" height="1200">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#4B5563"/></marker></defs>
{"".join(svg_el)}</svg></body></html>"""

with open("view_flow.html", "w") as f:
    f.write(html_frame)
print("Rendered! Open 'view_flow.html' in any web browser to see your diagram.")