# models/estado_cuenta_bancario_import_wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import csv
import io
from datetime import datetime


class EstadoCuentaBancarioImportWizard(models.TransientModel):
    _name = 'estado.cuenta.bancario.import.wizard'
    _description = 'Importar Movimientos de Estado de Cuenta desde CSV'

    csv_file = fields.Binary(string='Archivo CSV', required=True)
    filename = fields.Char(string='Nombre del Archivo')
    estado_cuenta_id = fields.Many2one(
        'estado.cuenta.bancario',
        string='Estado de Cuenta',
        required=True,
    )

    def action_import(self):
        if not self.csv_file:
            raise UserError('Debe seleccionar un archivo CSV.')

        file_content = base64.b64decode(self.csv_file)
        # Try utf-8 first, then latin-1
        try:
            file_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            file_content = file_content.decode('latin-1')

        # Detect delimiter (tab or comma)
        first_line = file_content.split('\n')[0]
        delimiter = '\t' if '\t' in first_line else ','

        csv_reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)

        # Read header row
        header = next(csv_reader, None)
        if not header:
            raise UserError('El archivo CSV está vacío.')

        # Normalize headers for matching
        normalized_headers = [self._normalize_header(h) for h in header]

        # Map columns by name
        col_map = {}
        for idx, h in enumerate(normalized_headers):
            if h in ('fecha',) and 'fecha' not in col_map:
                col_map['fecha'] = idx
            elif h in ('descripcion', 'descripción'):
                col_map['descripcion'] = idx
            elif h in ('retiro',):
                col_map['retiro'] = idx
            elif h in ('deposito', 'depósito'):
                col_map['deposito'] = idx
            elif h in ('saldo',):
                col_map['saldo'] = idx
            elif h in ('observaciones',):
                col_map['observaciones'] = idx

        if 'fecha' not in col_map:
            raise UserError(
                'No se encontró la columna FECHA en el archivo CSV. '
                'Columnas detectadas: %s' % ', '.join(header)
            )

        line_obj = self.env['estado.cuenta.bancario.line']
        lines_created = 0

        for row in csv_reader:
            if not row or all(not cell.strip() for cell in row):
                continue

            fecha = self._parse_fecha(
                row[col_map['fecha']].strip() if col_map.get('fecha') is not None and col_map['fecha'] < len(row) else ''
            )
            descripcion = (
                row[col_map['descripcion']].strip()
                if col_map.get('descripcion') is not None and col_map['descripcion'] < len(row)
                else ''
            )
            retiro = self._parse_float(
                row[col_map['retiro']].strip()
                if col_map.get('retiro') is not None and col_map['retiro'] < len(row)
                else '0'
            )
            deposito = self._parse_float(
                row[col_map['deposito']].strip()
                if col_map.get('deposito') is not None and col_map['deposito'] < len(row)
                else '0'
            )
            saldo = self._parse_float(
                row[col_map['saldo']].strip()
                if col_map.get('saldo') is not None and col_map['saldo'] < len(row)
                else '0'
            )
            observaciones = (
                row[col_map['observaciones']].strip()
                if col_map.get('observaciones') is not None and col_map['observaciones'] < len(row)
                else ''
            )

            line_obj.create({
                'estado_cuenta_id': self.estado_cuenta_id.id,
                'fecha': fecha,
                'descripcion': descripcion,
                'retiro': retiro,
                'deposito': deposito,
                'saldo': saldo,
                'observaciones': observaciones,
            })
            lines_created += 1

        if lines_created == 0:
            raise UserError('No se encontraron movimientos válidos en el archivo CSV.')

        return {'type': 'ir.actions.act_window_close'}

    def _normalize_header(self, header):
        """Normalize header text for matching."""
        h = header.strip().lower()
        # Remove accents
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u',
        }
        for old, new in replacements.items():
            h = h.replace(old, new)
        return h

    def _parse_fecha(self, value):
        """Parse date from various formats."""
        if not value:
            return False
        # Try common date formats
        for fmt in ('%d/%m/%y', '%d/%m/%Y', '%d-%m-%y', '%d-%m-%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return False

    def _parse_float(self, value):
        """Parse float from string, handling currency formats."""
        if not value:
            return 0.0
        # Remove currency symbols, spaces, commas used as thousands separator
        value = value.replace('$', '').replace(' ', '').replace(',', '')
        try:
            return abs(float(value))
        except ValueError:
            return 0.0
