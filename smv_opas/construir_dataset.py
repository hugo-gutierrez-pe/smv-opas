"""Construye OPAs_Peru_dataset.csv (una fila por operacion) a partir de:
    - data/opas_expedientes_smv.csv       (catalogo maestro de expedientes)
    - data/opas_documentos_smv.csv        (documentos por expediente, con fechas)

Clasifica cada expediente (opa / opc_exclusion / seleccion_valorizadora /
mejora_opa) y extrae empresa objetivo / oferente del titulo con heuristicas
de regex. ADVERTENCIA: la extraccion de nombres de empresa es heuristica,
no exacta -- requiere QA manual antes de usarse en el paper (ver columna
`revisar`).

Uso:
    python -m smv_opas dataset
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

RAIZ = Path.cwd()
EXPEDIENTES_CSV = RAIZ / "data" / "opas_expedientes_smv.csv"
DOCUMENTOS_CSV = RAIZ / "data" / "opas_documentos_smv.csv"
OUT_CSV = RAIZ / "data" / "OPAs_Peru_dataset.csv"

SUFIJO = (r"(?:S\.?A\.?A\.?|S\.?A\.?C\.?|S\.?R\.?L\.?|S\.?L\.?U\.?|S\.?L\.?|S\.?A\.?|"
          r"ASA|Corp\.?|Ltd\.?|PLC|LP|Inc\.?|AG|N\.?V\.?|B\.?V\.?)")
RE_EMPRESA = re.compile(
    r"([A-ZÁÉÍÓÚÑ][\wÀ-ÿ&\.,\-\s]{2,80}?\s" + SUFIJO + r")(?=\s|,|\.|$)"
)
MARCADORES_OFERENTE = ("por parte de", "formulada por", "formulado por", "realizada por")


def limpiar_nombre(s):
    """Quita artefactos de arrastre como 'Clase A de ' / 'B de ' capturados por error."""
    s = re.sub(r"^(?:Clase\s+)?[A-Z]\s+de\s+", "", s)
    return s.strip(" .,")


def clasificar_tipo(titulo):
    t = titulo.lower()
    if "selecci" in t and ("valorizador" in t or "precio m" in t or "entidad responsable" in t):
        return "seleccion_valorizadora"
    if "exclusi" in t or re.search(r"\bopc\b", t):
        return "opc_exclusion"
    if t.startswith("mejora"):
        return "mejora_opa"
    if "redenci" in t or "canje" in t:
        return "redencion_canje"
    return "opa"


def clasificar_subtipo(titulo):
    t = titulo.lower()
    partes = []
    if "previa" in t:
        partes.append("previa")
    if "posterior" in t:
        partes.append("posterior")
    if "voluntaria" in t:
        partes.append("voluntaria")
    if "obligatoria" in t:
        partes.append("obligatoria")
    return "|".join(partes)


def extraer_empresas(titulo):
    """Heuristica: separa oferente (tras 'por parte de'/'formulada por') del resto;
    toma la ultima empresa con sufijo societario de cada tramo como objetivo/oferente."""
    oferente = ""
    objetivo_zona = titulo
    for marcador in MARCADORES_OFERENTE:
        idx = titulo.lower().find(marcador)
        if idx != -1:
            zona_oferente = titulo[idx + len(marcador):]
            m = RE_EMPRESA.search(zona_oferente)
            if m:
                oferente = limpiar_nombre(m.group(1))
            objetivo_zona = titulo[:idx]
            break

    candidatos = RE_EMPRESA.findall(objetivo_zona)
    objetivo = limpiar_nombre(candidatos[-1]) if candidatos else ""
    return objetivo, oferente


def main():
    expedientes = list(csv.DictReader(open(EXPEDIENTES_CSV, encoding="utf-8")))

    fechas_por_exp = defaultdict(list)
    ndocs_por_exp = defaultdict(int)
    if DOCUMENTOS_CSV.exists():
        for fila in csv.DictReader(open(DOCUMENTOS_CSV, encoding="utf-8")):
            eid = fila["expediente_id"]
            ndocs_por_exp[eid] += 1
            for campo in ("fecha", "fecha_doc"):
                v = fila.get(campo, "").strip()
                if v:
                    fechas_por_exp[eid].append(v)

    def a_fecha_ordenable(s):
        try:
            d, m, a = s.split("/")
            return (a, m, d)
        except ValueError:
            return ("0000", "00", "00")

    filas_out = []
    for exp in expedientes:
        eid = exp["expediente_id"]
        titulo = exp["titulo"]
        tipo = clasificar_tipo(titulo)
        subtipo = clasificar_subtipo(titulo)
        objetivo, oferente = extraer_empresas(titulo)
        fechas = sorted(fechas_por_exp.get(eid, []), key=a_fecha_ordenable)
        revisar = "SI" if not objetivo else ""
        filas_out.append({
            "expediente_id": eid,
            "tipo_operacion": tipo,
            "subtipo": subtipo,
            "empresa_objetivo": objetivo,
            "empresa_oferente": oferente,
            "fecha_primer_doc": fechas[0] if fechas else "",
            "fecha_ultimo_doc": fechas[-1] if fechas else "",
            "num_documentos": ndocs_por_exp.get(eid, 0),
            "titulo_original": titulo,
            "revisar": revisar,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        campos = ["expediente_id", "tipo_operacion", "subtipo", "empresa_objetivo",
                  "empresa_oferente", "fecha_primer_doc", "fecha_ultimo_doc",
                  "num_documentos", "titulo_original", "revisar"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas_out)

    n_opa = sum(1 for f in filas_out if f["tipo_operacion"] == "opa")
    n_opc = sum(1 for f in filas_out if f["tipo_operacion"] == "opc_exclusion")
    n_sel = sum(1 for f in filas_out if f["tipo_operacion"] == "seleccion_valorizadora")
    n_revisar = sum(1 for f in filas_out if f["revisar"] == "SI")
    print(f"{len(filas_out)} expedientes -> {OUT_CSV}")
    print(f"  opa (transferencia de control): {n_opa}")
    print(f"  opc_exclusion (delisting):      {n_opc}")
    print(f"  seleccion_valorizadora (tramite previo, no es la operacion en si): {n_sel}")
    print(f"  otros: {len(filas_out) - n_opa - n_opc - n_sel}")
    print(f"  sin empresa objetivo detectada (revisar manualmente): {n_revisar}")


if __name__ == "__main__":
    main()
