# models/costos_gastos_line_wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError

class CostosGastosLineWizard(models.TransientModel):
    _name = 'costos.gastos.line.wizard'
    _description = 'Asistente para Confirmar Carga de Datos de Orden de Compra'

    line_id = fields.Many2one('costos.gastos.line', string='Línea de Costos y Gastos')
    confirm = fields.Boolean(string='Confirmar', default=False)

    def action_confirm(self):
        if self.line_id and self.confirm:
            self.line_id._load_data_from_purchase_order()
        return {'type': 'ir.actions.act_window_close'}
