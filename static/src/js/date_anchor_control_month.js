odoo.define('om_control_interno.DateAnchorControlMonth', function (require) {
    'use strict';

    const fieldRegistry = require('web.field_registry');
    const basic_fields = require('web.basic_fields');
    const FieldDate = basic_fields.FieldDate;

    const DateAnchorControlMonth = FieldDate.extend({
        _getPickerOptions: function () {
            const opts = this._super.apply(this, arguments);
            try {
                const data = (this.record && this.record.data) || {};
                const isNew = !(this.record && this.record.res_id); // sin id => creando
                const anchor = data.mes; // related al padre: control_interno_id.mes
                const prefill = this.nodeOptions && this.nodeOptions.prefill_on_edit; // opcional

                // Solo al EDITAR, y si el campo está vacío
                if (!isNew && !this.value && anchor) {
                    const m = moment(anchor, moment.ISO_8601).startOf('month');
                    opts.defaultDate = m;
                    opts.useCurrent = false; // no autocolocar hoy

                    if (prefill) {
                        // Si algún día quieres escribir el valor al editar:
                        this._setValue(m.format('YYYY-MM-DD'));
                    }
                }
            } catch (e) {
                // nunca romper la vista por errores aquí
            }
            return opts;
        },
    });

    fieldRegistry.add('date_anchor_control_month', DateAnchorControlMonth);
    return DateAnchorControlMonth;
});
