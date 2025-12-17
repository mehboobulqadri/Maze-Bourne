import json
import glob
import os

def fix_level(path):
    print(f"Checking {path}...")
    with open(path, 'r') as f:
        data = json.load(f)
    
    cells = data.get("cells", [])
    width = data.get("width", 25)
    height = data.get("height", 20)
    
    # 1. Fix Keys
    key_cells = [c for c in cells if c["type"] == "KEY"]
    if len(key_cells) > 1:
        print(f"  Found {len(key_cells)} keys. Keeping the first one.")
        # Keep the first one, change others to FLOOR
        first_key = key_cells[0]
        for k in key_cells[1:]:
            k["type"] = "FLOOR"
        key_pos = [[first_key["x"], first_key["y"]]]
    elif len(key_cells) == 1:
        key = key_cells[0]
        key_pos = [[key["x"], key["y"]]]
    else:
        print("  No keys found! Adding one near center.")
        # Add key at center if safe
        cx, cy = width//2, height//2
        # Use existing cell or add new
        existing = next((c for c in cells if c["x"] == cx and c["y"] == cy), None)
        if existing:
            existing["type"] = "KEY"
        else:
            cells.append({"x": cx, "y": cy, "type": "KEY"})
        key_pos = [[cx, cy]]
            
    # Update objects metadata
    if "objects" not in data:
        data["objects"] = {}
    data["objects"]["key_positions"] = key_pos

    # 2. Fix Exits (Ensure 1)
    exit_cells = [c for c in cells if c["type"] == "EXIT"]
    if not exit_cells:
        print("  No exit found! Adding one.")
        # Add exit far from spawn (assume spawn at 1,1 or similar)
        # Just put at width-2, height-2
        ex, ey = width-2, height-2
        existing = next((c for c in cells if c["x"] == ex and c["y"] == ey), None)
        if existing:
            existing["type"] = "EXIT"
        else:
            cells.append({"x": ex, "y": ey, "type": "EXIT"})
        exit_pos = [ex, ey]
    else:
        # If multiple, keep one?
        exit_pos = [exit_cells[0]["x"], exit_cells[0]["y"]]
    
    data["objects"]["exit_point"] = exit_pos
    
    # Save back
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print("  Fixed.")

for f in glob.glob("levels/*.json"):
    fix_level(f)
