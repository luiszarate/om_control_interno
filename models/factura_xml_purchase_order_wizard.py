#models/factura_xml_purchase_order_wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError

class FacturaXMLPurchaseOrderWizard(models.TransientModel):
    _name = 'factura.xml.purchase.order.wizard'
    _description = 'Asistente para vincular Órdenes de Compra con Factura XML'

    factura_xml_id = fields.Many2one('factura.xml', string='Factura XML', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Orden de Compra', domain="[('id', 'in', suggested_purchase_order_ids)]")

    suggested_purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Órdenes de Compra Sugeridas',
        related='factura_xml_id.suggested_purchase_order_ids',
        readonly=True,
    )

    def action_link_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError('Debe seleccionar una Orden de Compra.')
        # Vincular la Orden de Compra a la factura.xml
        self.factura_xml_id.ordenes_compra_ids = [(4, self.purchase_order_id.id)]

        # Sincronizar las líneas de Control Interno
        self._sync_control_interno_lines()

        return {'type': 'ir.actions.act_window_close'}

    def _sync_control_interno_lines(self):
        factura = self.factura_xml_id
        purchase_order = self.purchase_order_id
        
        # Buscar líneas de control interno relacionadas con esta factura
        control_interno_lines = self.env['costos.gastos.line'].search([
            ('factura_xml_id', '=', factura.id)  # Asumiendo que existe este campo
        ])

        for line in control_interno_lines:
            line.orden_compra_id = purchase_order.id
            line._load_data_from_purchase_order()
