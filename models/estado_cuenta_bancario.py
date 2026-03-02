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
