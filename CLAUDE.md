# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module Overview

**om_control_interno** is a custom Odoo 14 module for Mexican companies to manage internal invoice control. It tracks monthly costs/expenses, imports CFDI XML invoices, links them to purchase orders, and classifies them with chart-of-accounts entries using an intelligent suggestion algorithm.

**Dependencies:** `account`, `purchase` (Odoo core modules)

## Development Setup

This is an Odoo 14 add-on. To develop and test:

1. Place the module in your Odoo addons path
2. Restart the Odoo server: `./odoo-bin -c odoo.conf -d <database>`
3. Upgrade the module after changes: `./odoo-bin -c odoo.conf -d <database> -u om_control_interno`
4. For a single model change, upgrade is required to reflect field/view changes

There are no automated tests in this module. Validation is done manually through the Odoo UI.

## Architecture

### Data Flow

```
XML Invoices (CFDI) → factura_xml.py → link to purchase.order
                                      ↓
Control Interno Mensual → costos_gastos_line.py → catalogo_cuentas.py
(monthly record)           (expense lines)          (account assignment)
                                ↓
                    Account suggestion algorithm
                    (scores historical matches)
```

### Key Models

| Model | File | Purpose |
|-------|------|---------|
| `control.interno.mensual` | `models/control_interno_mensual.py` | Monthly control record; contains all expense lines for a given month |
| `costos.gastos.line` | `models/costos_gastos_line.py` | Individual expense/cost line with 40+ fields; core of the module |
| `factura.xml` | `models/factura_xml.py` | Imported CFDI invoice; unique by UUID |
| `catalogo.cuentas` | `models/catalogo_cuentas.py` | Searchable chart of accounts; formatted as "[number] name" |
| `purchase.order` | `models/purchase_order.py` | Extended with `control_interno` boolean flag |

### Wizard Models (all transient)

- `factura.xml.wizard` — Upload/parse XML or ZIP archives of CFDI invoices
- `factura.xml.purchase.order.wizard` — Link invoices to purchase orders with scored suggestions
- `costos.gastos.line.wizard` — Confirm loading data from a purchase order into an expense line
- `catalogo.cuentas.import.wizard` — Import chart of accounts from CSV
- `control.interno.import.wizard` — Import full control interno data from CSV with flexible column mapping

### JavaScript Widgets

Located in `static/src/js/`:
- `date_anchor_control_month.js` — Date picker anchored to the parent control's month
- `date_control_month.js` — Contextual date picker widget

Registered in `views/assets.xml`.

## Key Algorithms

### Account Suggestion Scoring (`costos_gastos_line.py`)

The `_calculate_account_suggestions()` method scores historical expense lines to suggest accounts:
- Provider name exact match: **+6 points**
- Concept text similarity (difflib): **up to +5 points**
- Voucher type match: **+3 points**
- Usage frequency: **up to +3 points**
- Age penalty: **-0.3 per year old**
- Admin expense bonus: **+2 points**

Results stored in `suggested_cuenta_ids` (M2M), `suggested_cuenta_selection` (selection field), and `suggestion_info` (display string). Applied via `action_apply_suggestion_1/2/3()`.

### Purchase Order Matching (`factura_xml.py`)

`_get_suggestions_with_scores()` scores POs against an invoice:
- RFC exact match: **+3 points**
- Provider name >60% similarity: **+2 points**
- Amount difference <10%: **+2 points**
- Date within 7 days: **+1 point**
- Same month/year: **+2 points**
- Minimum threshold: **4 points**

## Important Conventions

- **Mexican CFDI support:** Handles CFDI 3.x and 4.x formats. Payment vouchers (`tipo_comprobante = 'P'`) are skipped during import.
- **UUID uniqueness:** `factura.xml` enforces a SQL UNIQUE constraint on `uuid`. Duplicates are silently skipped during import.
- **Currency handling:** Lines support MXN and foreign currencies with exchange rate fields (`tipo_cambio`, `importe_mn`).
- **Text normalization:** `_normalize_text()` in `costos_gastos_line.py` strips accents, lowercases, and removes special chars — used consistently for matching/comparison.
- **CSV import flexibility:** `control_interno_import_wizard.py` uses flexible header normalization to handle column name variations.
- **`proveedor_text`** is a free-text vendor name field used alongside the relational `proveedor_id`; the suggestion algorithm keys on `proveedor_text`.

## File Locations

- Model access rules: `security/ir.model.access.csv`
- Initial account data: `data/catalogo_cuentas_data.xml`
- Menu structure: `views/control_interno_menus.xml` (under Finance > Controls)
- Full integration guide: `DEVELOPER_GUIDE.md`
