# models/bank_pdf_parsers/bajio.py
"""Banco del Bajío statement PDF parser.

Ported from ``external tools/bank_account2csv/extract.py`` for use inside
the Odoo module. Reads PDF bytes (no filesystem access required) and
returns structured statements ready to be persisted as
``estado.cuenta.bancario.line`` records.
"""

import io
import logging
import re
from collections import defaultdict
from typing import Optional

from .base import BankStatementParser, ParsedStatement, ParsedTransaction, register

_logger = logging.getLogger(__name__)

# Column X-coordinate boundaries
X_FECHA_MAX = 55
X_DESC_MAX = 390
X_DEP_MAX = 470
X_RET_MAX = 545

MESES = {
    'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12,
}

HEADER_WORDS = {
    'FECHA', 'DESCRIPCION', 'DEPOSITOS', 'RETIROS', 'SALDO',
    'DOCTO', 'REF.', 'NO.',
}

_PAT_SECTION_START = re.compile(r'DETALLE DE LA CUENTA:', re.IGNORECASE)
_PAT_SECTION_END = re.compile(r'SALDO TOTAL\*|TOTAL DE MOVIMIENTOS', re.IGNORECASE)
_PAT_SKIP = re.compile(
    r'CONTINUA EN LA SIGUIENTE PAGINA|PAGINA \d+ DE \d+',
    re.IGNORECASE,
)


def _words_to_text(words) -> str:
    return ' '.join(w['text'] for w in words).strip()


def _is_table_header(row_words) -> bool:
    texts = {w['text'] for w in row_words}
    return bool(texts & HEADER_WORDS)


def _parse_amount(words) -> Optional[float]:
    text = ' '.join(w['text'] for w in words if w['text'].strip() not in ('$', ''))
    text = text.replace(',', '').strip()
    try:
        return float(text)
    except ValueError:
        return None


def _is_valid_date(date_words) -> bool:
    text = _words_to_text(date_words)
    parts = text.split()
    return (
        len(parts) >= 2
        and parts[0].isdigit()
        and 1 <= int(parts[0]) <= 31
        and parts[1].upper() in MESES
    )


def _parse_date(date_text: str, year: Optional[int]):
    parts = date_text.split()
    dia = int(parts[0]) if parts and parts[0].isdigit() else None
    mes_str = parts[1].upper() if len(parts) > 1 else ''
    mes_num = MESES.get(mes_str)
    return dia, mes_num, year


def _split_ref_and_desc(text: str):
    match = re.match(r'^(\d{2,})([A-ZÁÉÍÓÚÑÜ\(\s\-].*|$)', text)
    if match:
        return match.group(1), match.group(2).strip()
    return '', text


def _extract_year(pdf) -> Optional[int]:
    text = pdf.pages[0].extract_text() or ''
    m = re.search(r'PERIODO:.*?(\d{4})\s*$', text, re.MULTILINE | re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_month(pdf) -> Optional[int]:
    """Detect the statement month from the 'PERIODO:' header (last month in range)."""
    text = pdf.pages[0].extract_text() or ''
    m = re.search(r'PERIODO:\s*.*?(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚ]+)', text, re.IGNORECASE)
    if not m:
        m = re.search(r'AL\s+\d{1,2}\s+DE\s+([A-ZÁÉÍÓÚ]+)', text, re.IGNORECASE)
        if m:
            mes_str = m.group(1).upper()[:3]
            return MESES.get(mes_str)
        return None
    mes_str = m.group(2).upper()[:3]
    return MESES.get(mes_str)


@register
class BajioParser(BankStatementParser):
    bank_code = 'bajio'

    def parse(self, pdf_bytes: bytes) -> list:
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError(
                "El paquete Python 'pdfplumber' no está instalado. "
                "Ejecute: pip install pdfplumber"
            ) from exc

        statements_by_account: dict = {}
        stream = io.BytesIO(pdf_bytes)

        with pdfplumber.open(stream) as pdf:
            year = _extract_year(pdf)
            month = _extract_month(pdf)
            current_account = ''
            in_tx_section = False
            current_tx: Optional[dict] = None

            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                rows = defaultdict(list)
                for w in words:
                    rows[round(w['top'])].append(w)

                for top in sorted(rows.keys()):
                    row_words = sorted(rows[top], key=lambda w: w['x0'])
                    all_text = _words_to_text(row_words)

                    if _is_table_header(row_words):
                        continue
                    if _PAT_SKIP.search(all_text):
                        continue
                    if re.search(r'SALDO\s+INICIAL', all_text, re.IGNORECASE):
                        continue

                    if _PAT_SECTION_START.search(all_text):
                        in_tx_section = True
                        current_tx = None
                        m = re.search(r'#(\d+)', all_text)
                        if m:
                            current_account = m.group(1)
                            statements_by_account.setdefault(
                                current_account,
                                ParsedStatement(cuenta=current_account, anio=year, mes=month),
                            )
                        continue

                    if _PAT_SECTION_END.search(all_text):
                        in_tx_section = False
                        current_tx = None
                        continue

                    if not in_tx_section:
                        continue

                    date_words = [w for w in row_words if w['x0'] < X_FECHA_MAX]
                    desc_words = [w for w in row_words if X_FECHA_MAX <= w['x0'] < X_DESC_MAX]
                    dep_words = [w for w in row_words if X_DESC_MAX <= w['x0'] < X_DEP_MAX]
                    ret_words = [w for w in row_words if X_DEP_MAX <= w['x0'] < X_RET_MAX]
                    saldo_words = [w for w in row_words if w['x0'] >= X_RET_MAX]

                    has_date = bool(date_words) and _is_valid_date(date_words)
                    has_amount = bool(dep_words or ret_words)

                    if not has_date and not has_amount:
                        if current_tx and all_text:
                            current_tx['detalles'].append(all_text)
                        continue

                    if has_date:
                        date_text = _words_to_text(date_words)
                        desc_text = _words_to_text(desc_words)
                        dia, mes, anio = _parse_date(date_text, year)
                        ref, desc = _split_ref_and_desc(desc_text)

                        deposito = _parse_amount(dep_words) if dep_words else None
                        retiro = _parse_amount(ret_words) if ret_words else None
                        saldo = _parse_amount(saldo_words) if saldo_words else None

                        current_tx = {
                            'cuenta': current_account,
                            'dia': dia, 'mes': mes, 'anio': anio,
                            'referencia': ref,
                            'descripcion': desc,
                            'detalles': [],
                            'deposito': deposito,
                            'retiro': retiro,
                            'saldo': saldo,
                        }
                        stmt = statements_by_account.setdefault(
                            current_account,
                            ParsedStatement(cuenta=current_account, anio=year, mes=month),
                        )
                        stmt.transacciones.append(current_tx)

                    elif has_amount and current_tx and desc_words:
                        extra = _words_to_text(desc_words)
                        if extra:
                            current_tx['detalles'].append(extra)

        result = []
        for stmt in statements_by_account.values():
            transacciones = []
            for tx in stmt.transacciones:
                detalles = ' | '.join(tx['detalles']) if tx['detalles'] else ''
                desc_completa = tx['descripcion']
                if detalles:
                    desc_completa = f"{desc_completa} | {detalles}" if desc_completa else detalles
                fecha_iso = ''
                if tx['dia'] and tx['mes'] and tx['anio']:
                    fecha_iso = f"{tx['anio']:04d}-{tx['mes']:02d}-{tx['dia']:02d}"
                transacciones.append(ParsedTransaction(
                    cuenta=tx['cuenta'],
                    fecha=fecha_iso or None,
                    descripcion=desc_completa,
                    retiro=tx['retiro'] or 0.0,
                    deposito=tx['deposito'] or 0.0,
                    saldo=tx['saldo'] or 0.0,
                    referencia=tx['referencia'],
                ))
            stmt.transacciones = transacciones
            result.append(stmt)

        _logger.info(
            "Bajio parser: %d account(s), %d total transactions",
            len(result), sum(len(s.transacciones) for s in result),
        )
        return result
