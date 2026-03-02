from odoo import models, fields, api


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
        self._sync_to_movimiento()
        return {'type': 'ir.actions.act_window_close'}
