#models/catalogo_cuentas.py

from odoo import models, fields, api

class CatalogoCuentas(models.Model):
    _name = 'catalogo.cuentas'
    _description = 'Catálogo de Cuentas'

    nombre_cuenta = fields.Char(string='Nombre de Cuenta', required=True)
    numero_cuenta = fields.Char(string='Número de Cuenta', required=True)
    descripcion = fields.Text(string='Descripción')

    def name_get(self):
        result = []
        for cuenta in self:
            name = f"[{cuenta.numero_cuenta}] {cuenta.nombre_cuenta}"
            result.append((cuenta.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = args + ['|', ('numero_cuenta', operator, name), ('nombre_cuenta', operator, name)]
        records = self.search(domain, limit=limit)
        return records.name_get()