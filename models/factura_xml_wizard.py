#models/factura.xml.wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import zipfile
import io
import xml.etree.ElementTree as ET

class FacturaXMLWizard(models.TransientModel):
    _name = 'factura.xml.wizard'
    _description = 'Asistente para cargar Facturas XML'

    xml_file = fields.Binary(string='Archivo XML', attachment=False)
    zip_file = fields.Binary(string='Archivo ZIP', attachment=False)
    filename = fields.Char(string='Nombre de Archivo')

    def cargar_facturas_xml(self):
        if self.zip_file:
            data = base64.b64decode(self.zip_file)
            with zipfile.ZipFile(io.BytesIO(data), 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith('.xml'):
                        xml_content = zip_ref.read(file_info.filename)
                        self._parse_xml(xml_content, file_info.filename)
        elif self.xml_file:
            xml_content = base64.b64decode(self.xml_file)
            self._parse_xml(xml_content, self.filename)
        else:
            raise UserError('Debe cargar un archivo XML o ZIP.')

    def _parse_xml(self, xml_content, filename):
        root = ET.fromstring(xml_content)
        version = root.attrib.get('Version', root.attrib.get('version', ''))
        if version.startswith('3'):
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/3'}
        else:
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/4'}

        tipo_de_comprobante = root.attrib.get('TipoDeComprobante')
        if tipo_de_comprobante == 'P':
            return

        complemento = root.find('cfdi:Complemento', ns)
        uuid = ''
        if complemento is not None:
            tfd = complemento.find('tfd:TimbreFiscalDigital', {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'})
            if tfd is not None:
                uuid = tfd.get('UUID', '')

        emisor = root.find('cfdi:Emisor', ns)
        rfc = emisor.get('Rfc', '') if emisor is not None else ''
        nombre = emisor.get('Nombre', '') if emisor is not None else ''

        folio = root.attrib.get('Folio', '')
        fecha = root.attrib.get('Fecha', '')
        subtotal = float(root.attrib.get('SubTotal', '0'))
        total = float(root.attrib.get('Total', '0'))
        descuento = float(root.attrib.get('Descuento', '0'))
        moneda = root.attrib.get('Moneda', 'MXN')
        tipo_cambio = float(root.attrib.get('TipoCambio', '1'))

        impuestos = root.find('cfdi:Impuestos', ns)
        iva = 0.0
        if impuestos is not None:
            traslados = impuestos.find('cfdi:Traslados', ns)
            if traslados is not None:
                for traslado in traslados.findall('cfdi:Traslado', ns):
                    if traslado.attrib.get('Impuesto') in ['002', 'IVA']:
                        iva += float(traslado.attrib.get('Importe', '0'))

        conceptos = root.find('cfdi:Conceptos', ns)
        descripcion_concatenada = ''
        if conceptos is not None:
            descripcion_concatenada = ', '.join([
                concepto.attrib.get('Descripcion', '') for concepto in conceptos.findall('cfdi:Concepto', ns)
            ])

        proveedor = self.env['res.partner'].search([('vat', '=', rfc)], limit=1)
        

        moneda_id = self.env['res.currency'].search([('name', '=', moneda)], limit=1)

        self.env['factura.xml'].create({
            'filename': filename,
            'uuid': uuid,
            'folio': folio,
            'fecha': fecha,
            'proveedor_id': proveedor.id,
            'proveedor_text': nombre,
            'rfc': rfc,
            'pais_id': proveedor.country_id.id or self.env.ref('base.mx').id,
            'subtotal': subtotal,
            'descuento': descuento,
            'moneda_id': moneda_id.id,
            'tipo_cambio': tipo_cambio,
            'iva': iva,
            'total': total,
            'concepto': descripcion_concatenada,
        })
