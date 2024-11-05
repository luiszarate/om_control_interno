#models/factura_xml_purchase_order_wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError

class FacturaXMLPurchaseOrderWizard(models.TransientModel):
    _name = 'factura.xml.purchase.order.wizard'
    _description = 'Asistente para vincular Órdenes de Compra con Factura XML'

    factura_xml_id = fields.Many2one('factura.xml', string='Factura XML', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Orden de Compra', required=True)
    suggested_purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Órdenes de Compra Sugeridas',
        readonly=True,
    )
    suggested_purchase_order_ids_ordered = fields.Char(string='IDs Ordenados', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super(FacturaXMLPurchaseOrderWizard, self).default_get(fields)
        factura_xml = self.env['factura.xml'].browse(self._context.get('default_factura_xml_id'))
        res['suggested_purchase_order_ids'] = [(6, 0, factura_xml.suggested_purchase_order_ids.ids)]
        res['suggested_purchase_order_ids_ordered'] = ','.join(map(str, factura_xml.suggested_purchase_order_ids.ids))
        return res

    def action_link_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError('Debe seleccionar una Orden de Compra.')
        self.factura_xml_id.ordenes_compra_ids = [(4, self.purchase_order_id.id)]
        return {'type': 'ir.actions.act_window_close'}

    def action_suggest_purchase_orders(self):
        self.ensure_one()
        # Abrir un asistente para mostrar las sugerencias
        return {
            'name': 'Sugerir Órdenes de Compra',
            'type': 'ir.actions.act_window',
            'res_model': 'factura.xml.purchase.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_factura_xml_id': self.id,
            },
        }