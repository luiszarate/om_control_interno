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
        string='Cuenta Bancaria',
        help='Si se deja vacío, el parser intentará detectarla del PDF.',
    )
    auto_crear_cuenta = fields.Boolean(
        string='Crear cuenta bancaria si no existe',
        default=True,
    )
    estado_cuenta_id = fields.Many2one(
        'estado.cuenta.bancario',
        string='Estado de Cuenta (existente)',
        help='Si se especifica, los movimientos se añaden a este registro.',
    )
    forzar_reemplazo = fields.Boolean(
        string='Reemplazar movimientos existentes',
        default=False,
        help='Si la combinación cuenta/mes ya existe, borra movimientos previos antes de importar.',
    )
    estado_existente_id = fields.Many2one(
        'estado.cuenta.bancario',
        string='Estado de Cuenta Existente',
        readonly=True,
    )
    mensaje_aviso = fields.Text(string='Aviso', readonly=True)

    def _get_parser(self, bank_code: str):
        parser = parsers_base.get_parser(bank_code)
        if not parser:
            raise UserError(_(
                "No hay un parser implementado para el banco '%s'. "
                "Bancos soportados actualmente: %s"
            ) % (bank_code, ', '.join(parsers_base.supported_banks()) or 'ninguno'))
        return parser

    def action_import(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_('Debe seleccionar un archivo PDF.'))

        pdf_bytes = base64.b64decode(self.pdf_file)

        bank_code = self.cuenta_bancaria_id.banco if self.cuenta_bancaria_id else 'bajio'
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

        cuenta_obj = self.env['cuenta.bancaria']
        estado_obj = self.env['estado.cuenta.bancario']
        line_obj = self.env['estado.cuenta.bancario.line']

        estados_creados = []
        total_lineas = 0

        for stmt in statements:
            cuenta = self._resolve_cuenta_bancaria(stmt, cuenta_obj, bank_code)
            mes_date = self._resolve_mes(stmt)

            existente = estado_obj.search([
                ('cuenta_bancaria_id', '=', cuenta.id),
                ('mes', '=', mes_date),
            ], limit=1)

            if existente and not self.forzar_reemplazo and not self.estado_cuenta_id:
                self.write({
                    'estado_existente_id': existente.id,
                    'mensaje_aviso': _(
                        'Ya existe un estado de cuenta para %(cuenta)s en %(mes)s. '
                        'Marque "Reemplazar movimientos existentes" para borrar los '
                        'movimientos previos y reimportar, o abra el estado existente.'
                    ) % {'cuenta': cuenta.display_name, 'mes': mes_date.strftime('%Y-%m')},
                })
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                    'context': self.env.context,
                }

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
                total_lineas += 1
            estados_creados.append(estado)

        if not estados_creados:
            raise UserError(_('No se importó ningún movimiento.'))

        if len(estados_creados) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'estado.cuenta.bancario',
                'res_id': estados_creados[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estados de Cuenta Importados'),
            'res_model': 'estado.cuenta.bancario',
            'domain': [('id', 'in', [e.id for e in estados_creados])],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_abrir_existente(self):
        self.ensure_one()
        if not self.estado_existente_id:
            raise UserError(_('No hay un estado de cuenta existente al cual abrir.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estado.cuenta.bancario',
            'res_id': self.estado_existente_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_borrar_y_reimportar(self):
        self.ensure_one()
        self.forzar_reemplazo = True
        return self.action_import()

    def _resolve_cuenta_bancaria(self, stmt, cuenta_obj, bank_code):
        if self.cuenta_bancaria_id:
            return self.cuenta_bancaria_id
        if not stmt.cuenta:
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
                'bancaria primero o marque "Crear cuenta bancaria si no existe".'
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
        # fallback: derive from first transaction
        for tx in stmt.transacciones:
            if tx.fecha:
                y, m, _d = tx.fecha.split('-')
                return date(int(y), int(m), 1)
        raise UserError(_(
            'No se pudo determinar el mes del estado de cuenta a partir del PDF.'
        ))
