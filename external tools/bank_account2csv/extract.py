#!/usr/bin/env python3
"""
extract.py - Extrae movimientos de estados de cuenta Banco del Bajío (PDF → CSV)

Uso:
    python extract.py archivo.pdf [salida.csv]
    python extract.py PDFs/2034_036232650_1.pdf
    python extract.py PDFs/2034_036232650_1.pdf movimientos.csv

Requiere: pdfplumber  →  pip install pdfplumber
"""

import sys
import csv
import re
import pdfplumber
from collections import defaultdict
from pathlib import Path

# ─── Límites de columnas (coordenadas X del PDF) ─────────────────────────────
X_FECHA_MAX = 55      # FECHA:       x0 < 55
X_DESC_MAX  = 390     # DESCRIPCION: 55 ≤ x0 < 390
X_DEP_MAX   = 470     # DEPOSITOS:   390 ≤ x0 < 470
X_RET_MAX   = 545     # RETIROS:     470 ≤ x0 < 545
                      # SALDO:       x0 ≥ 545

# ─── Mapeo de meses ──────────────────────────────────────────────────────────
MESES = {
    'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
}

# Palabras que indican encabezado de tabla (se omiten)
HEADER_WORDS = {
    'FECHA', 'DESCRIPCION', 'DEPOSITOS', 'RETIROS', 'SALDO',
    'DOCTO', 'REF.', 'NO.'
}

# ─── Patrones de control de sección ──────────────────────────────────────────
# Marca el inicio de la sección de transacciones de una cuenta
_PAT_SECTION_START = re.compile(r'DETALLE DE LA CUENTA:', re.IGNORECASE)
# Marca el final de la sección de transacciones (inicio del resumen)
_PAT_SECTION_END = re.compile(r'SALDO TOTAL\*|TOTAL DE MOVIMIENTOS', re.IGNORECASE)
# Líneas de pie de página / continuación que deben ignorarse siempre
_PAT_SKIP = re.compile(
    r'CONTINUA EN LA SIGUIENTE PAGINA|PAGINA \d+ DE \d+',
    re.IGNORECASE
)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def words_to_text(words):
    """Une palabras en una cadena de texto."""
    return ' '.join(w['text'] for w in words).strip()


def is_table_header(row_words):
    """Detecta si la fila es un encabezado de la tabla de movimientos."""
    texts = {w['text'] for w in row_words}
    return bool(texts & HEADER_WORDS)


def parse_amount(words):
    """Extrae monto numérico de lista de palabras (ignora '$')."""
    text = ' '.join(w['text'] for w in words if w['text'].strip() not in ('$', ''))
    text = text.replace(',', '').strip()
    try:
        return float(text)
    except ValueError:
        return None


def is_valid_date(date_words):
    """
    Valida que las palabras representen una fecha real tipo "1 SEP", "15 ENE".
    Evita falsos positivos en el encabezado del PDF.
    """
    text = words_to_text(date_words)
    parts = text.split()
    return (len(parts) >= 2
            and parts[0].isdigit()
            and 1 <= int(parts[0]) <= 31
            and parts[1].upper() in MESES)


def parse_date(date_text, year):
    """Parsea "15 SEP" → (15, 9, year)."""
    parts = date_text.split()
    dia = int(parts[0]) if parts and parts[0].isdigit() else None
    mes_str = parts[1].upper() if len(parts) > 1 else ''
    mes_num = MESES.get(mes_str)
    return dia, mes_num, year


def split_ref_and_desc(text):
    """
    Separa número de referencia del inicio de la descripción.
    "2187642COMPRA-DISPOSICION..." → ("2187642", "COMPRA-DISPOSICION...")
    "76 CHEQUE PAGADO..."          → ("76", "CHEQUE PAGADO...")
    "COMISION POR TRANSFERENCIA"   → ("", "COMISION POR TRANSFERENCIA")
    """
    match = re.match(r'^(\d{2,})([A-ZÁÉÍÓÚÑÜ\(\s\-].*|$)', text)
    if match:
        return match.group(1), match.group(2).strip()
    return '', text


def extract_year(pdf):
    """Extrae el año del periodo desde la primera página."""
    text = pdf.pages[0].extract_text() or ''
    m = re.search(r'PERIODO:.*?(\d{4})\s*$', text, re.MULTILINE | re.IGNORECASE)
    return int(m.group(1)) if m else None


# ─── Extracción principal ─────────────────────────────────────────────────────

def extract_transactions(pdf_path):
    """
    Procesa el PDF y retorna lista de transacciones.
    Maneja múltiples cuentas dentro del mismo PDF.
    """
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        year = extract_year(pdf)
        current_account = ''
        in_tx_section = False   # dentro de la sección de movimientos
        current_tx = None

        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)

            # Agrupar palabras por fila (coordenada Y)
            rows = defaultdict(list)
            for w in words:
                rows[round(w['top'])].append(w)

            for top in sorted(rows.keys()):
                row_words = sorted(rows[top], key=lambda w: w['x0'])
                all_text = words_to_text(row_words)

                # ── Omitir encabezados de tabla ────────────────────────────
                if is_table_header(row_words):
                    continue

                # ── Omitir pie de página / texto de continuación ───────────
                if _PAT_SKIP.search(all_text):
                    continue

                # ── Omitir "SALDO INICIAL" ─────────────────────────────────
                if re.search(r'SALDO\s+INICIAL', all_text, re.IGNORECASE):
                    continue

                # ── Detectar inicio de sección de cuenta ───────────────────
                if _PAT_SECTION_START.search(all_text):
                    in_tx_section = True
                    current_tx = None
                    # Extraer número de cuenta del encabezado "#XXXXXXXXXXX"
                    m = re.search(r'#(\d+)', all_text)
                    if m:
                        current_account = m.group(1)
                    continue

                # ── Detectar fin de sección de cuenta ──────────────────────
                if _PAT_SECTION_END.search(all_text):
                    in_tx_section = False
                    current_tx = None
                    continue

                # ── Ignorar contenido fuera de sección ─────────────────────
                if not in_tx_section:
                    continue

                # ── Clasificar palabras por columna ───────────────────────
                date_words  = [w for w in row_words if w['x0'] < X_FECHA_MAX]
                desc_words  = [w for w in row_words if X_FECHA_MAX <= w['x0'] < X_DESC_MAX]
                dep_words   = [w for w in row_words if X_DESC_MAX  <= w['x0'] < X_DEP_MAX]
                ret_words   = [w for w in row_words if X_DEP_MAX   <= w['x0'] < X_RET_MAX]
                saldo_words = [w for w in row_words if w['x0'] >= X_RET_MAX]

                has_date   = bool(date_words) and is_valid_date(date_words)
                has_amount = bool(dep_words or ret_words)

                # ── Línea de continuación (sin fecha ni monto) ─────────────
                if not has_date and not has_amount:
                    if current_tx and all_text:
                        current_tx['detalles'].append(all_text)
                    continue

                # ── Nueva transacción (tiene fecha) ───────────────────────
                if has_date:
                    date_text = words_to_text(date_words)
                    desc_text = words_to_text(desc_words)
                    dia, mes, anio = parse_date(date_text, year)
                    ref, desc = split_ref_and_desc(desc_text)

                    deposito = parse_amount(dep_words)   if dep_words   else None
                    retiro   = parse_amount(ret_words)   if ret_words   else None
                    saldo    = parse_amount(saldo_words) if saldo_words else None

                    current_tx = {
                        'cuenta':      current_account,
                        'dia':         dia,
                        'mes':         mes,
                        'anio':        anio,
                        'referencia':  ref,
                        'descripcion': desc,
                        'detalles':    [],
                        'deposito':    deposito,
                        'retiro':      retiro,
                        'saldo':       saldo,
                    }
                    transactions.append(current_tx)

                # ── Monto sin fecha (no debería ocurrir normalmente) ───────
                elif has_amount and current_tx:
                    if desc_words:
                        extra = words_to_text(desc_words)
                        if extra:
                            current_tx['detalles'].append(extra)

    return transactions


# ─── Formato CSV ─────────────────────────────────────────────────────────────

CSV_HEADER = [
    'FECHA', 'Etapa No.', 'DESCRIPCIÓN', 'MONTO',
    'FECHA', 'RETIRO', 'DEPÓSITO', 'SALDO', 'DIFERENCIA', 'OBSERVACIONES'
]


def build_csv_rows(transactions):
    """Convierte la lista de transacciones a filas para el CSV."""
    rows = []
    for tx in transactions:
        detalles = ' | '.join(tx['detalles']) if tx['detalles'] else ''
        desc_completa = tx['descripcion']
        if detalles:
            desc_completa = f"{desc_completa} | {detalles}" if desc_completa else detalles

        if tx['dia'] and tx['mes'] and tx['anio']:
            fecha_iso = f"{tx['anio']:04d}-{tx['mes']:02d}-{tx['dia']:02d}"
        else:
            fecha_iso = ''

        deposito = tx['deposito']
        retiro   = tx['retiro']

        if deposito is not None:
            monto      = deposito
            diferencia = deposito
        elif retiro is not None:
            monto      = -retiro
            diferencia = -retiro
        else:
            monto      = ''
            diferencia = ''

        rows.append([
            fecha_iso,
            '',
            desc_completa,
            monto,
            fecha_iso,
            retiro   if retiro   is not None else '',
            deposito if deposito is not None else '',
            tx['saldo'] if tx['saldo'] is not None else '',
            diferencia,
            '',
        ])
    return rows


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: no se encontró el archivo '{pdf_path}'")
        sys.exit(1)

    # Si el usuario pasa un directorio de salida lo usamos; si pasa un archivo
    # lo tomamos como prefijo base (sin extensión).
    base_out = Path(sys.argv[2]) if len(sys.argv) >= 3 else pdf_path.parent / pdf_path.stem

    print(f"Procesando: {pdf_path}")
    transactions = extract_transactions(pdf_path)

    # Agrupar transacciones por cuenta
    by_account = defaultdict(list)
    for tx in transactions:
        by_account[tx['cuenta']].append(tx)

    total = 0
    for cuenta, txs in by_account.items():
        rows = build_csv_rows(txs)
        csv_path = Path(f"{base_out}_{cuenta}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
        print(f"  Cuenta {cuenta}: {len(rows)} movimientos → {csv_path}")
        total += len(rows)

    print(f"Total: {total} movimientos en {len(by_account)} cuenta(s)")


if __name__ == '__main__':
    main()
