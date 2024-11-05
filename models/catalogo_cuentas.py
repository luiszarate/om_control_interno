#models/catalogo_cuentas.py

from odoo import models, fields

class CatalogoCuentas(models.Model):
    _name = 'catalogo.cuentas'
    _description = 'Catálogo de Cuentas'

    nombre_cuenta = fields.Char(string='Nombre de Cuenta', required=True)
    numero_cuenta = fields.Char(string='Número de Cuenta', required=True)
    descripcion = fields.Text(string='Descripción')
