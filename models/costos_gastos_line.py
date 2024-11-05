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
        self.fecha_pago = po.date_order
        self.proveedor_id = po.partner_id
        self.tax_id = po.partner_id.vat
        self.moneda_id = po.currency_id
        self.importe = po.amount_untaxed
        self.iva = po.amount_tax
        self.total = po.amount_total
        # Asigna 'tipo_pago' según tu lógica o déjalo para que el usuario lo complete
        # self.tipo_pago = ...

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