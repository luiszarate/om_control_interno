# models/catalogo_cuentas_import_wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import csv
import io

class CatalogoCuentasImportWizard(models.TransientModel):
    _name = 'catalogo.cuentas.import.wizard'
    _description = 'Importar Catálogo de Cuentas desde CSV'

    csv_file = fields.Binary(string='Archivo CSV', required=True)
    filename = fields.Char(string='Nombre del Archivo')

    def action_import(self):
        if not self.csv_file:
            raise UserError('Debe seleccionar un archivo CSV.')

        # Decode the uploaded file
        file_content = base64.b64decode(self.csv_file)
        file_content = file_content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(file_content))

        # Skip header if present
        # header = next(csv_reader, None)

        catalogo_cuentas_obj = self.env['catalogo.cuentas']
        for row in csv_reader:
            # Assuming the CSV columns are: numero_cuenta, nombre_cuenta, descripcion
            if len(row) >= 2:
                numero_cuenta = row[0].strip()
                nombre_cuenta = row[1].strip()
                descripcion = row[2].strip() if len(row) > 2 else ''

                # Check if the account already exists
                existing_account = catalogo_cuentas_obj.search([('numero_cuenta', '=', numero_cuenta)], limit=1)
                if existing_account:
                    # Update existing account
                    existing_account.write({
                        'nombre_cuenta': nombre_cuenta,
                        'descripcion': descripcion,
                    })
                else:
                    # Create new account
                    catalogo_cuentas_obj.create({
                        'numero_cuenta': numero_cuenta,
                        'nombre_cuenta': nombre_cuenta,
                        'descripcion': descripcion,
                    })
            else:
                # Skip rows that don't have enough columns
                continue

        return {'type': 'ir.actions.act_window_close'}
