"""Pre-migration script for 14.0.1.1.0.

Creates the ``cuenta.bancaria`` table (if Odoo has not done it yet for an
upgrade), seeds it from distinct ``numero_cuenta`` values found in
``estado_cuenta_bancario``, adds the ``cuenta_bancaria_id`` column to
``estado_cuenta_bancario`` and back-fills it before Odoo applies the
NOT NULL constraint required by the new ``required=True`` field.

Runs before the registry is fully loaded with the new model definitions,
so we must use raw SQL.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    _logger.info("om_control_interno: pre-migrate to %s -- seeding cuenta.bancaria", version)

    # 1. Ensure the cuenta_bancaria table exists (created automatically by
    #    Odoo's ORM init for new model, but we may run pre-migrate before
    #    that). Create a minimal version idempotently.
    cr.execute("""
        CREATE TABLE IF NOT EXISTS cuenta_bancaria (
            id SERIAL PRIMARY KEY,
            name VARCHAR,
            numero_cuenta VARCHAR,
            banco VARCHAR,
            clabe VARCHAR,
            moneda_id INTEGER,
            activo BOOLEAN DEFAULT TRUE,
            notas TEXT,
            create_uid INTEGER,
            create_date TIMESTAMP WITHOUT TIME ZONE,
            write_uid INTEGER,
            write_date TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    # 2. Check whether estado_cuenta_bancario already has the new column.
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'estado_cuenta_bancario'
          AND column_name = 'cuenta_bancaria_id';
    """)
    has_col = cr.fetchone()

    if not has_col:
        cr.execute("""
            ALTER TABLE estado_cuenta_bancario
            ADD COLUMN cuenta_bancaria_id INTEGER;
        """)
        _logger.info("Added column estado_cuenta_bancario.cuenta_bancaria_id")

    # 3. Seed cuenta_bancaria from distinct existing numero_cuenta values.
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'estado_cuenta_bancario'
          AND column_name = 'numero_cuenta';
    """)
    if not cr.fetchone():
        _logger.info("No legacy numero_cuenta column found, skipping seed.")
        return

    cr.execute("""
        SELECT DISTINCT TRIM(numero_cuenta)
        FROM estado_cuenta_bancario
        WHERE numero_cuenta IS NOT NULL
          AND TRIM(numero_cuenta) <> ''
        ORDER BY 1;
    """)
    existing = [row[0] for row in cr.fetchall()]
    _logger.info("Found %d distinct legacy bank account numbers to seed", len(existing))

    for numero in existing:
        cr.execute("""
            SELECT id FROM cuenta_bancaria WHERE numero_cuenta = %s LIMIT 1;
        """, (numero,))
        row = cr.fetchone()
        if row:
            cuenta_id = row[0]
        else:
            cr.execute("""
                INSERT INTO cuenta_bancaria
                    (name, numero_cuenta, banco, activo, create_date, write_date)
                VALUES
                    (%s, %s, %s, TRUE, NOW(), NOW())
                RETURNING id;
            """, (numero, numero, 'bajio'))
            cuenta_id = cr.fetchone()[0]
            _logger.info("Created cuenta_bancaria id=%s for numero=%s", cuenta_id, numero)

        # 4. Back-fill estado_cuenta_bancario rows.
        cr.execute("""
            UPDATE estado_cuenta_bancario
            SET cuenta_bancaria_id = %s
            WHERE TRIM(numero_cuenta) = %s
              AND (cuenta_bancaria_id IS NULL);
        """, (cuenta_id, numero))

    # 5. Sanity check: any estado_cuenta_bancario row left without a
    #    cuenta_bancaria_id will block the NOT NULL constraint. Warn the
    #    operator but do not abort -- Odoo will fail loudly afterwards.
    cr.execute("""
        SELECT COUNT(*) FROM estado_cuenta_bancario
        WHERE cuenta_bancaria_id IS NULL;
    """)
    leftover = cr.fetchone()[0]
    if leftover:
        _logger.warning(
            "estado_cuenta_bancario has %d row(s) with NULL cuenta_bancaria_id "
            "after seeding. Update them manually before the module finishes "
            "loading.", leftover,
        )
    else:
        _logger.info("All estado_cuenta_bancario rows successfully linked to cuenta_bancaria.")
