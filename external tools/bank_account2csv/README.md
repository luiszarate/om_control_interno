# bank_account2csv

Extrae movimientos de estados de cuenta Banco del Bajío (PDF) a formato CSV.

## Requisitos

- Python 3.10+
- [pdfplumber](https://github.com/jsvine/pdfplumber)

```bash
pip install pdfplumber
```

## Uso

```bash
python extract.py PDFs/archivo.pdf [salida.csv]
```

Si no se especifica archivo de salida, se genera con el mismo nombre que el PDF:

```bash
python extract.py PDFs/2034_036232650_1.pdf
# → genera PDFs/2034_036232650_1.csv

python extract.py PDFs/2034_036232650_1.pdf movimientos_sep.csv
```

## Columnas del CSV

| Columna | Descripción |
|---|---|
| `cuenta` | Número de cuenta bancaria |
| `fecha` | Fecha en formato ISO (YYYY-MM-DD) |
| `dia` | Día del movimiento |
| `mes` | Mes del movimiento (número) |
| `anio` | Año del movimiento |
| `referencia` | Número de referencia / folio |
| `descripcion` | Descripción completa del movimiento (incluye detalles SPEI, beneficiario, etc.) |
| `deposito` | Monto del depósito (vacío si es retiro) |
| `retiro` | Monto del retiro (vacío si es depósito) |
| `saldo` | Saldo después del movimiento |

## Notas

- Cada PDF puede contener múltiples cuentas; el script las separa automáticamente.
- La descripción incluye detalles de la transacción (institución receptora, beneficiario, clave de rastreo, etc.) separados por ` | `.
- Los totales de movimientos extraídos se validan contra los reportados en el PDF.
