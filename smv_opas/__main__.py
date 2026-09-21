"""Interfaz de linea de comandos: python -m smv_opas <comando> [argumentos]"""
import importlib
import sys

COMANDOS = {
    "expedientes": ("expedientes", "Lista maestra de expedientes de OPA/OPC de SMV"),
    "documentos": ("documentos", "Documentos de cada expediente (fechas, tipo, url)"),
    "pdfs": ("pdfs", "Descarga prospectos y los pasa a texto"),
    "ocr": ("ocr", "OCR para prospectos escaneados (requiere Tesseract)"),
    "dataset": ("construir_dataset", "Una fila por operacion, clasificada"),
    "precios": ("precio_auto", "Precio ofertado y oferente por regex (a revisar a mano)"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print("Uso: python -m smv_opas <comando> [argumentos]\n")
        for c, (_, desc) in COMANDOS.items():
            print(f"  {c:<12} {desc}")
        sys.exit(0 if len(sys.argv) < 2 else 1)
    cmd = sys.argv[1]
    sys.argv = [f"smv_opas {cmd}"] + sys.argv[2:]
    importlib.import_module(f"smv_opas.{COMANDOS[cmd][0]}").main()


if __name__ == "__main__":
    main()
