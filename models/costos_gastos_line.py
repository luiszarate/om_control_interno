#models/costos_gastos_line.py

from odoo import models, fields, api
from odoo.exceptions import UserError


class CostosGastosLine(models.Model):
    _name = 'costos.gastos.line'
    _description = 'Línea de Costos y Gastos'

    control_interno_id = fields.Many2one('control.interno.mensual', string='Control Interno')
    factura_xml_id = fields.Many2one('factura.xml', string='Factura XML')  # Nueva relación
    orden_compra_id = fields.Many2one('purchase.order', string='Orden de Compra')
    fecha_pago = fields.Date(string='Fecha de Pago')
    tipo_pago = fields.Selection([
        ('caja_chica', 'Caja Chica'),
        ('debito', 'Débito'),
        ('credito', 'Crédito'),
        ('transferencia', 'Transferencia'),
        ('otro', 'Otro'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque'),
    ], string='Tipo de Pago')
    tipo_comprobante = fields.Selection([
        ('factura_nacional', 'Factura Nacional'),
        ('factura_extranjera', 'Factura Extranjera'),
        ('nota_remision', 'Nota de Remisión'),
        ('pedimento', 'Pedimento'),
        ('linea_captura', 'Línea de Captura'),
        ('estado_cuenta', 'Estado de Cuenta'),
        ('recibo_caja', 'Recibo de Caja'),
        ('sin_recibo', 'Sin Recibo'),
    ], string='Tipo de Comprobante')
    folio_fiscal = fields.Char(string='Folio Fiscal')
    no_comprobante = fields.Char(string='No. Comprobante')
    fecha_comprobante = fields.Date(string='Fecha de Comprobante')
    concepto = fields.Char(string='Concepto')
    proveedor_id = fields.Many2one('res.partner', string='Proveedor')
    proveedor_text = fields.Char(string='Proveedor Texto')
    tax_id = fields.Char(string='TAX ID')
    country_id = fields.Many2one('res.country', string='País')
    importe = fields.Float(string='Importe')
    descuento = fields.Float(string='Descuento')
    moneda_id = fields.Many2one('res.currency', string='Moneda')
    tipo_cambio = fields.Float(string='Tipo de Cambio')
    importe_mxn = fields.Float(string='Importe MXN', compute='_compute_importe_mxn')
    iva = fields.Float(string='IVA')
    total = fields.Float(string='Total')
    retencion_iva = fields.Float(string='Retención IVA')
    otras_retenciones = fields.Float(string='Otras Retenciones')
    pedimento_no = fields.Char(string='Pedimento No.')
    iva_pedimento = fields.Float(string='IVA Pedimento')
    otros_impuestos_pedimento = fields.Float(string='Otros Impuestos Pedimento')
    division_subcuentas = fields.Char(string='División en Subcuentas')
    importe_subcuenta = fields.Float(string='Importe Subcuenta')
    descuento_subcuenta = fields.Float(string='Descuento Subcuenta')
    total_subcuenta_sin_iva = fields.Float(string='Total Subcuenta s/IVA')
    descripcion_cuenta = fields.Text(string='Descripción de Cuenta', related='cuenta_id.descripcion', store=True)
    cuenta_id = fields.Many2one('catalogo.cuentas', string='Cuenta')
    comentarios_imago = fields.Text(string='Comentarios Imago Aerospace')
    comentarios_contador = fields.Text(string='Comentarios Contador')

    orden_compra_changed = fields.Boolean(string='Orden de Compra Cambiada', default=False, compute='_compute_orden_compra_changed', store=False)

    @api.depends('orden_compra_id')
    def _compute_orden_compra_changed(self):
        for record in self:
            if record.id:
                original = self.env['costos.gastos.line'].browse(record.id)
                if original.exists() and original.orden_compra_id != record.orden_compra_id:
                    record.orden_compra_changed = True
                else:
                    record.orden_compra_changed = False
            else:
                record.orden_compra_changed = False

    @api.depends('importe', 'tipo_cambio')
    def _compute_importe_mxn(self):
        for record in self:
            tipo_cambio = record.tipo_cambio or 1.0
            moneda = record.moneda_id.name if record.moneda_id else 'MXN'
            if moneda != 'MXN':
                record.importe_mxn = record.importe * tipo_cambio
            else:
                record.importe_mxn = record.importe

    @api.onchange('orden_compra_id')
    def _onchange_orden_compra_id(self):
        if self.orden_compra_id and not self.id:
            # Es un nuevo registro, cargar datos automáticamente
            self._load_data_from_purchase_order()
        # No realizar nada para registros existente
                

    def _load_data_from_purchase_order(self):
        po = self.orden_compra_id
        # Only fill fields that are empty
        #if not self.fecha_pago:
        #    self.fecha_pago = po.date_order
        if not self.proveedor_id:
            self.proveedor_id = po.partner_id
        if not self.tax_id:
            self.tax_id = po.partner_id.vat
        if not self.moneda_id:
            self.moneda_id = po.currency_id
        if not self.importe:
            self.importe = po.amount_untaxed
        if not self.iva:
            self.iva = po.amount_tax
        if not self.total:
            self.total = po.amount_total
        if not self.proveedor_text:
            self.proveedor_text = po.partner_id.name

    def action_load_data_from_purchase_order(self):
        if not self.orden_compra_id:
            raise UserError('Debe seleccionar una Orden de Compra.')
        # Abrir el wizard
        return {
            'name': 'Confirmar Carga de Datos',
            'type': 'ir.actions.act_window',
            'res_model': 'costos.gastos.line.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            },
        }
    
    @api.model
    def create(self, vals):
        res = super(CostosGastosLine, self).create(vals)
        if res.orden_compra_id:
            res.orden_compra_id.control_interno = True
        return res

    def write(self, vals):
        # Store previous purchase orders
        previous_orders = {line.id: line.orden_compra_id for line in self}
        res = super(CostosGastosLine, self).write(vals)
        for line in self:
            prev_po = previous_orders.get(line.id)
            new_po = line.orden_compra_id
            if prev_po != new_po:
                # Update 'control_interno' in previous PO if no other lines reference it
                if prev_po and not self.search([('orden_compra_id', '=', prev_po.id)]):
                    prev_po.control_interno = False
                # Set 'control_interno' in new PO
                if new_po:
                    new_po.control_interno = True
        return res

    def unlink(self):
        purchase_orders = self.mapped('orden_compra_id')
        res = super(CostosGastosLine, self).unlink()
        for po in purchase_orders:
            if not self.search([('orden_compra_id', '=', po.id)]):
                po.control_interno = False
        return res
    
    @api.onchange('factura_xml_id')
    def _onchange_factura_xml_id(self):
        if self.factura_xml_id:
            factura = self.factura_xml_id
            # Fill in fields if they are empty
            if not self.folio_fiscal:
                self.folio_fiscal = factura.uuid
            if not self.fecha_comprobante:
                self.fecha_comprobante = factura.fecha
            if not self.proveedor_id:
                self.proveedor_id = factura.proveedor_id
            if not self.proveedor_text:
                self.proveedor_text = factura.proveedor_text
            if not self.tax_id:
                self.tax_id = factura.rfc
            if not self.country_id:
                self.country_id = factura.pais_id
            if not self.importe:
                self.importe = factura.subtotal
            if not self.descuento:
                self.descuento = factura.descuento
            if not self.moneda_id:
                self.moneda_id = factura.moneda_id
            if not self.tipo_cambio:
                self.tipo_cambio = factura.tipo_cambio
            if not self.iva:
                self.iva = factura.iva
            if not self.total:
                self.total = factura.total
            if not self.no_comprobante:
                self.no_comprobante = factura.folio
            if not self.concepto:
                self.concepto = factura.concepto
            # If 'orden_compra_id' is empty, set it from 'factura.xml'
            if not self.orden_compra_id and factura.ordenes_compra_ids:
                self.orden_compra_id = factura.ordenes_compra_ids[0]
                self._load_data_from_purchase_order()
