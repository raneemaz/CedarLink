import json

def terminator(id_, x, y, w, h, text):
    return {"id": id_, "type": "terminator", "boundingBox": {"x": x, "y": y, "w": w, "h": h},
            "text": text, "style": {"fill": {"type": "color", "color": "#D1FAE5"}}}

def process(id_, x, y, w, h, text):
    return {"id": id_, "type": "process", "boundingBox": {"x": x, "y": y, "w": w, "h": h},
            "text": text, "style": {"fill": {"type": "color", "color": "#DBEAFE"}}}

def decision(id_, x, y, w, h, text):
    return {"id": id_, "type": "decision", "boundingBox": {"x": x, "y": y, "w": w, "h": h},
            "text": text, "style": {"fill": {"type": "color", "color": "#FEF3C7"}}}

def header(id_, x, y, w, h, text):
    return {"id": id_, "type": "text", "boundingBox": {"x": x, "y": y, "w": w, "h": h}, "text": text}

shapes = []
lines = []
line_n = [0]

def link(a, b, label=None):
    line_n[0] += 1
    l = {"id": f"l{line_n[0]}", "lineType": "elbow",
         "endpoint1": {"type": "shapeEndpoint", "style": "none", "shapeId": a},
         "endpoint2": {"type": "shapeEndpoint", "style": "arrow", "shapeId": b},
         "stroke": {"color": "#4B5563", "width": 1.5, "style": "solid"}}
    if label:
        l["text"] = [{"text": label, "position": 0.5, "side": "top"}]
    lines.append(l)

W = 260
X_CUST, X_VEND, X_ADMIN = 40, 380, 720

# =====================================================================
# 1. CUSTOMER FLOW
# =====================================================================
shapes.append(header("h_cust", X_CUST, 0, W, 40, "CUSTOMER FLOW"))
shapes.append(terminator("c1", X_CUST, 70, W, 50, "Start: Visit CedarLink"))
shapes.append(process("c2", X_CUST, 150, W, 60, "Register / Login"))
shapes.append(process("c3", X_CUST, 240, W, 60, "Browse Stores & Search Products"))
shapes.append(process("c4", X_CUST, 330, W, 60, "View Product Details & Add to Cart"))
shapes.append(decision("c5", X_CUST, 420, W, 90, "Ready to Checkout? (No: keep browsing)"))
shapes.append(process("c6", X_CUST, 540, W, 60, "Enter Delivery Address"))
shapes.append(process("c7", X_CUST, 630, W, 60, "Select Payment Method"))
shapes.append(decision("c8", X_CUST, 720, W, 90, "Payment Successful? (No: retry/cancel)"))
shapes.append(process("c9", X_CUST, 840, W, 60, "Order Confirmed - Status: Pending"))
shapes.append(process("c10", X_CUST, 930, W, 60, "Track Order Status"))
shapes.append(terminator("c11", X_CUST, 1020, W, 50, "End: Order Delivered"))

for a, b, lbl in [("c1","c2",None), ("c2","c3",None), ("c3","c4",None), ("c4","c5",None),
                  ("c5","c6","Yes"), ("c6","c7",None), ("c7","c8",None), ("c8","c9","Yes"),
                  ("c9","c10",None), ("c10","c11",None)]:
    link(a, b, lbl)

# =====================================================================
# 2. VENDOR FLOW
# =====================================================================
shapes.append(header("h_vend", X_VEND, 0, W, 40, "VENDOR FLOW"))
shapes.append(terminator("v1", X_VEND, 70, W, 50, "Start: Account Created by Admin"))
shapes.append(process("v2", X_VEND, 150, W, 60, "Login"))
shapes.append(process("v3", X_VEND, 240, W, 60, "Create / Manage Store Profile"))
shapes.append(process("v4", X_VEND, 330, W, 60, "Add / Edit / Delete Products"))
shapes.append(process("v5", X_VEND, 420, W, 60, "Configure Delivery Fee & Availability"))
shapes.append(process("v6", X_VEND, 510, W, 60, "Receive Incoming Orders"))
shapes.append(process("v7", X_VEND, 600, W, 60, "Update Order Status"))
shapes.append(process("v8", X_VEND, 690, W, 60, "View Sales Statistics"))
shapes.append(terminator("v9", X_VEND, 780, W, 50, "End"))

for a, b in [("v1","v2"), ("v2","v3"), ("v3","v4"), ("v4","v5"), ("v5","v6"), ("v6","v7"), ("v7","v8"), ("v8","v9")]:
    link(a, b)

# =====================================================================
# 3. ADMIN FLOW
# =====================================================================
shapes.append(header("h_admin", X_ADMIN, 0, W, 40, "ADMIN FLOW"))
shapes.append(terminator("a1", X_ADMIN, 70, W, 50, "Start: Admin Login"))
shapes.append(process("a2", X_ADMIN, 150, W, 60, "View All Users & Stores"))
shapes.append(process("a3", X_ADMIN, 240, W, 60, "Create Store Owner Accounts"))
shapes.append(process("a4", X_ADMIN, 330, W, 60, "Manage Product Categories"))
shapes.append(process("a5", X_ADMIN, 420, W, 60, "Monitor Orders & Handle Reports"))
shapes.append(decision("a6", X_ADMIN, 510, W, 90, "Policy Violation Found? (No: continue monitoring)"))
shapes.append(process("a7", X_ADMIN, 630, W, 60, "Suspend / Remove Store"))
shapes.append(terminator("a8", X_ADMIN, 720, W, 50, "End"))

for a, b, lbl in [("a1","a2",None), ("a2","a3",None), ("a3","a4",None), ("a4","a5",None),
                  ("a5","a6",None), ("a6","a7","Yes"), ("a7","a8",None)]:
    link(a, b, lbl)

# =====================================================================
# 4. CROSS-COLUMN INTERACTIONS (Connected Ecosystem)
# =====================================================================
link("a3", "v1", "Onboards Vendor")      # Admin creates account -> Vendor start
link("c9", "v6", "Dispatches Order")     # Customer order confirmed -> Vendor receives it
link("v7", "c10", "Updates Tracking")    # Vendor changes order status -> Customer tracks it

# =====================================================================
# OUTPUT GENERATION
# =====================================================================
doc = {"version": 1, "pages": [{"id": "page1", "title": "CedarLink Connected User Flow", "shapes": shapes, "lines": lines}]}

output_file = "cedarlink_flow.json"
with open(output_file, "w") as f:
    json.dump(doc, f, separators=(",", ":"))

print(f"Successfully generated mapping file: '{output_file}'")
print(f"Total Shapes: {len(shapes)} | Total Lines: {len(lines)}")