# om_control_interno

Custom Odoo 14 module for Mexican companies to manage internal invoice control, bank reconciliation, and expense reporting.

## Features

- Import CFDI XML invoices (3.x and 4.x) individually or from ZIP archives
- Link invoices to purchase orders using a scored-suggestion algorithm
- Classify expenses with chart-of-accounts entries via an intelligent suggestion engine
- Import the chart of accounts from CSV
- Track monthly costs/expenses in a structured control record (`Control Interno Mensual`)
- Reconcile bank statement movements with expense lines (auto and manual)
- Link bank movements to purchase orders automatically during reconciliation
- Export reconciled bank movements to Excel-compatible CSV

## Dependencies

- `account` (Odoo core)
- `purchase` (Odoo core)

## Installation

1. Copy the module folder into your Odoo addons path.
2. Restart the Odoo server:
   ```
   ./odoo-bin -c odoo.conf -d <database>
   ```
3. In Odoo, go to **Apps**, search for **Control Interno**, and install.

After any code change, upgrade the module to apply field/view updates:
```
./odoo-bin -c odoo.conf -d <database> -u om_control_interno
```

## Module Structure

```
om_control_interno/
├── models/
│   ├── control_interno_mensual.py          # Monthly control record
│   ├── costos_gastos_line.py               # Individual expense lines (core model)
│   ├── factura_xml.py                      # CFDI XML invoices
│   ├── catalogo_cuentas.py                 # Chart of accounts
│   ├── purchase_order.py                   # Extended purchase.order
│   ├── estado_cuenta_bancario.py           # Bank statements and movements
│   ├── factura_xml_wizard.py               # XML upload wizard
│   ├── factura_xml_purchase_order_wizard.py
│   ├── costos_gastos_line_wizard.py
│   ├── catalogo_cuentas_import_wizard.py
│   ├── control_interno_import_wizard.py
│   ├── conciliacion_manual_wizard.py       # Manual bank reconciliation
│   └── estado_cuenta_bancario_export_wizard.py  # CSV export
├── views/
│   ├── control_interno_views.xml
│   ├── factura_xml_views.xml
│   ├── catalogo_cuentas_views.xml
│   ├── estado_cuenta_bancario_views.xml
│   ├── estado_cuenta_bancario_export_wizard_views.xml
│   ├── control_interno_menus.xml
│   └── ...
├── security/
│   └── ir.model.access.csv
├── static/src/js/
│   ├── date_anchor_control_month.js
│   └── date_control_month.js
├── data/
│   └── catalogo_cuentas_data.xml
├── CLAUDE.md
└── DEVELOPER_GUIDE.md
```

## Usage

### Importing Invoices

1. Go to **Finanzas > Control > Facturas XML**.
2. Click **Importar XML** to upload one or more CFDI files (`.xml` or `.zip`).
3. The wizard parses the CFDI, extracts UUID, RFC, amounts, and dates.
4. Payment vouchers (`tipo_comprobante = P`) are automatically skipped.
5. Duplicate UUIDs are silently ignored.

### Linking Invoices to Purchase Orders

1. From the invoice list, select records and use **Acción > Relacionar con OC**.
2. The wizard scores each purchase order by RFC, provider name similarity, amount, and date.
3. Accept the suggested PO or select one manually.

### Monthly Control Record

1. Go to **Finanzas > Control > Control Interno**.
2. Create or open a monthly record.
3. Expense lines (`costos.gastos.line`) are added here.
4. Use **Importar desde CSV** to bulk-load expense lines.
5. For each line, the system suggests chart-of-accounts entries based on historical data.

### Bank Reconciliation

1. Go to **Finanzas > Control > Estados de Cuenta Bancarios**.
2. Import a bank statement (CSV) using **Importar**.
3. Click **Auto-Conciliar** to automatically match movements to expense lines by amount.
4. For movements not auto-matched, click the movement and use **Conciliar Manualmente**.
5. The reconciliation dialog pre-filters expense lines by month and amount (±10).
6. After reconciling previously imported data, click **Sincronizar OC** to populate purchase orders from reconciled expense lines.

### CSV Export

1. In the bank statement list, select one or more records.
2. Click **Acción > Exportar Movimientos a CSV**.
3. Enter the **Etapa** label (e.g., "Aprobado", "Revisión").
4. Click **Exportar CSV** to download an Excel-compatible file.

Exported columns: `Fecha de compra`, `Etapa`, `Descripción`, `Monto`, `Fecha en estado de cuenta`, `Retiro`, `Depósito`, `Saldo`, `Diferencia`, `Observaciones`, `Órdenes de compra relacionadas`.

## Key Algorithms

### Account Suggestion Scoring

Historical expense lines are scored to suggest the most relevant chart-of-accounts entry:

| Signal | Points |
|--------|--------|
| Provider name exact match | +6 |
| Concept similarity (difflib) | up to +5 |
| Voucher type match | +3 |
| Usage frequency | up to +3 |
| Admin expense bonus | +2 |
| Age penalty | −0.3 per year |

### Purchase Order Matching

CFDI invoices are scored against open purchase orders:

| Signal | Points |
|--------|--------|
| RFC exact match | +3 |
| Provider name >60% similar | +2 |
| Amount difference <10% | +2 |
| Same month/year | +2 |
| Date within 7 days | +1 |
| Minimum threshold | 4 |

## For Developers

See [CLAUDE.md](CLAUDE.md) for architecture details, conventions, and algorithm documentation.
See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for a full integration guide.
