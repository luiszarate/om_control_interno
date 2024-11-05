#models/costos_gastos_line.py

from odoo import models, fields, api

class CostosGastosLine(models.Model):
    _name = 'costos.gastos.line'
    _description = 'Línea de Costos y Gastos'

    control_interno_id = fields.Many2one('control.interno.mensual', string='Control Interno')
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

    @api.depends('importe', 'tipo_cambio')
    def _compute_importe_mxn(self):
        for record in self:
            tipo_cambio = record.tipo_cambio or 1.0
            moneda = record.moneda_id.name if record.moneda_id else 'MXN'
            if moneda != 'MXN':
                record.importe_mxn = record.importe * tipo_cambio
            else:
                record.importe_mxn = record.importe
