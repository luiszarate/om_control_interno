# models/estado_cuenta_pdf_import_wizard.py

import base64
import logging
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .bank_pdf_parsers import base as parsers_base

_logger = logging.getLogger(__name__)


class EstadoCuentaPdfImportWizard(models.TransientModel):
    _name = 'estado.cuenta.bancario.pdf.import.wizard'
    _description = 'Importar Movimientos de Estado de Cuenta desde PDF'

    pdf_file = fields.Binary(string='Archivo PDF', required=True)
    filename = fields.Char(string='Nombre del Archivo')
    cuenta_bancaria_id = fields.Many2one(
        'cuenta.bancaria',
        string='Filtrar a Cuenta Bancaria',
        help='Opcional. Si se especifica, sólo se importará la cuenta del PDF '
             'cuyo número coincida. Útil cuando el PDF contiene varias cuentas '
             'y sólo te interesa una.',
    )
    auto_crear_cuenta = fields.Boolean(
        string='Crear cuentas bancarias si no existen',
        default=True,
        help='Si el PDF contiene cuentas que no están en el catálogo, se crean '
             'automáticamente. Aplica a todas las cuentas detectadas en el PDF.',
    )
    estado_cuenta_id = fields.Many2one(
        'estado.cuenta.bancario',
        string='Estado de Cuenta (existente)',
        help='Cuando se invoca desde un estado existente, solo se importa la '
             'cuenta del PDF que coincida con éste.',
    )
    forzar_reemplazo = fields.Boolean(
        string='Reemplazar movimientos existentes',
        default=False,
        help='Si alguna combinación cuenta/mes ya existe, borra los movimientos '
             'previos antes de importar.',
    )
    estados_existentes_ids = fields.Many2many(
        'estado.cuenta.bancario',
        string='Estados de Cuenta Existentes',
        readonly=True,
    )
    mensaje_aviso = fields.Text(string='Aviso', readonly=True)
    bank_code = fields.Selection(
        selection=[
            ('bajio', 'Banco del Bajío'),
        ],
        string='Banco',
        default='bajio',
        required=True,
        help='Banco emisor del PDF. Determina el parser usado.',
    )

    def _get_parser(self, bank_code: str):
        parser = parsers_base.get_parser(bank_code)
        if not parser:
            raise UserError(_(
                "No hay un parser implementado para el banco '%s'. "
                "Bancos soportados actualmente: %s"
            ) % (bank_code, ', '.join(parsers_base.supported_banks()) or 'ninguno'))
        return parser

    def _bank_code(self):
        """Resolve the bank code to use for parsing."""
        if self.cuenta_bancaria_id:
            return self.cuenta_bancaria_id.banco
        if self.estado_cuenta_id and self.estado_cuenta_id.cuenta_bancaria_id:
            return self.estado_cuenta_id.cuenta_bancaria_id.banco
        return self.bank_code or 'bajio'

    def _filter_statements(self, statements):
        """When invoked in 'filtered mode', restrict to the relevant account."""
        filtro_numero = None
        if self.estado_cuenta_id and self.estado_cuenta_id.cuenta_bancaria_id:
            filtro_numero = self.estado_cuenta_id.cuenta_bancaria_id.numero_cuenta
        elif self.cuenta_bancaria_id:
            filtro_numero = self.cuenta_bancaria_id.numero_cuenta

        if not filtro_numero:
            return statements

        matched = [s for s in statements if (s.cuenta or '').strip() == filtro_numero.strip()]
        if not matched:
            cuentas_detectadas = ', '.join(s.cuenta or '?' for s in statements) or 'ninguna'
            raise UserError(_(
                'El PDF no contiene la cuenta %(esperada)s. '
                'Cuentas detectadas: %(detectadas)s.'
            ) % {'esperada': filtro_numero, 'detectadas': cuentas_detectadas})
        return matched

    def action_import(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_('Debe seleccionar un archivo PDF.'))

        pdf_bytes = base64.b64decode(self.pdf_file)
        bank_code = self._bank_code()
        parser = self._get_parser(bank_code)

        try:
            statements = parser.parse(pdf_bytes)
        except RuntimeError as exc:
            raise UserError(str(exc))
        except Exception as exc:
            _logger.exception("Error parsing bank statement PDF")
            raise UserError(_('Error al procesar el PDF: %s') % exc)

        if not statements:
            raise UserError(_('No se detectaron movimientos en el PDF.'))

        statements = self._filter_statements(statements)
        _logger.info(
            "PDF import: %d statement(s) to process (forzar_reemplazo=%s)",
            len(statements), self.forzar_reemplazo,
        )

        cuenta_obj = self.env['cuenta.bancaria']
        estado_obj = self.env['estado.cuenta.bancario']

        # Resolve cuenta_bancaria + mes for each statement up front.
        resolved = []
        for stmt in statements:
            cuenta = self._resolve_cuenta_bancaria(stmt, cuenta_obj, bank_code)
            mes_date = self._resolve_mes(stmt)
            existente = estado_obj.search([
                ('cuenta_bancaria_id', '=', cuenta.id),
                ('mes', '=', mes_date),
            ], limit=1)
            resolved.append({
                'stmt': stmt,
                'cuenta': cuenta,
                'mes': mes_date,
                'existente': existente,
            })

        # Detect conflicts. estado_cuenta_id mode reuses the existing record
        # by design, so it is not a conflict.
        conflictos = [
            r for r in resolved
            if r['existente'] and not self.estado_cuenta_id
        ]

        if conflictos and not self.forzar_reemplazo:
            lineas = []
            for r in conflictos:
                lineas.append(_(' • %(cuenta)s — %(mes)s (estado existente id=%(id)s)') % {
                    'cuenta': r['cuenta'].display_name,
                    'mes': r['mes'].strftime('%Y-%m'),
                    'id': r['existente'].id,
                })
            mensaje = _(
                'Las siguientes combinaciones cuenta/mes ya existen en la base '
                'de datos:\n\n%(lista)s\n\n'
                'Use "Borrar y Reimportar" para reemplazar los movimientos '
                'previos de esas combinaciones (las cuentas sin conflicto se '
                'crearán normalmente), o "Abrir Existentes" para revisarlas.'
            ) % {'lista': '\n'.join(lineas)}
            self.write({
                'estados_existentes_ids': [(6, 0, [r['existente'].id for r in conflictos])],
                'mensaje_aviso': mensaje,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context,
            }

        # Commit imports.
        estados_procesados = self._commit_imports(resolved)

        if not estados_procesados:
            raise UserError(_('No se importó ningún movimiento.'))

        return self._open_results(estados_procesados)

    def _commit_imports(self, resolved):
        estado_obj = self.env['estado.cuenta.bancario']
        line_obj = self.env['estado.cuenta.bancario.line']
        estados = []

        for r in resolved:
            stmt = r['stmt']
            cuenta = r['cuenta']
            mes_date = r['mes']
            existente = r['existente']

            if self.estado_cuenta_id:
                estado = self.estado_cuenta_id
            elif existente:
                estado = existente
                if self.forzar_reemplazo:
                    estado.movimiento_ids.unlink()
            else:
                estado = estado_obj.create({
                    'cuenta_bancaria_id': cuenta.id,
                    'mes': mes_date,
                })

            for tx in stmt.transacciones:
                line_obj.create({
                    'estado_cuenta_id': estado.id,
                    'fecha': tx.fecha or False,
                    'descripcion': tx.descripcion,
                    'retiro': tx.retiro or 0.0,
                    'deposito': tx.deposito or 0.0,
                    'saldo': tx.saldo or 0.0,
                })
            estados.append(estado)
            _logger.info(
                "Imported %d line(s) into estado.cuenta.bancario id=%s (%s / %s)",
                len(stmt.transacciones), estado.id, cuenta.display_name, mes_date,
            )
        return estados

    def _open_results(self, estados):
        if len(estados) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'estado.cuenta.bancario',
                'res_id': estados[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estados de Cuenta Importados'),
            'res_model': 'estado.cuenta.bancario',
            'domain': [('id', 'in', [e.id for e in estados])],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_abrir_existente(self):
        self.ensure_one()
        if not self.estados_existentes_ids:
            raise UserError(_('No hay estados de cuenta existentes para abrir.'))
        if len(self.estados_existentes_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'estado.cuenta.bancario',
                'res_id': self.estados_existentes_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estados de Cuenta Existentes'),
            'res_model': 'estado.cuenta.bancario',
            'domain': [('id', 'in', self.estados_existentes_ids.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_borrar_y_reimportar(self):
        self.ensure_one()
        self.forzar_reemplazo = True
        return self.action_import()

    def _resolve_cuenta_bancaria(self, stmt, cuenta_obj, bank_code):
        if not stmt.cuenta:
            # Last resort: when the wizard was given a manual cuenta_bancaria_id
            # and the parser did not detect a number, use the manual value.
            if self.cuenta_bancaria_id:
                return self.cuenta_bancaria_id
            raise UserError(_(
                'El PDF no expone un número de cuenta detectable. '
                'Seleccione manualmente la cuenta bancaria en el wizard.'
            ))
        cuenta = cuenta_obj.search([('numero_cuenta', '=', stmt.cuenta)], limit=1)
        if cuenta:
            return cuenta
        if not self.auto_crear_cuenta:
            raise UserError(_(
                'La cuenta %s no existe en el catálogo. Cree la cuenta '
                'bancaria primero o marque "Crear cuentas bancarias si no existen".'
            ) % stmt.cuenta)
        return cuenta_obj.create({
            'name': _('Cuenta %s') % stmt.cuenta,
            'numero_cuenta': stmt.cuenta,
            'banco': bank_code,
        })

    def _resolve_mes(self, stmt):
        if self.estado_cuenta_id and self.estado_cuenta_id.mes:
            return self.estado_cuenta_id.mes
        if stmt.anio and stmt.mes:
            return date(stmt.anio, stmt.mes, 1)
        for tx in stmt.transacciones:
            if tx.fecha:
                y, m, _d = tx.fecha.split('-')
                return date(int(y), int(m), 1)
        raise UserError(_(
            'No se pudo determinar el mes del estado de cuenta a partir del PDF.'
        ))
