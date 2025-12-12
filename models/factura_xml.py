#models/factura_xml.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import difflib
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

import base64
import zipfile
import io
import xml.etree.ElementTree as ET


FORMA_PAGO_TO_TIPO_PAGO = {
    '1': 'caja_chica',
    '01': 'caja_chica',
    '2': 'cheque',
    '02': 'cheque',
    '3': 'transferencia',
    '03': 'transferencia',
    '4': 'credito',
    '04': 'credito',
    '28': 'debito',
    '028': 'debito',
}


def map_forma_pago_to_tipo_pago(forma_pago):
    forma_pago = (forma_pago or '').strip()
    tipo_pago = FORMA_PAGO_TO_TIPO_PAGO.get(forma_pago)
    if not tipo_pago and forma_pago.isdigit():
        tipo_pago = FORMA_PAGO_TO_TIPO_PAGO.get(forma_pago.zfill(2))
    return tipo_pago


class FacturaXML(models.Model):
    _name = 'factura.xml'
    _description = 'Factura XML'

    filename = fields.Char(string='Nombre de Archivo')
    uuid = fields.Char(string='UUID')
    folio = fields.Char(string='Folio')
    fecha = fields.Date(string='Fecha')
    proveedor_text = fields.Char(string='Proveedor')
    proveedor_id = fields.Many2one('res.partner', string='Proveedor Odoo')
    rfc = fields.Char(string='RFC')
    pais_id = fields.Many2one('res.country', string='País')
    subtotal = fields.Float(string='Subtotal')
    descuento = fields.Float(string='Descuento')
    moneda_id = fields.Many2one('res.currency', string='Moneda')
    tipo_cambio = fields.Float(string='Tipo de Cambio')
    iva = fields.Float(string='IVA')
    total = fields.Float(string='Total')
    concepto = fields.Char(string='Concepto')
    forma_pago = fields.Char(string='Forma de Pago')
    ordenes_compra_ids = fields.Many2many('purchase.order', string='Órdenes de Compra')
    fecha_text = fields.Char(string='Fecha (texto)', compute='_compute_fecha_text', store=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True)

    _sql_constraints = [
        ('uuid_unique', 'unique(uuid)', 'Ya existe una factura con este UUID.'),
    ]

    suggested_purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Órdenes de Compra Sugeridas',
        compute='_compute_suggested_purchase_orders',
        store=False,
    )

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

    def get_tipo_pago_control_interno(self):
        self.ensure_one()
        return map_forma_pago_to_tipo_pago(self.forma_pago)
    

    def _get_suggestions_with_scores(self):
        suggestions = []
        if not self.fecha:
            return suggestions

        # Obtener la fecha de la factura
        invoice_date = self.fecha

        # Calcular el primer día del mes anterior
        start_date = (invoice_date.replace(day=1) - timedelta(days=1)).replace(day=1)

        # Calcular el último día del mes posterior
        next_month = invoice_date.replace(day=28) + timedelta(days=4)
        end_date = (next_month + timedelta(days=31)).replace(day=1) - timedelta(days=1)

        # Buscar órdenes de compra dentro del rango de fechas
        domain = [
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
        ]
        purchase_orders = self.env['purchase.order'].search(domain)

        for po in purchase_orders:
            score = 0
            # Coincidencia por RFC
            if self.rfc and po.partner_id.vat:
                if self.rfc.strip() == po.partner_id.vat.strip():
                    score += 3
            # Coincidencia por nombre de proveedor
            else:
                ratio = difflib.SequenceMatcher(
                    None,
                    (self.proveedor_id.name or '').lower(),
                    (po.partner_id.name or '').lower()
                ).ratio()
                if ratio > 0.6:
                    score += 2
            # Coincidencia por monto
            invoice_total = self.total or 0.0
            po_total = po.amount_total or 0.0
            if invoice_total > 0 and abs(invoice_total - po_total) / invoice_total < 0.1:
                score += 2
            # Coincidencia por fecha (dentro de 7 días)
            if self.fecha and po.date_order:
                date_diff = abs((self.fecha - po.date_order.date()).days)
                if date_diff <= 7:
                    score += 1
                # Coincidencia en el mismo mes y año
                if self.fecha.month == po.date_order.month and self.fecha.year == po.date_order.year:
                    score += 2
            if score > 0:
                suggestions.append({'po': po, 'score': score})
        # Ordenar las sugerencias por puntaje
        suggestions = sorted(suggestions, key=lambda x: x['score'], reverse=True)
        return suggestions

    def _compute_suggested_purchase_orders(self):
        for record in self:
            suggestions = self.env['purchase.order']
            if not record.fecha:
                # Si no hay fecha en la factura, no podemos limitar por fecha
                continue

            # Obtener la fecha de la factura
            invoice_date = record.fecha

            # Calcular el primer día del mes anterior
            start_date = (invoice_date.replace(day=1) - timedelta(days=1)).replace(day=1)

            # Calcular el último día del mes posterior
            next_month = invoice_date.replace(day=28) + timedelta(days=4)  # asegura estar en el siguiente mes
            end_date = (next_month + timedelta(days=31)).replace(day=1) - timedelta(days=1)


            # Buscar órdenes de compra dentro del rango de fechas
            domain = [
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
            ]
            purchase_orders = self.env['purchase.order'].search(domain)

            for po in purchase_orders:
                score = 0
                # Coincidencia por RFC
                if record.rfc and po.partner_id.vat:
                    if record.rfc.strip() == po.partner_id.vat.strip():
                        score += 3
                # Coincidencia por nombre de proveedor
                else:
                    ratio = difflib.SequenceMatcher(
                        None,
                        (record.proveedor_id.name or '').lower(),
                        (po.partner_id.name or '').lower()
                    ).ratio()
                    if ratio > 0.6:
                        score += 2
                # Coincidencia por monto
                invoice_total = record.total or 0.0
                po_total = po.amount_total or 0.0
                if invoice_total > 0 and abs(invoice_total - po_total) / invoice_total < 0.1:  # 10% de tolerancia
                    score += 2
                # Coincidencia por fecha (dentro de 7 días)
                if record.fecha and po.date_order:
                    date_diff = abs((record.fecha - po.date_order.date()).days)
                    if date_diff <= 7:
                        score += 1
                if score >= 4:  # Umbral para considerar una sugerencia
                    suggestions |= po
            record.suggested_purchase_order_ids = suggestions

    def write(self, vals):
        res = super(FacturaXML, self).write(vals)
        if 'ordenes_compra_ids' in vals:
            for factura in self:
                # Get the first related purchase order, if any
                purchase_order = factura.ordenes_compra_ids[:1]
                # Find related costos.gastos.line records
                control_interno_lines = self.env['costos.gastos.line'].search([
                    ('factura_xml_id', '=', factura.id)
                ])
                for line in control_interno_lines:
                    line.orden_compra_id = purchase_order.id if purchase_order else False
        return res
    
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.uuid or ''} - {record.proveedor_text or ''} - {record.folio or ''} - {record.fecha_text or ''}"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = args + ['|', '|', '|', '|',
                         ('uuid', operator, name),
                         ('proveedor_text', operator, name),
                         ('folio', operator, name),
                         ('fecha_text', operator, name),
                         ('proveedor_id.name', operator, name)]
        records = self.search(domain, limit=limit)
        return records.name_get()
    
    @api.depends('fecha')
    def _compute_fecha_text(self):
        for record in self:
            record.fecha_text = record.fecha.strftime('%Y-%m-%d') if record.fecha else ''