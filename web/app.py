import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from flask import Flask, jsonify, render_template, request  # noqa: E402
from rutas import QUERY_EDGES, calcular_ruta, engine  # noqa: E402

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/ruta")
def api_ruta():
    try:
        origen = (float(request.args["origen_lon"]), float(request.args["origen_lat"]))
        destino = (float(request.args["destino_lon"]), float(request.args["destino_lat"]))
    except (KeyError, ValueError):
        return jsonify({"error": "Parámetros esperados: origen_lon, origen_lat, destino_lon, destino_lat"}), 400

    try:
        with engine.connect() as conn:
            rutas = {criterio: calcular_ruta(conn, origen, destino, criterio) for criterio in QUERY_EDGES}
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(rutas)


if __name__ == "__main__":
    app.run(debug=True)
