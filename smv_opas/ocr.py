"""OCR local de Prospectos Informativos escaneados (sin capa de texto),
para los expedientes donde el comando `pdfs` extrajo un .txt casi vacio.

Pipeline 100% local, sin servicio externo:
    pymupdf (render de pagina a imagen, 300dpi) -> tesseract -l spa (OCR)

Solo procesa las primeras MAX_PAGINAS de cada PDF -- el precio ofertado
siempre esta en la caratula o el Resumen Ejecutivo (paginas 1-10 en todos
los casos verificados a mano hasta ahora), y varios expedientes tienen
cientos de paginas de anexos/estados financieros que no hace falta OCRear.
Si un expediente puntual no tiene el precio en esas paginas, se re-procesa
aparte con --paginas mas alto.

Requiere tesseract instalado con datos de idioma 'spa' (ver
scoop install tesseract + tessdata copiado a mano si el instalador falla).

Uso:
    python -m smv_opas ocr 24079 24078 23982
    python -m smv_opas ocr --paginas 20 24079
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

RAIZ = Path.cwd()
PDFS_DIR = RAIZ / "data" / "raw" / "opas_pdfs"

MAX_PAGINAS_DEFAULT = 15


def ocr_pdf(pdf_path, max_paginas):
    doc = pymupdf.open(pdf_path)
    n = min(max_paginas, doc.page_count)
    partes = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(n):
            pix = doc[i].get_pixmap(dpi=300)
            png_path = Path(tmpdir) / f"p{i+1}.png"
            pix.save(str(png_path))
            out_base = Path(tmpdir) / f"p{i+1}"
            subprocess.run(
                ["tesseract", str(png_path), str(out_base), "-l", "spa"],
                check=True, capture_output=True,
            )
            texto = (out_base.with_suffix(".txt")).read_text(encoding="utf-8")
            partes.append(f"--- pagina {i+1}/{doc.page_count} (OCR) ---\n{texto}")
    return "\n".join(partes), doc.page_count, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("expedientes", nargs="+")
    ap.add_argument("--paginas", type=int, default=MAX_PAGINAS_DEFAULT)
    args = ap.parse_args()

    for eid in args.expedientes:
        pdf_path = PDFS_DIR / f"{eid}.pdf"
        txt_path = PDFS_DIR / f"{eid}.txt"
        if not pdf_path.exists():
            print(f"[{eid}] no existe {pdf_path.name}, se omite")
            continue
        print(f"[{eid}] OCR en curso...", end=" ", flush=True)
        try:
            texto, total_paginas, procesadas = ocr_pdf(pdf_path, args.paginas)
        except Exception as e:
            print(f"ERROR: {e}")
            continue
        txt_path.write_text(texto, encoding="utf-8")
        print(f"OK: {procesadas}/{total_paginas} paginas -> {txt_path.name} ({len(texto)} chars)")


if __name__ == "__main__":
    main()
