from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ConciliacionManualWizard(models.TransientModel):
    _name = 'conciliacion.manual.wizard'
    _description = 'Wizard de Conciliación Manual'

    movimiento_id = fields.Many2one(
        'estado.cuenta.bancario.line',
        string='Movimiento Bancario',
        required=True,
        readonly=True,
    )
    costos_gastos_line_ids = fields.Many2many(
        'costos.gastos.line',
        'conciliacion_wizard_costos_gastos_rel',
        'wizard_id',
        'costos_gastos_line_id',
        string='Líneas de Control Interno',
    )

    # Display fields (from movimiento)
    estado_cuenta_id = fields.Many2one(
        related='movimiento_id.estado_cuenta_id', readonly=True,
    )
    fecha = fields.Date(related='movimiento_id.fecha', readonly=True)
    descripcion = fields.Text(
        related='movimiento_id.descripcion', readonly=True,
    )
    retiro = fields.Float(related='movimiento_id.retiro', readonly=True)
    deposito = fields.Float(related='movimiento_id.deposito', readonly=True)
    saldo = fields.Float(related='movimiento_id.saldo', readonly=True)
    conciliado = fields.Boolean(compute='_compute_conciliado')

    # Filter fields
    filtro_fecha_inicio = fields.Date(string='Desde')
    filtro_fecha_fin = fields.Date(string='Hasta')
    filtro_monto_min = fields.Float(string='Monto Mín', digits=(16, 2))
    filtro_monto_max = fields.Float(string='Monto Máx', digits=(16, 2))

    @api.depends('costos_gastos_line_ids')
    def _compute_conciliado(self):
        for rec in self:
            rec.conciliado = bool(rec.costos_gastos_line_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        movimiento_id = self.env.context.get('default_movimiento_id')
        if movimiento_id:
            mov = self.env['estado.cuenta.bancario.line'].browse(movimiento_id)
            res['costos_gastos_line_ids'] = [
                (6, 0, mov.costos_gastos_line_ids.ids)
            ]

            # Month filter based on bank statement month
            if mov.mes_estado_cuenta:
                mes = mov.mes_estado_cuenta
                res['filtro_fecha_inicio'] = mes.replace(day=1)
                if mes.month == 12:
                    next_month = mes.replace(
                        year=mes.year + 1, month=1, day=1,
                    )
                else:
                    next_month = mes.replace(month=mes.month + 1, day=1)
                res['filtro_fecha_fin'] = next_month - timedelta(days=1)
            else:
                res['filtro_fecha_inicio'] = fields.Date.from_string(
                    '2000-01-01'
                )
                res['filtro_fecha_fin'] = fields.Date.from_string(
                    '2099-12-31'
                )

            # Amount filter (±10 pesos)
            monto = mov.retiro if mov.retiro > 0 else mov.deposito
            if monto:
                res['filtro_monto_min'] = max(0, monto - 10.0)
                res['filtro_monto_max'] = monto + 10.0
            else:
                res['filtro_monto_min'] = 0
                res['filtro_monto_max'] = 99999999.0
        return res

    @api.model
    def create(self, vals):
        """Override create to immediately propagate M2M to bank movement."""
        record = super().create(vals)
        record._sync_to_movimiento()
        return record

    def write(self, vals):
        """Override write to immediately propagate M2M to bank movement."""
        result = super().write(vals)
        if 'costos_gastos_line_ids' in vals:
            self._sync_to_movimiento()
        return result

    def _sync_to_movimiento(self):
        """Write the wizard M2M values to the real bank movement."""
        for rec in self:
            if rec.movimiento_id:
                rec.movimiento_id.sudo().write({
                    'costos_gastos_line_ids': [
                        (6, 0, rec.costos_gastos_line_ids.ids)
                    ],
                })

    def action_confirmar(self):
        """Ensure save and close the dialog."""
        self.ensure_one()
        # Belt-and-suspenders: sync one more time in case create/write
        # was called without costos_gastos_line_ids in vals.
        self._sync_to_movimiento()
        return {'type': 'ir.actions.act_window_close'}

    def action_limpiar_filtros(self):
        """Reset filters to show all lines."""
        self.write({
            'filtro_fecha_inicio': fields.Date.from_string('2000-01-01'),
            'filtro_fecha_fin': fields.Date.from_string('2099-12-31'),
            'filtro_monto_min': 0,
            'filtro_monto_max': 99999999.0,
        })
        return {
            'name': 'Conciliar Movimiento',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
