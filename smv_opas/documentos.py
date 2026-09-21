"""Descarga, para cada expediente OPA de data/opas_expedientes_smv.csv, la
grilla de documentos asociada (postback sobre el dropdown lisDenominacion de
Frm_Opas) y la vuelca a un CSV plano (una fila por documento).

Usa el patron WebForms de SIMV (postback con requests,
sin Selenium/Playwright).

Uso (desde la raiz del repo):
    python -m smv_opas documentos [--limit N] [--out data/opas_documentos_smv.csv]
"""
import argparse
import csv
import html as ihtml
import re
import sys
import time
from pathlib import Path

import requests

URL = "https://www.smv.gob.pe/SIMV/Frm_Opas?data=B0BAD43B72085E6947D724B1B24FA334D125F9653C"
PAUSA = 1.3  # s, cortesia entre requests
REINTENTOS = 2


def hidden(html_txt):
    out = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION",
                 "__PREVIOUSPAGE", "__LASTFOCUS"):
        m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html_txt)
        out[name] = m.group(1) if m else ""
    return out


def parse_grilla(pagina_html):
    """Devuelve lista de dicts: fecha, tramite, fecha_doc, documento, url."""
    m = re.search(
        r'<table[^>]*id="MainContent_gvPublicacion"[^>]*>(.*?)</table>',
        pagina_html, re.S,
    )
    if not m:
        return []
    filas = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S)
    out = []
    for f in filas:
        if "header-grid" in f:
            continue
        celdas = re.findall(r"<td[^>]*>(.*?)</td>", f, re.S)
        if len(celdas) < 5:
            continue
        fecha, tramite, fecha_doc, documento, col_link = celdas[:5]
        limpiar = lambda s: ihtml.unescape(re.sub(r"<[^>]+>", "", s)).strip()
        href = re.search(r'href="([^"]+)"', col_link)
        out.append({
            "fecha": limpiar(fecha),
            "tramite": limpiar(tramite),
            "fecha_doc": limpiar(fecha_doc),
            "documento": limpiar(documento),
            "url": href.group(1) if href else "",
        })
    return out


def consultar_expediente(sesion, pagina_inicial_html, expediente_id):
    """POST postback seleccionando expediente_id en lisDenominacion. Devuelve HTML resultante."""
    data = hidden(pagina_inicial_html)
    data.update({
        "__EVENTTARGET": "ctl00$MainContent$lisDenominacion",
        "__EVENTARGUMENT": "",
        "ctl00$MainContent$lisDenominacion": str(expediente_id),
        "ctl00$MainContent$txtDesDoc": "",
        "ctl00$MainContent$ddlAnio": "-1",
    })
    r = sesion.post(URL, data=data, timeout=60)
    r.raise_for_status()
    return r.text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expedientes", default="data/opas_expedientes_smv.csv")
    ap.add_argument("--out", default="data/opas_documentos_smv.csv")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    filas_exp = list(csv.DictReader(open(args.expedientes, encoding="utf-8")))
    if args.limit:
        filas_exp = filas_exp[: args.limit]

    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    pagina_inicial = s.get(URL, timeout=60).text

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not out_path.exists()
    fh = open(out_path, "a", newline="", encoding="utf-8")
    w = csv.writer(fh)
    if nuevo:
        w.writerow(["expediente_id", "expediente_titulo", "fecha", "tramite",
                    "fecha_doc", "documento", "url"])

    total = len(filas_exp)
    for i, fila in enumerate(filas_exp, 1):
        eid = fila["expediente_id"]
        titulo = fila["titulo"]
        docs = None
        for intento in range(1, REINTENTOS + 1):
            try:
                html_resp = consultar_expediente(s, pagina_inicial, eid)
                docs = parse_grilla(html_resp)
                break
            except Exception as e:
                print(f"[{i}/{total}] {eid}: fallo intento {intento} ({e})", flush=True)
                time.sleep(3)
        if docs is None:
            print(f"[{i}/{total}] {eid}: ERROR definitivo, se omite", flush=True)
            continue
        if not docs:
            # sin documentos parseados: registrar al menos el expediente
            w.writerow([eid, titulo, "", "", "", "", ""])
        for d in docs:
            w.writerow([eid, titulo, d["fecha"], d["tramite"], d["fecha_doc"],
                        d["documento"], d["url"]])
        fh.flush()
        print(f"[{i}/{total}] {eid}: {len(docs)} documentos", flush=True)
        time.sleep(PAUSA)

    fh.close()
    print(f"listo -> {out_path}")


if __name__ == "__main__":
    main()
