# smv-opas

Extrae y ordena las ofertas públicas de adquisición (OPA) y de compra por exclusión (OPC) registradas en la SMV del Perú. Es la parte reutilizable de una investigación sobre OPAs en Latinoamérica.

La SMV publica cada expediente en un formulario web (SIMV, «Ofertas Públicas de Adquisición»). Este repo lo convierte en tablas:

| Comando | Qué hace | Salida |
|---|---|---|
| `expedientes` | Lee el menú con todos los expedientes (2005 en adelante) | `data/opas_expedientes_smv.csv` |
| `documentos` | Por postback del formulario, lista los documentos de cada expediente | `data/opas_documentos_smv.csv` |
| `pdfs` | Descarga el prospecto informativo y lo pasa a texto (PyMuPDF) | `data/raw/opas_pdfs/` |
| `ocr` | OCR en español para prospectos escaneados (Tesseract) | `data/raw/opas_pdfs/*.txt` |
| `dataset` | Una fila por operación: OPA, OPC, selección de valorizadora, etc. | `data/OPAs_Peru_dataset.csv` |
| `precios` | Precio ofertado y oferente por expresiones regulares | `data/opas_precio_auto.csv` |

## Uso

```bash
pip install -r requirements.txt          # requests, pymupdf
python -m smv_opas expedientes           # ~120 expedientes
python -m smv_opas documentos --limit 5  # prueba con 5
python -m smv_opas pdfs 25638            # prospecto de un expediente
python -m smv_opas dataset
```

Los datos se guardan en `data/` dentro de la carpeta desde donde corres el comando. No usa Selenium: son requests contra el formulario, con una pausa de cortesía entre consultas.

## Límites

- El portal cambia sin aviso: si `expedientes` falla con «no se encontró el select», cambió el HTML.
- Los prospectos no tienen formato fijo. `precios` detecta por regex y marca `revisar` cuando no está seguro; el precio debe verificarse a mano en el documento.
- La extracción de empresa y oferente desde el título de cada expediente es heurística: revisa la columna `revisar` del dataset.
- `ocr` requiere Tesseract con el idioma `spa`.
- Son documentos públicos de la SMV; respeta sus condiciones de uso y no aumentes la frecuencia de consultas.

## Origen

Extraído de un proyecto de investigación más grande (event study de OPAs en Perú, Brasil, Chile y México) que aún no es público. Aquí solo va la parte de SMV.
