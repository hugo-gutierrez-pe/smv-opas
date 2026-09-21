"""Descarga los Prospectos Informativos (u otro documento clave) de expedientes
OPA desde SMV y extrae su texto con fitz/pymupdf, para lectura manual/IA y
extraccion de oferente + precio ofrecido.

No parsea precio/oferente automaticamente (los prospectos no tienen formato
fijo) -- guarda el .txt para lectura directa, igual que la curacion manual
de titulos (la lectura es manual).

Uso:
    python -m smv_opas pdfs 23493 20917 22898
    python -m smv_opas pdfs --tipo-doc "Prospecto Informativo" 23493
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import pymupdf
import requests

RAIZ = Path.cwd()
DOCUMENTOS_CSV = RAIZ / "data" / "opas_documentos_smv.csv"
OUT_DIR = RAIZ / "data" / "raw" / "opas_pdfs"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PAUSA = 1.3

TIPOS_PREFERIDOS = ("prospecto informativo", "aviso de oferta", "prospecto")


def a_fecha_ordenable(s):
    try:
        d, m, a = s.split("/")
        return (a, m, d)
    except ValueError:
        return ("0000", "00", "00")


def elegir_documento(filas, tipo_doc_filtro=None):
    """De las filas de un expediente, elige el mejor Prospecto Informativo
    (el mas reciente si hay rectificatorias/subsanaciones)."""
    candidatas = filas
    if tipo_doc_filtro:
        candidatas = [f for f in filas if tipo_doc_filtro.lower() in f["documento"].lower()]
    else:
        for tipo in TIPOS_PREFERIDOS:
            match = [f for f in filas if tipo in f["documento"].lower()]
            if match:
                candidatas = match
                break
    if not candidatas:
        return None
    return sorted(candidatas, key=lambda f: a_fecha_ordenable(f["fecha_doc"]))[-1]


def descargar_pdf(url, destino_pdf):
    if destino_pdf.exists():
        return True
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    r = sesion.get(url, allow_redirects=True, timeout=30)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        print(f"  AVISO: respuesta no es PDF (magic bytes) -- {url}")
        return False
    destino_pdf.write_bytes(r.content)
    return True


def extraer_texto(pdf_path, txt_path):
    doc = pymupdf.open(pdf_path)
    partes = [f"--- pagina {i+1}/{doc.page_count} ---\n{pagina.get_text()}" for i, pagina in enumerate(doc)]
    txt_path.write_text("\n".join(partes), encoding="utf-8")
    return doc.page_count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("expedientes", nargs="+", help="expediente_id(s) a procesar")
    ap.add_argument("--tipo-doc", default=None, help="filtrar por texto exacto en columna 'documento'")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    docs_por_exp = {}
    with open(DOCUMENTOS_CSV, encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            docs_por_exp.setdefault(fila["expediente_id"], []).append(fila)

    for eid in args.expedientes:
        filas = docs_por_exp.get(eid, [])
        if not filas:
            print(f"[{eid}] sin documentos catalogados, se omite")
            continue
        elegido = elegir_documento(filas, args.tipo_doc)
        if not elegido:
            print(f"[{eid}] no se encontro Prospecto/Aviso, se omite")
            continue

        pdf_path = OUT_DIR / f"{eid}.pdf"
        txt_path = OUT_DIR / f"{eid}.txt"
        print(f"[{eid}] {elegido['documento']} ({elegido['fecha_doc']}) -> {pdf_path.name}")
        try:
            ok = descargar_pdf(elegido["url"], pdf_path)
        except requests.RequestException as e:
            print(f"  ERROR descarga: {e}")
            continue
        if not ok:
            continue
        try:
            npaginas = extraer_texto(pdf_path, txt_path)
        except Exception as e:
            print(f"  ERROR extraccion texto: {e}")
            continue
        print(f"  OK: {npaginas} paginas -> {txt_path.name}")
        time.sleep(PAUSA)


if __name__ == "__main__":
    main()
