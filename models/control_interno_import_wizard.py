# models/control_interno_import_wizard.py

from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
import base64
import csv
import io
import unicodedata

class ControlInternoImportWizard(models.TransientModel):
    _name = 'control.interno.import.wizard'
    _description = 'Asistente para importar Control Interno desde CSV'

    csv_file = fields.Binary(string='Archivo CSV', required=True)
    filename = fields.Char(string='Nombre del Archivo')
    control_interno_id = fields.Many2one('control.interno.mensual', string='Control Interno Mensual')

    def action_import(self):
        if not self.csv_file:
            raise UserError('Debe seleccionar un archivo CSV.')

        # Decode the uploaded file
        file_content = base64.b64decode(self.csv_file)
        file_content = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))

        # Define the expected fields and possible variations
        expected_fields = {
            'orden_compra_id': ['orden de compra', 'oc', 'orden compra'],
            'fecha_pago': ['fecha de pago', 'fecha pago'],
            'tipo_pago': ['tipo de pago', 'tipo pago'],
            'tipo_comprobante': ['tipo de comprobante', 'tipo comprobante'],
            'folio_fiscal': ['folio fiscal'],
            'no_comprobante': ['no. comprobante', 'numero comprobante', 'no comprobante'],
            'fecha_comprobante': ['fecha de comprobante', 'fecha comprobante'],
            'concepto': ['concepto'],
            'proveedor_text': ['proveedor'],
            'tax_id': ['tax id', 'rfc'],
            'country_id': ['country', 'pais'],
            'importe': ['importe'],
            'descuento': ['descuento'],
            'moneda_id': ['moneda'],
            'tipo_cambio': ['tipo de cambio', 'tipo cambio'],
            'importe_mxn': ['importe mxn'],
            'iva': ['iva'],
            'total': ['total'],
            'retencion_iva': ['retención iva', 'retencion iva'],
            'otras_retenciones': ['otras retenciones'],
            'pedimento_no': ['pedimento no.', 'pedimento numero'],
            'iva_pedimento': ['iva pedimento'],
            'otros_impuestos_pedimento': ['otros impuestos pedimento'],
            'division_subcuentas': ['división en subcuentas', 'division en subcuentas'],
            'importe_subcuenta': ['importe subcuenta'],
            'descuento_subcuenta': ['descuento subcuenta'],
            'total_subcuenta_sin_iva': ['total subcuenta s/iva', 'total subcuenta sin iva'],
            'descripcion_cuenta': ['descripción de cuenta', 'descripcion de cuenta'],
            'cuenta_id': ['cuenta'],
            'comentarios_imago': ['comentarios imago aerospace', 'comentarios imago'],
            'comentarios_contador': ['comentarios contador']
        }

        # Normalize CSV column names and map them to expected fields
        def normalize_string(s):
            if not s:
                return ''
            s = s.strip()
            s = s.lower()
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            return s

        csv_fieldnames_normalized = [normalize_string(name) for name in csv_reader.fieldnames]

        field_mapping = {}
        for expected_field, possible_names in expected_fields.items():
            found = False
            for possible_name in possible_names:
                normalized_possible_name = normalize_string(possible_name)
                if normalized_possible_name in csv_fieldnames_normalized:
                    index = csv_fieldnames_normalized.index(normalized_possible_name)
                    csv_fieldname = csv_reader.fieldnames[index]
                    field_mapping[expected_field] = csv_fieldname
                    found = True
                    break
            if not found:
                field_mapping[expected_field] = None

        missing_fields = [field for field, csv_name in field_mapping.items() if not csv_name]

        for field in missing_fields:
            field_mapping[field] = None  # O asignar un valor por defecto
        '''if missing_fields:
            missing_fields_names = ', '.join(missing_fields)
            raise UserError(f'Las siguientes columnas faltan en el archivo CSV: {missing_fields_names}')'''

        costos_gastos_line_obj = self.env['costos.gastos.line']
        catalogo_cuentas_obj = self.env['catalogo.cuentas']
        purchase_order_obj = self.env['purchase.order']
        res_partner_obj = self.env['res.partner']
        res_country_obj = self.env['res.country']
        res_currency_obj = self.env['res.currency']

        tipo_comprobante_mapping = {
            'factura nacional': 'factura_nacional',
            'factura extranjera': 'factura_extranjera',
            'nota de remision': 'nota_remision',
            'nota de remisión': 'nota_remision',
            'pedimento': 'pedimento',
            'linea de captura': 'linea_captura',
            'línea de captura': 'linea_captura',
            'estado de cuenta': 'estado_cuenta',
            'recibo de caja': 'recibo_caja',
            'sin recibo': 'sin_recibo',
        }

        tipo_pago_mapping = {
            'caja chica': 'caja_chica',
            'tarjeta de débito': 'debito',
            'tarjeta de debito': 'debito',
            'debito': 'debito',
            'débito': 'debito',
            'credito': 'credito',
            'crédito': 'credito',
            'tarjeta de crédito': 'credito',
            'tarjeta de credito': 'credito',
            'transferencia': 'transferencia',
            'otro': 'otro',
            'efectivo': 'efectivo',
            'cheque': 'cheque',
        }

        for row in csv_reader:
            # Build the data dict using the field mapping
            data = {}
            for field, csv_name in field_mapping.items():
                data[field] = row.get(csv_name, '') if csv_name else ''

            # Buscar o crear los registros relacionados
            orden_compra = None
            if data['orden_compra_id']:
                orden_compra = purchase_order_obj.search([('name', '=', data['orden_compra_id'])], limit=1)
                if not orden_compra:
                    # Si no existe la orden de compra, puedes decidir crearla o lanzar un error
                    orden_compra = purchase_order_obj.create({'name': data['orden_compra_id'], 'partner_id': False})

            proveedor = None
            if data['proveedor_text']:
                proveedor = res_partner_obj.search([('name', '=', data['proveedor_text'])], limit=1)
                if not proveedor:
                    proveedor = res_partner_obj.create({'name': data['proveedor_text']})

            country = None
            if data['country_id']:
                country = res_country_obj.search([('name', '=', data['country_id'])], limit=1)

            moneda = None
            if data['moneda_id']:
                moneda = res_currency_obj.search([('name', '=', data['moneda_id'])], limit=1)

            cuenta = None
            if data['cuenta_id']:
                cuenta = catalogo_cuentas_obj.search([('numero_cuenta', '=', data['cuenta_id'])], limit=1)

            # Convertir fechas y valores numéricos
            def parse_date(date_str):
                formats = ["%d/%m/%y", "%d-%m-%y", "%d-%b", "%d-%B"]  # Formatos de fecha posibles
                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        # Si el año no está incluido, se asume el año actual
                        if "%y" not in fmt:
                            parsed_date = parsed_date.replace(year=datetime.now().year)
                        return fields.Date.to_string(parsed_date)
                    except ValueError:
                        continue  # Prueba el siguiente formato si el actual falla
                return False  # Retorna False si no se pudo convertir en ninguno de los formatos

            def parse_float(value):
                try:
                    value = value.replace(',', '').replace(' ', '').replace('$', '')
                    return float(value)
                except:
                    return 0.0
                
            tipo_comprobante_csv_value = data['tipo_comprobante']
            if tipo_comprobante_csv_value:
                tipo_comprobante_normalized = normalize_string(tipo_comprobante_csv_value)
                tipo_comprobante_key = tipo_comprobante_mapping.get(tipo_comprobante_normalized)
                if not tipo_comprobante_key:
                    raise UserError(f"Tipo de comprobante '{tipo_comprobante_csv_value}' no reconocido.")
            else:
                tipo_comprobante_key = False

            tipo_pago_csv_value = data['tipo_pago']
            if tipo_pago_csv_value:
                tipo_pago_normalized = normalize_string(tipo_pago_csv_value)
                tipo_pago_key = tipo_pago_mapping.get(tipo_pago_normalized)
                if not tipo_pago_key:
                    raise UserError(f"Tipo de pago '{tipo_pago_csv_value}' no reconocido.")
            else:
                tipo_pago_key = False

            # Crear la línea de costos y gastos
            costos_gastos_line_obj.create({
                'control_interno_id': self.control_interno_id.id,
                'orden_compra_id': orden_compra.id if orden_compra else False,
                'fecha_pago': parse_date(data['fecha_pago']),
                'tipo_pago': tipo_pago_key,
                'tipo_comprobante': tipo_comprobante_key,
                'folio_fiscal': data['folio_fiscal'],
                'no_comprobante': data['no_comprobante'],
                'fecha_comprobante': parse_date(data['fecha_comprobante']),
                'concepto': data['concepto'],
                'proveedor_id': proveedor.id if proveedor else False,
                'proveedor_text': data['proveedor_text'],
                'tax_id': data['tax_id'],
                'country_id': country.id if country else False,
                'importe': parse_float(data['importe']),
                'descuento': parse_float(data['descuento']),
                'moneda_id': moneda.id if moneda else False,
                'tipo_cambio': parse_float(data['tipo_cambio']),
                'importe_mxn': parse_float(data['importe_mxn']),
                'iva': parse_float(data['iva']),
                'total': parse_float(data['total']),
                'retencion_iva': parse_float(data['retencion_iva']),
                'otras_retenciones': parse_float(data['otras_retenciones']),
                'pedimento_no': data['pedimento_no'],
                'iva_pedimento': parse_float(data['iva_pedimento']),
                'otros_impuestos_pedimento': parse_float(data['otros_impuestos_pedimento']),
                'division_subcuentas': data['division_subcuentas'],
                'importe_subcuenta': parse_float(data['importe_subcuenta']),
                'descuento_subcuenta': parse_float(data['descuento_subcuenta']),
                'total_subcuenta_sin_iva': parse_float(data['total_subcuenta_sin_iva']),
                'descripcion_cuenta': data['descripcion_cuenta'],
                'cuenta_id': cuenta.id if cuenta else False,
                'comentarios_imago': data['comentarios_imago'],
                'comentarios_contador': data['comentarios_contador'],
            })

        return {'type': 'ir.actions.act_window_close'}

