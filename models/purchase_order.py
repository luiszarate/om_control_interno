# models/purchase_order.py

from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    control_interno = fields.Boolean(string='Control Interno', default=False)
