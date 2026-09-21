"""Extraccion automatica (regex) de precio ofertado + oferente desde los
.txt de Prospectos Informativos ya descargados (ver el comando `pdfs`).

Validado contra los 3 casos piloto leidos a mano (Enel-Niagara, Luz del Sur,
Alicorp) en una lectura manual previa -- el parrafo de apertura del prospecto
sigue casi siempre el patron "El Ofertante ofrece pagar la suma de <MONTO>
... por cada Accion". Cuando el regex no encuentra match con confianza,
NO inventa: deja el campo vacio y marca confianza='revisar'.

Esto es automatizacion tipo regex (barata, no 100% precisa) -- a diferencia
de la lectura humana verificada. Ambas conviven
en el dataset final con su propio metodo_precio para no mezclar fuentes de
distinta confiabilidad (ver columna metodo_precio: 'lectura_prospecto' vs
'regex_auto' vs 'pendiente').

Uso:
    python -m smv_opas precios
"""
import csv
import re
from pathlib import Path

RAIZ = Path.cwd()
PDFS_DIR = RAIZ / "data" / "raw" / "opas_pdfs"
OUT_CSV = RAIZ / "data" / "opas_precio_auto.csv"

RE_PRECIO = re.compile(
    r"(?:ofrece\s+pagar|pagar[áa])\s+(?:la\s+suma\s+de\s+)?(US\$|USD|S/\.?|LIS\$)\s*([\d,]+\.\d+)"
    r"(?:[^.]{0,40}por\s+cada\s+[Aa]cci[oó]n)?",
    re.IGNORECASE,
)
# "LIS$" es un typo de OCR/extracción de PDF sobre "US$" (ligadura rota) visto
# en al menos un prospecto real -- se trata como USD.

# candidatos de oferente, en orden de confianza decreciente
RE_OFERENTE_CANDIDATOS = [
    re.compile(r'El\s+Ofertante\s+es\s+([A-ZÁÉÍÓÚÑ][\wÀ-ÿ&\.,\-\s]{2,80}?),\s', re.UNICODE),
    re.compile(r'([A-ZÁÉÍÓÚÑ][\wÀ-ÿ&\.\-\s]{2,80}?)\s*\(indistintamente,[^)]*el\s*[""“”]Ofertante[""“”]\)', re.UNICODE),
    re.compile(r'([A-ZÁÉÍÓÚÑ][\wÀ-ÿ&\.\-\s]{2,80}?),?\s+[^.]{0,120}?se\s+constituye\s+como\s+(?:el\s+)?[Oo]fertante', re.UNICODE),
]


def limpiar(s):
    return re.sub(r"\s+", " ", s).strip(" .,")


def extraer(texto):
    # antes se limitaba a los primeros 20000 caracteres ("cabecera"), pero al
    # menos un prospecto real (expediente 13552) tiene la clausula de precio
    # mas alla de ese limite (declaraciones/anexos extensos antes) -- se
    # busca en el texto completo.
    cabecera = texto

    precio = moneda = ""
    m = RE_PRECIO.search(cabecera)
    if m:
        moneda = "USD" if m.group(1).upper().startswith(("US", "LIS")) else "PEN"
        precio = m.group(2).replace(",", "")

    # oferente por regex es poco confiable (validado contra los 3 pilotos:
    # 2/3 fallaron o dieron texto basura) -- se guarda solo como pista, NUNCA
    # se usa como verdad sin lectura humana.
    oferente_candidato = ""
    for rgx in RE_OFERENTE_CANDIDATOS:
        m = rgx.search(cabecera)
        if m:
            candidato = limpiar(m.group(1))
            if 4 <= len(candidato) <= 90:
                oferente_candidato = candidato
                break

    confianza = "precio_ok" if precio else "revisar"
    return precio, moneda, oferente_candidato, confianza


def main():
    filas = []
    for txt_path in sorted(PDFS_DIR.glob("*.txt")):
        eid = txt_path.stem
        texto = txt_path.read_text(encoding="utf-8", errors="replace")
        precio, moneda, oferente_candidato, confianza = extraer(texto)
        filas.append({
            "expediente_id": eid,
            "precio_ofertado_auto": precio,
            "moneda_auto": moneda,
            "oferente_candidato_SIN_VERIFICAR": oferente_candidato,
            "confianza": confianza,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        campos = ["expediente_id", "precio_ofertado_auto", "moneda_auto",
                   "oferente_candidato_SIN_VERIFICAR", "confianza"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    n_ok = sum(1 for f in filas if f["confianza"] == "precio_ok")
    n_revisar = sum(1 for f in filas if f["confianza"] == "revisar")
    print(f"{len(filas)} prospectos procesados -> {OUT_CSV}")
    print(f"  precio detectado (regex): {n_ok}")
    print(f"  revisar manualmente (sin precio detectado): {n_revisar}")


if __name__ == "__main__":
    main()
