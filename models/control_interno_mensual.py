#models/control.interno.mensual.py

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import csv
import base64
from io import StringIO


class ControlInternoMensual(models.Model):
    _name = 'control.interno.mensual'
    _description = 'Control Interno Mensual'

    name = fields.Char(string='Nombre', required=True)
    mes = fields.Date(string='Mes', required=True)
    costos_gastos_ids = fields.One2many('costos.gastos.line', 'control_interno_id', string='Costos y Gastos')
    mes_fin = fields.Date(string='Fin del Mes', compute='_compute_mes_fin')
    #ingresos_ids = fields.One2many('ingresos.line', 'control_interno_id', string='Ingresos')

    def cargar_datos_desde_xml(self):
        factura_xml_records = self.env['factura.xml'].search([
            ('fecha', '>=', self.mes.replace(day=1)),
            ('fecha', '<', (self.mes + relativedelta(months=1)).replace(day=1))
        ])
        if not factura_xml_records:
            raise UserError('No hay facturas cargadas para este mes.')
        for factura in factura_xml_records:
            # Check if a costos.gastos.line already exists for this factura.xml
            existing_line = self.env['costos.gastos.line'].search([
                ('control_interno_id', '=', self.id),
                ('factura_xml_id', '=', factura.id)
            ], limit=1)
            if existing_line:
                # Skip creating a duplicate line
                continue
            self.env['costos.gastos.line'].create({
                'control_interno_id': self.id,
                'factura_xml_id': factura.id,
                'fecha_comprobante': factura.fecha,
                'proveedor_id': factura.proveedor_id.id,
                'proveedor_text': factura.proveedor_text,
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

    def action_export_csv(self):
        self.ensure_one()
        # Prepare CSV data
        output = StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            'Orden de Compra',
            'Fecha de Pago',
            'Tipo de Pago',
            'Tipo de Comprobante',
            'Folio Fiscal',
            'No. Comprobante',
            'Fecha de Comprobante',
            'Concepto',
            'Proveedor',
            'Tax ID',
            'País',
            'Importe',
            'Descuento',
            'Moneda',
            'Tipo de Cambio',
            'Importe MXN',
            'IVA',
            'Total',
            'Retención IVA',
            'Otras Retenciones',
            'Pedimento No.',
            'IVA Pedimento',
            'Otros Impuestos Pedimento',
            'División en Subcuentas',
            'Importe Subcuenta',
            'Descuento Subcuenta',
            'Total Subcuenta s/IVA',
            'Descripción de Cuenta',
            'Cuenta',
            'Comentarios Imago',
            'Comentarios Contador',
        ])

        # Data rows
        for line in self.costos_gastos_ids:
            # Handle folio_fiscal as both Many2one and Char
            if isinstance(line.folio_fiscal, models.BaseModel):
                folio_fiscal_uuid = line.folio_fiscal.uuid or ''
            else:
                folio_fiscal_uuid = line.folio_fiscal or ''
            writer.writerow([
                line.orden_compra_id.name or '',
                line.fecha_pago or '',
                line.tipo_pago or '',
                line.tipo_comprobante or '',
                folio_fiscal_uuid,
                line.no_comprobante or '',
                line.fecha_comprobante or '',
                line.concepto or '',
                line.proveedor_text or line.proveedor_id.name or '',
                line.tax_id or '',
                line.country_id.name or '',
                line.importe or 0.0,
                line.descuento or 0.0,
                line.moneda_id.name or '',
                line.tipo_cambio or 0.0,
                line.importe_mxn or 0.0,
                line.iva or 0.0,
                line.total or 0.0,
                line.retencion_iva or 0.0,
                line.otras_retenciones or 0.0,
                line.pedimento_no or '',
                line.iva_pedimento or 0.0,
                line.otros_impuestos_pedimento or 0.0,
                line.division_subcuentas or '',
                line.importe_subcuenta or 0.0,
                line.descuento_subcuenta or 0.0,
                line.total_subcuenta_sin_iva or 0.0,
                line.descripcion_cuenta or '',
                line.cuenta_num or '',
                line.comentarios_imago or '',
                line.comentarios_contador or '',
            ])

        # Get CSV content
        csv_data = output.getvalue()
        output.close()

        # Encode to base64
        csv_data_encoded = base64.b64encode(csv_data.encode('utf-8'))

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'Control_Interno_{self.name}.csv',
            'type': 'binary',
            'datas': csv_data_encoded,
            'res_model': 'control.interno.mensual',
            'res_id': self.id,
            'mimetype': 'text/csv',
        })

        # Return action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    @api.depends('mes')
    def _compute_mes_fin(self):
        for record in self:
            if record.mes:
                record.mes_fin = (record.mes + relativedelta(months=1)).replace(day=1)
            else:
                record.mes_fin = False