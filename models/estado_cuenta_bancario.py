# models/estado_cuenta_bancario.py

from odoo import models, fields, api
from odoo.exceptions import UserError


class EstadoCuentaBancario(models.Model):
    _name = 'estado.cuenta.bancario'
    _description = 'Estado de Cuenta Bancario'
    _order = 'mes desc'

    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True,
    )
    numero_cuenta = fields.Char(string='Número de Cuenta', required=True)
    mes = fields.Date(string='Mes', required=True)
    movimiento_ids = fields.One2many(
        'estado.cuenta.bancario.line',
        'estado_cuenta_id',
        string='Movimientos',
    )
    movimiento_count = fields.Integer(
        string='No. Movimientos',
        compute='_compute_movimiento_count',
    )
    conciliados_count = fields.Integer(
        string='Conciliados',
        compute='_compute_conciliacion_counts',
    )
    pendientes_count = fields.Integer(
        string='Pendientes',
        compute='_compute_conciliacion_counts',
    )

    _sql_constraints = [
        ('unique_cuenta_mes', 'unique(numero_cuenta, mes)',
         'Ya existe un estado de cuenta para esta cuenta y mes.'),
    ]

    @api.depends('numero_cuenta', 'mes')
    def _compute_name(self):
        meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
        }
        for rec in self:
            if rec.numero_cuenta and rec.mes:
                mes_nombre = meses.get(rec.mes.month, '')
                rec.name = f"{rec.numero_cuenta} - {mes_nombre} {rec.mes.year}"
            else:
                rec.name = 'Nuevo'

    @api.depends('movimiento_ids')
    def _compute_movimiento_count(self):
        for rec in self:
            rec.movimiento_count = len(rec.movimiento_ids)

    @api.depends('movimiento_ids.costos_gastos_line_ids')
    def _compute_conciliacion_counts(self):
        for rec in self:
            conciliados = sum(1 for m in rec.movimiento_ids if m.conciliado)
            rec.conciliados_count = conciliados
            rec.pendientes_count = len(rec.movimiento_ids) - conciliados

    def action_import_csv(self):
        self.ensure_one()
        return {
            'name': 'Importar Movimientos desde CSV',
            'type': 'ir.actions.act_window',
            'res_model': 'estado.cuenta.bancario.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_estado_cuenta_id': self.id,
            },
        }

    def action_auto_conciliar(self):
        """Auto-match bank movements with control interno lines.

        Only matches when there is exactly one costos.gastos.line with
        the same fecha_pago and matching total (retiro or deposito).
        Skips lines that already have matches or where multiple candidates exist.
        """
        self.ensure_one()
        matched = 0
        skipped = 0

        for mov in self.movimiento_ids:
            if mov.costos_gastos_line_ids:
                continue  # already matched

            monto = mov.retiro if mov.retiro > 0 else mov.deposito
            if not monto or not mov.fecha:
                continue

            # Search for costos.gastos.line with matching date and amount
            # Use a small tolerance for float comparison (0.01)
            domain = [
                ('fecha_pago', '=', mov.fecha),
                ('total', '>=', monto - 0.01),
                ('total', '<=', monto + 0.01),
            ]
            candidates = self.env['costos.gastos.line'].search(domain)

            # Exclude candidates already linked to other bank movements
            candidates = candidates.filtered(
                lambda c: not c.movimiento_bancario_ids
            )

            if len(candidates) == 1:
                mov.costos_gastos_line_ids = [(4, candidates.id)]
                matched += 1
            else:
                skipped += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Conciliación Automática',
                'message': f'Se conciliaron {matched} movimientos. '
                           f'{skipped} movimientos no pudieron conciliarse automáticamente.',
                'type': 'info' if matched > 0 else 'warning',
                'sticky': False,
            },
        }


class EstadoCuentaBancarioLine(models.Model):
    _name = 'estado.cuenta.bancario.line'
    _description = 'Movimiento de Estado de Cuenta Bancario'
    _order = 'fecha, id'

    estado_cuenta_id = fields.Many2one(
        'estado.cuenta.bancario',
        string='Estado de Cuenta',
        required=True,
        ondelete='cascade',
    )
    fecha = fields.Date(string='Fecha')
    descripcion = fields.Text(string='Descripción')
    retiro = fields.Float(string='Retiro', digits=(16, 2))
    deposito = fields.Float(string='Depósito', digits=(16, 2))
    saldo = fields.Float(string='Saldo', digits=(16, 2))
    observaciones = fields.Text(string='Observaciones')
    costos_gastos_line_ids = fields.Many2many(
        'costos.gastos.line',
        'estado_cuenta_costos_gastos_rel',
        'estado_cuenta_line_id',
        'costos_gastos_line_id',
        string='Líneas de Control Interno',
    )
    conciliado = fields.Boolean(
        string='Conciliado',
        compute='_compute_conciliado',
        store=True,
    )
    costos_gastos_count = fields.Integer(
        string='# Líneas CI',
        compute='_compute_conciliado',
        store=True,
    )
    mes_estado_cuenta = fields.Date(
        related='estado_cuenta_id.mes',
        store=True,
    )

    @api.depends('costos_gastos_line_ids')
    def _compute_conciliado(self):
        for rec in self:
            rec.conciliado = bool(rec.costos_gastos_line_ids)
            rec.costos_gastos_count = len(rec.costos_gastos_line_ids)

    def action_open_conciliacion(self):
        """Open the bank movement form to manage conciliation."""
        self.ensure_one()
        return {
            'name': 'Conciliar Movimiento',
            'type': 'ir.actions.act_window',
            'res_model': 'estado.cuenta.bancario.line',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'om_control_interno.view_estado_cuenta_bancario_line_form'
            ).id,
            'target': 'new',
        }

    def action_save_conciliacion(self):
        """Save conciliation changes and close the dialog."""
        return {'type': 'ir.actions.act_window_close'}
