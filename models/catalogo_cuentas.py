#models/catalogo_cuentas.py

from odoo import models, fields, api

class CatalogoCuentas(models.Model):
    _name = 'catalogo.cuentas'
    _description = 'Catálogo de Cuentas'
    _rec_name = 'nombre_cuenta'

    nombre_cuenta = fields.Char(string='Nombre de Cuenta', required=True)
    numero_cuenta = fields.Char(string='Número de Cuenta', required=True)
    descripcion = fields.Text(string='Descripción')
    costos_gastos_line_ids = fields.One2many(
        'costos.gastos.line', 'cuenta_id',
        string='Líneas de Control Interno')
    usage_count = fields.Integer(
        string='Veces Utilizada',
        compute='_compute_usage_count',
        store=True,
        help='Número de líneas de control interno que usan esta cuenta. '
             'Se usa para mostrar primero las cuentas más utilizadas.')

    @api.depends('costos_gastos_line_ids')
    def _compute_usage_count(self):
        for cuenta in self:
            cuenta.usage_count = len(cuenta.costos_gastos_line_ids)

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
        records = self.search(domain, limit=limit, order='usage_count desc, numero_cuenta')
        return records.name_get()
