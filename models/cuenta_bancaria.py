# models/cuenta_bancaria.py

from odoo import models, fields, api


class CuentaBancaria(models.Model):
    _name = 'cuenta.bancaria'
    _description = 'Cuenta Bancaria'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, help='Alias descriptivo (ej. "Bajío Operaciones MXN")')
    numero_cuenta = fields.Char(string='Número de Cuenta', required=True, index=True)
    banco = fields.Selection(
        selection=[
            ('bajio', 'Banco del Bajío'),
            ('bbva', 'BBVA'),
            ('santander', 'Santander'),
            ('banamex', 'Banamex / Citibanamex'),
            ('hsbc', 'HSBC'),
            ('banorte', 'Banorte'),
            ('otro', 'Otro'),
        ],
        string='Banco',
        required=True,
        default='bajio',
        help='Determina el parser usado al importar estados de cuenta en PDF.',
    )
    clabe = fields.Char(string='CLABE Interbancaria')
    moneda_id = fields.Many2one('res.currency', string='Moneda')
    activo = fields.Boolean(string='Activo', default=True)
    notas = fields.Text(string='Notas')
    estado_cuenta_ids = fields.One2many(
        'estado.cuenta.bancario',
        'cuenta_bancaria_id',
        string='Estados de Cuenta',
    )
    estado_cuenta_count = fields.Integer(
        string='# Estados de Cuenta',
        compute='_compute_estado_cuenta_count',
    )

    _sql_constraints = [
        ('unique_numero_cuenta', 'unique(numero_cuenta)',
         'Ya existe una cuenta bancaria con ese número.'),
    ]

    @api.depends('estado_cuenta_ids')
    def _compute_estado_cuenta_count(self):
        for rec in self:
            rec.estado_cuenta_count = len(rec.estado_cuenta_ids)

    def name_get(self):
        result = []
        for rec in self:
            label = f"{rec.numero_cuenta} - {rec.name}" if rec.name else rec.numero_cuenta
            result.append((rec.id, label))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = ['|', ('numero_cuenta', operator, name), ('name', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
