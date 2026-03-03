import base64
import csv
import io

from odoo import models, fields, api


class EstadoCuentaBancarioExportWizard(models.TransientModel):
    _name = 'estado.cuenta.bancario.export.wizard'
    _description = 'Exportar Movimientos de Estado de Cuenta a CSV'

    estado_cuenta_ids = fields.Many2many(
        'estado.cuenta.bancario',
        string='Estados de Cuenta',
    )
    etapa = fields.Char(string='Etapa', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['estado_cuenta_ids'] = [(6, 0, active_ids)]
        return res

    def action_export(self):
        """Generate and download CSV file with bank movements."""
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'Fecha de compra',
            'Etapa',
            'Descripción',
            'Monto',
            'Fecha en estado de cuenta',
            'Retiro',
            'Depósito',
            'Saldo',
            'Diferencia',
            'Observaciones',
            'Órdenes de compra relacionadas',
        ])

        for estado in self.estado_cuenta_ids.sorted('mes'):
            for mov in estado.movimiento_ids.sorted('fecha'):
                lines = mov.costos_gastos_line_ids

                # Fecha de compra: fecha_pago from linked control interno lines
                fechas = sorted({
                    str(l.fecha_pago) for l in lines if l.fecha_pago
                })
                fecha_compra = ', '.join(fechas) if fechas else (
                    str(mov.fecha) if mov.fecha else ''
                )

                # Descripción: concatenated concepts from expense lines
                conceptos = [l.concepto for l in lines if l.concepto]
                descripcion = ' | '.join(conceptos)

                # Monto: whichever side is non-zero
                monto = mov.retiro if mov.retiro else mov.deposito

                # Diferencia: negative for retiro, positive for deposito
                diferencia = -mov.retiro if mov.retiro else mov.deposito

                # Purchase orders
                oc_names = ', '.join(po.name for po in mov.purchase_order_ids)

                writer.writerow([
                    fecha_compra,
                    self.etapa,
                    descripcion,
                    monto if monto else '',
                    str(mov.fecha) if mov.fecha else '',
                    mov.retiro if mov.retiro else '',
                    mov.deposito if mov.deposito else '',
                    mov.saldo,
                    diferencia if (mov.retiro or mov.deposito) else '',
                    '',  # Observaciones: always blank
                    oc_names,
                ])

        csv_content = output.getvalue()

        attachment = self.env['ir.attachment'].create({
            'name': 'movimientos_banco.csv',
            'type': 'binary',
            'datas': base64.b64encode(csv_content.encode('utf-8-sig')),
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
