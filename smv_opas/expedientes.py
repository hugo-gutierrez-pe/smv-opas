"""Extrae el listado maestro de expedientes OPA desde el dropdown de Frm_Opas.

El select ctl00$MainContent$lisDenominacion contiene TODOS los expedientes de
Ofertas Publicas de Adquisicion/Compra registrados en SMV (no solo los "en
proceso" del titulo de la pagina) -- va de valor mas reciente (2026) hasta
los mas antiguos (~2005-2008, ej. "Backus", id 5531).

Uso:
    python -m smv_opas expedientes [out.csv]
"""
import csv
import html as ihtml
import re
import sys
from pathlib import Path

import requests

URL = "https://www.smv.gob.pe/SIMV/Frm_Opas?data=B0BAD43B72085E6947D724B1B24FA334D125F9653C"


def obtener_html():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    r = s.get(URL, timeout=60)
    r.raise_for_status()
    return r.text


def extraer_dropdown(pagina_html):
    m = re.search(
        r'<select name="ctl00\$MainContent\$lisDenominacion".*?</select>',
        pagina_html, re.S,
    )
    if not m:
        raise RuntimeError("No se encontro el select lisDenominacion (¿cambio la pagina?)")
    bloque = m.group(0)
    opciones = re.findall(r'<option[^>]*value="(-?\d+)"[^>]*>(.*?)</option>', bloque, re.S)
    return [
        (valor, ihtml.unescape(texto).strip())
        for valor, texto in opciones
        if valor != "-1"
    ]


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/opas_expedientes_smv.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pagina = obtener_html()
    filas = extraer_dropdown(pagina)

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["expediente_id", "titulo"])
        w.writerows(filas)

    print(f"{len(filas)} expedientes OPA extraidos -> {out_path}")
    print("Mas reciente:", filas[0])
    print("Mas antiguo: ", filas[-1])


if __name__ == "__main__":
    main()
