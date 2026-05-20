# models/bank_pdf_parsers/base.py
"""Base interface for bank statement PDF parsers.

Each bank-specific parser subclasses :class:`BankStatementParser` and
implements :meth:`parse`. The wizard selects the appropriate parser
based on ``cuenta.bancaria.banco``.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedTransaction:
    cuenta: str
    fecha: Optional[str]  # ISO 'YYYY-MM-DD'
    descripcion: str
    retiro: float = 0.0
    deposito: float = 0.0
    saldo: float = 0.0
    referencia: str = ''


@dataclass
class ParsedStatement:
    cuenta: str
    anio: Optional[int]
    mes: Optional[int]
    transacciones: list = field(default_factory=list)


class BankStatementParser:
    """Abstract base parser. Subclasses must override :meth:`parse`."""

    bank_code: str = ''

    def parse(self, pdf_bytes: bytes) -> list:
        """Parse PDF bytes and return a list of :class:`ParsedStatement`.

        Multiple statements may be returned when the PDF contains
        transactions for more than one account.
        """
        raise NotImplementedError


_REGISTRY: dict = {}


def register(cls):
    _REGISTRY[cls.bank_code] = cls
    return cls


def get_parser(bank_code: str) -> Optional[BankStatementParser]:
    cls = _REGISTRY.get(bank_code)
    return cls() if cls else None


def supported_banks() -> list:
    return sorted(_REGISTRY.keys())
