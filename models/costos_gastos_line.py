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
    importe_mxn = fields.Float(string='Importe MXN')
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
    descripcion_cuenta = fields.Text(string='Descripción de Cuenta', store=True)
    cuenta_num = fields.Text(string='Numero de Cuenta', store=True)
    cuenta_id = fields.Many2one('catalogo.cuentas', string='Cuenta')

    # Campos de sugerencias de cuentas
    suggested_cuenta_ids = fields.Many2many(
        'catalogo.cuentas',
        'costos_gastos_suggested_cuenta_rel',
        'costos_gastos_line_id',
        'catalogo_cuenta_id',
        string='Cuentas Sugeridas',
        compute='_compute_suggested_cuentas',
        store=False
    )
    suggested_cuenta_selection = fields.Many2one(
        'catalogo.cuentas',
        string='💡 Sugerencia',
        compute='_compute_suggested_cuenta_selection',
        inverse='_inverse_suggested_cuenta_selection',
        store=False,
        help='Cuenta sugerida basada en histórico. Selecciona aquí para aplicarla rápidamente.'
    )
    suggestion_info = fields.Html(
        string='Información de Sugerencias',
        compute='_compute_suggested_cuentas',
        store=False
    )

    comentarios_imago = fields.Text(string='Comentarios Imago Aerospace')
    comentarios_contador = fields.Text(string='Comentarios Contador')

    mes = fields.Date(related='control_interno_id.mes', store=True)
    mes_fin = fields.Date(related='control_interno_id.mes_fin', store=True)

    """@api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        control_id = defaults.get('control_interno_id') or self.env.context.get('default_control_interno_id')
        control = self.env['control.interno.mensual']
        if control_id:
            control = control.browse(control_id)
        if control and control.exists() and control.mes:
            first_day = control.mes.replace(day=1)
            if 'fecha_pago' in fields_list and not defaults.get('fecha_pago'):
                defaults['fecha_pago'] = first_day
            if 'fecha_comprobante' in fields_list and not defaults.get('fecha_comprobante'):
                defaults['fecha_comprobante'] = first_day
        return defaults"""

    @api.onchange('tipo_pago', 'fecha_comprobante')
    def _onchange_tipo_pago(self):
        """Set payment date from voucher date when using petty cash."""
        if (
            self.tipo_pago == 'caja_chica'
            and not self.fecha_pago
            and self.fecha_comprobante
        ):
            self.fecha_pago = self.fecha_comprobante

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

    @api.depends('importe', 'descuento', 'tipo_cambio', 'moneda_id')
    def _compute_importe_mxn(self):
        for record in self:
            tipo_cambio = record.tipo_cambio or 1.0
            importe_neto = (record.importe or 0.0) - (record.descuento or 0.0)
            if record.moneda_id and record.moneda_id.name != 'MXN':
                record.importe_mxn = importe_neto * tipo_cambio
            else:
                record.importe_mxn = importe_neto

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
            if not self.tipo_pago:
                tipo_pago = factura.get_tipo_pago_control_interno()
                if tipo_pago:
                    self.tipo_pago = tipo_pago
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
            if not self.tipo_comprobante and factura.pais_id and factura.pais_id.code:
                if factura.pais_id.code.upper() == 'MX':
                    self.tipo_comprobante = 'factura_nacional'
                else:
                    self.tipo_comprobante = 'factura_extranjera'
            # If 'orden_compra_id' is empty, set it from 'factura.xml'
            if not self.orden_compra_id and factura.ordenes_compra_ids:
                self.orden_compra_id = factura.ordenes_compra_ids[0]
                self._load_data_from_purchase_order()

    @api.onchange('importe', 'descuento', 'tipo_cambio', 'moneda_id')
    def _onchange_importe_mxn(self):
        if self.moneda_id and self.moneda_id.name != 'MXN':
            tipo_cambio = self.tipo_cambio or 1.0
            importe_neto = (self.importe or 0.0) - (self.descuento or 0.0)
            self.importe_mxn = importe_neto * tipo_cambio
        else:
            self.importe_mxn = (self.importe or 0.0) - (self.descuento or 0.0)

    @api.onchange('control_interno_id')
    def _onchange_control_interno_id(self):
        domain = {}
        if self.control_interno_id:
            mes = self.mes
            mes_fin = self.mes_fin
            domain['factura_xml_id'] = [('fecha', '>=', mes), ('fecha', '<', mes_fin)]
            domain['orden_compra_id'] = [('date_order', '>=', mes), ('date_order', '<', mes_fin), ('control_interno', '=', False)]
        else:
            domain['factura_xml_id'] = []
            domain['orden_compra_id'] = [('control_interno', '=', False)]
        return {'domain': domain}

    @api.onchange('proveedor_text')
    def _onchange_proveedor_text(self):
        """Busca el proveedor_id cuando se escribe el nombre del proveedor"""
        if self.proveedor_text and not self.proveedor_id:
            # Buscar proveedor por nombre (case insensitive)
            proveedor = self.env['res.partner'].search([
                ('name', 'ilike', self.proveedor_text.strip())
            ], limit=1)
            if proveedor:
                self.proveedor_id = proveedor

    @api.onchange('cuenta_id')
    def _onchange_numero_cuenta(self):
        if self.cuenta_id:
            cuenta = self.cuenta_id
            self.descripcion_cuenta = cuenta.nombre_cuenta
            self.cuenta_num = cuenta.numero_cuenta

    @api.depends('suggested_cuenta_ids')
    def _compute_suggested_cuenta_selection(self):
        """Devuelve la primera sugerencia para mostrar en tree"""
        for record in self:
            if record.suggested_cuenta_ids:
                record.suggested_cuenta_selection = record.suggested_cuenta_ids[0]
            else:
                record.suggested_cuenta_selection = False

    def _inverse_suggested_cuenta_selection(self):
        """Cuando seleccionan una sugerencia, aplicarla al campo cuenta_id"""
        for record in self:
            if record.suggested_cuenta_selection:
                record.cuenta_id = record.suggested_cuenta_selection
                record.descripcion_cuenta = record.suggested_cuenta_selection.nombre_cuenta
                record.cuenta_num = record.suggested_cuenta_selection.numero_cuenta

    @api.depends('proveedor_id', 'concepto', 'proveedor_text')
    def _compute_suggested_cuentas(self):
        """Calcula las cuentas contables sugeridas basadas en histórico"""
        for record in self:
            # Verificar si hay al menos proveedor (id o text) o concepto
            has_proveedor = record.proveedor_id or record.proveedor_text
            has_concepto = record.concepto

            if not has_proveedor and not has_concepto:
                record.suggested_cuenta_ids = [(5, 0, 0)]
                record.suggestion_info = ''
                continue

            suggestions = record._calculate_account_suggestions()
            if suggestions:
                # Tomar solo las 3 mejores sugerencias
                top_suggestions = suggestions[:3]
                cuenta_ids = [s['cuenta_id'] for s in top_suggestions]
                record.suggested_cuenta_ids = [(6, 0, cuenta_ids)]

                # Generar HTML con la información de sugerencias
                html = '<div style="font-size: 13px; line-height: 1.6; margin-bottom: 10px;">'
                for idx, sug in enumerate(top_suggestions, 1):
                    confidence = int(sug['confidence'])
                    # Colores: verde >= 70%, amarillo >= 40%, rojo < 40%
                    if confidence >= 70:
                        color = '#28a745'
                        emoji = '🟢'
                    elif confidence >= 40:
                        color = '#ffc107'
                        emoji = '🟡'
                    else:
                        color = '#dc3545'
                        emoji = '🟠'

                    html += f'<div style="margin: 5px 0; padding: 8px; background: #f8f9fa; border-left: 3px solid {color}; border-radius: 3px;">'
                    html += f'  <strong>{idx}.</strong> <strong>[{sug["cuenta_num"]}]</strong> {sug["cuenta_name"]}'
                    html += f'  <span style="color: {color}; font-weight: bold; margin-left: 8px;">{emoji} {confidence}%</span>'
                    html += '</div>'
                html += '</div>'
                record.suggestion_info = html
            else:
                record.suggested_cuenta_ids = [(5, 0, 0)]
                # Mostrar mensaje cuando no hay sugerencias pero sí hay datos
                if has_proveedor or has_concepto:
                    record.suggestion_info = '<div style="font-size: 12px; color: #6c757d; padding: 8px; background: #f8f9fa; border-radius: 3px;">ℹ️ No hay sugerencias disponibles. Necesitas más registros históricos con cuentas asignadas.</div>'
                else:
                    record.suggestion_info = ''

    def _calculate_account_suggestions(self):
        """
        Busca en registros históricos y calcula score para cada cuenta
        Retorna lista de diccionarios con información de sugerencias
        """
        self.ensure_one()

        # Buscar registros históricos (excluyendo el actual)
        domain = [('cuenta_id', '!=', False)]
        if self.id:
            domain.append(('id', '!=', self.id))

        historical_lines = self.env['costos.gastos.line'].search(domain, limit=500)

        if not historical_lines:
            return []

        # Diccionario para acumular scores por cuenta
        cuenta_scores = {}

        # Normalizar el concepto actual para comparación
        current_concepto = self._normalize_text(self.concepto or '')
        current_concepto_words = set(current_concepto.split())

        for line in historical_lines:
            if not line.cuenta_id:
                continue

            cuenta_id = line.cuenta_id.id
            if cuenta_id not in cuenta_scores:
                cuenta_scores[cuenta_id] = {
                    'cuenta': line.cuenta_id,
                    'score': 0,
                    'matches': []
                }

            score = 0
            match_reasons = []

            # 1. Coincidencia de proveedor (peso: 5)
            if self.proveedor_id and line.proveedor_id == self.proveedor_id:
                score += 5
                match_reasons.append('Mismo proveedor')
            elif self.proveedor_text and line.proveedor_text:
                # Comparar por texto si no hay proveedor_id
                if self._normalize_text(self.proveedor_text) == self._normalize_text(line.proveedor_text):
                    score += 4
                    match_reasons.append('Proveedor similar')

            # 2. Similitud de concepto (peso: hasta 3)
            if current_concepto and line.concepto:
                line_concepto = self._normalize_text(line.concepto)
                line_concepto_words = set(line_concepto.split())

                if line_concepto_words and current_concepto_words:
                    common_words = current_concepto_words & line_concepto_words
                    similarity = len(common_words) / max(len(current_concepto_words), len(line_concepto_words))
                    concepto_score = similarity * 3
                    score += concepto_score
                    if concepto_score > 1:
                        match_reasons.append(f'Concepto similar ({int(similarity * 100)}%)')

            # 3. Penalización por antigüedad (mejor los más recientes)
            if line.fecha_comprobante:
                today = fields.Date.today()
                days_ago = (today - line.fecha_comprobante).days
                years_ago = days_ago / 365.0
                age_penalty = years_ago * 0.5
                score -= age_penalty

            cuenta_scores[cuenta_id]['score'] += score
            if match_reasons:
                cuenta_scores[cuenta_id]['matches'].extend(match_reasons)

        # 4. Frecuencia de uso (peso: hasta 2)
        for cuenta_id, data in cuenta_scores.items():
            usage_count = len([l for l in historical_lines if l.cuenta_id.id == cuenta_id])
            frequency_score = min(usage_count / 10.0, 2.0)
            data['score'] += frequency_score

        # Ordenar por score descendente
        sorted_suggestions = sorted(
            cuenta_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        # Normalizar scores a porcentaje de confianza (0-100)
        if sorted_suggestions:
            max_score = max(s['score'] for s in sorted_suggestions)
            if max_score > 0:
                for sug in sorted_suggestions:
                    # Calcular confianza como porcentaje
                    confidence = min((sug['score'] / max_score) * 100, 100)
                    sug['confidence'] = confidence

        # Formatear resultados
        results = []
        for sug in sorted_suggestions[:3]:  # Solo top 3
            results.append({
                'cuenta_id': sug['cuenta'].id,
                'cuenta_num': sug['cuenta'].numero_cuenta,
                'cuenta_name': sug['cuenta'].nombre_cuenta,
                'score': sug['score'],
                'confidence': sug['confidence'],
                'matches': list(set(sug['matches']))  # Eliminar duplicados
            })

        return results

    def _normalize_text(self, text):
        """Normaliza texto para comparación (minúsculas, sin acentos, sin espacios extra)"""
        if not text:
            return ''
        import unicodedata
        # Remover acentos
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        # Convertir a minúsculas y remover espacios extra
        text = ' '.join(text.lower().split())
        return text

    def action_apply_suggested_account(self, cuenta_id):
        """Aplica una cuenta sugerida"""
        self.ensure_one()
        if cuenta_id:
            cuenta = self.env['catalogo.cuentas'].browse(cuenta_id)
            if cuenta.exists():
                self.cuenta_id = cuenta
                self.descripcion_cuenta = cuenta.nombre_cuenta
                self.cuenta_num = cuenta.numero_cuenta
                return True
        return False

    def action_apply_suggestion_1(self):
        """Aplica la primera sugerencia"""
        self.ensure_one()
        if self.suggested_cuenta_ids:
            return self.action_apply_suggested_account(self.suggested_cuenta_ids[0].id)
        return False

    def action_apply_suggestion_2(self):
        """Aplica la segunda sugerencia"""
        self.ensure_one()
        if len(self.suggested_cuenta_ids) >= 2:
            return self.action_apply_suggested_account(self.suggested_cuenta_ids[1].id)
        return False

    def action_apply_suggestion_3(self):
        """Aplica la tercera sugerencia"""
        self.ensure_one()
        if len(self.suggested_cuenta_ids) >= 3:
            return self.action_apply_suggested_account(self.suggested_cuenta_ids[2].id)
        return False

    @api.onchange('control_interno_id')
    def _anchor_dates_on_edit(self):
        # Solo cuando ya existe (editar en form) y el control tiene mes
        if self.id and self.control_interno_id and self.control_interno_id.mes:
            first = fields.Date.to_date(self.control_interno_id.mes).replace(day=1)
            if not self.fecha_pago:
                self.fecha_pago = first
            if not self.fecha_comprobante:
                self.fecha_comprobante = first