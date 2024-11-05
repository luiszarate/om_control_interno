#models/control.interno.mensual.py

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ControlInternoMensual(models.Model):
    _name = 'control.interno.mensual'
    _description = 'Control Interno Mensual'

    name = fields.Char(string='Nombre', required=True)
    mes = fields.Date(string='Mes', required=True)
    costos_gastos_ids = fields.One2many('costos.gastos.line', 'control_interno_id', string='Costos y Gastos')
    #ingresos_ids = fields.One2many('ingresos.line', 'control_interno_id', string='Ingresos')

    def cargar_datos_desde_xml(self):
        factura_xml_records = self.env['factura.xml'].search([
            ('fecha', '>=', self.mes.replace(day=1)),
            ('fecha', '<', (self.mes + relativedelta(months=1)).replace(day=1))
        ])
        if not factura_xml_records:
            raise UserError('No hay facturas cargadas para este mes.')
        for factura in factura_xml_records:
            self.env['costos.gastos.line'].create({
                'control_interno_id': self.id,
                'fecha_comprobante': factura.fecha,
                'proveedor_id': factura.proveedor_id.id,
                'tax_id': factura.rfc,
                'country_id': factura.pais_id.id,
                'importe': factura.subtotal,
                'descuento': factura.descuento,
                'moneda_id': factura.moneda_id.id,
                'tipo_cambio': factura.tipo_cambio,
                'iva': factura.iva,
                'total': factura.total,
                'folio_fiscal': factura.uuid,
                'no_comprobante': factura.folio,
                'concepto': factura.concepto,
            })
