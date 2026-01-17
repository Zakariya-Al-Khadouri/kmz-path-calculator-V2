from flask import Flask, render_template, request, jsonify, send_file
import zipfile
import xml.etree.ElementTree as ET
import re
import os
import uuid
import pandas as pd
from math import radians, sin, cos, sqrt, asin

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

NS = {"kml": "http://www.opengis.net/kml/2.2"}

# ---------- Distance Calculation ----------
def haversine(p1, p2):
    R = 6371000  # meters
    lat1, lon1 = radians(p1[0]), radians(p1[1])
    lat2, lon2 = radians(p2[0]), radians(p2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def calculate_true_length(coords):
    total = 0
    for i in range(len(coords) - 1):
        total += haversine(coords[i], coords[i+1])
    return round(total, 2)

# ---------- KMZ Processing ----------
def process_kmz(path):
    results = []
    all_coords = []

    with zipfile.ZipFile(path, 'r') as kmz:
        kml_file = [f for f in kmz.namelist() if f.endswith(".kml")][0]
        kml_data = kmz.read(kml_file)

    root = ET.fromstring(kml_data)

    for pm in root.findall(".//kml:Placemark", NS):
        name_el = pm.find("kml:name", NS)
        coord_el = pm.find(".//kml:coordinates", NS)

        if name_el is None or coord_el is None:
            continue

        declared = None
        match = re.search(r'(\d+)\s*m$', name_el.text)
        if match:
            declared = int(match.group(1))

        coords = []
        for c in coord_el.text.strip().split():
            lon, lat, *_ = map(float, c.split(","))
            coords.append([lat, lon])

        if len(coords) < 2:
            continue

        calculated = calculate_true_length(coords)

        diff = None
        diff_pct = None
        if declared:
            diff = round(calculated - declared, 2)
            diff_pct = round((diff / declared) * 100, 2)

        results.append({
            "name": name_el.text,
            "declared_m": declared,
            "calculated_m": calculated,
            "difference_m": diff,
            "difference_pct": diff_pct
        })

        all_coords.append(coords)

    return results, all_coords

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    all_results = []
    all_coords = []

    for file in request.files.getlist("files"):
        filename = f"{uuid.uuid4()}.kmz"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        results, coords = process_kmz(path)
        all_results.extend(results)
        all_coords.extend(coords)

    declared_total = sum(r["declared_m"] or 0 for r in all_results)
    calculated_total = sum(r["calculated_m"] for r in all_results)
    diff_total = round(calculated_total - declared_total, 2)

    equation = " + ".join(
        str(r["declared_m"]) for r in all_results if r["declared_m"]
    ) + f" = {declared_total} m"

    return jsonify({
        "paths": len(all_results),
        "declared_total": declared_total,
        "calculated_total": round(calculated_total, 2),
        "difference_total": diff_total,
        "equation": equation,
        "details": all_results,
        "coordinates": all_coords
    })

@app.route("/export/<fmt>", methods=["POST"])
def export(fmt):
    data = request.json
    df = pd.DataFrame(data)

    filename = f"results.{fmt}"
    path = os.path.join(UPLOAD_FOLDER, filename)

    if fmt == "csv":
        df.to_csv(path, index=False)
    else:
        df.to_excel(path, index=False)

    return send_file(path, as_attachment=True)

# ---------- START APP (Render compatible) ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
