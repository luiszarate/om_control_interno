#models/purchase_order_suggestion.py

from odoo import models, fields

class PurchaseOrderSuggestion(models.TransientModel):
    _name = 'purchase.order.suggestion'
    _description = 'Sugerencia de Orden de Compra'

    wizard_id = fields.Many2one('factura.xml.purchase.order.wizard', string='Asistente')
    purchase_order_id = fields.Many2one('purchase.order', string='Orden de Compra')
    score = fields.Integer(string='Puntaje')

