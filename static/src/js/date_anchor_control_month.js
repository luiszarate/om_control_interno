odoo.define('om_control_interno.DateAnchorControlMonth', function (require) {
    'use strict';

    const fieldRegistry = require('web.field_registry');
    const basic_fields = require('web.basic_fields');
    const FieldDate = basic_fields.FieldDate;

    const DateAnchorControlMonth = FieldDate.extend({
        _getPickerOptions: function () {
            const opts = this._super.apply(this, arguments);
            return this._patchPickerOptions(opts);
        },
        getPickerOptions: function () { // fallback por si tu build usa este
            const opts = this._super.apply(this, arguments);
            return this._patchPickerOptions(opts);
        },

        _patchPickerOptions: function (opts) {
            try {
                const data   = this.recordData || (this.record && this.record.data) || {};
                const resId  = this.res_id || (this.record && this.record.res_id);
                const isNew  = !resId;
                const anchor = data.mes; // 'YYYY-MM-DD' (related del padre)
                const nodeOpts = this.nodeOptions || {};

                if (!isNew && !this.value && anchor) {
                    const m = moment(anchor, 'YYYY-MM-DD', true); // estricto ISO
                    if (m.isValid()) {
                        opts.useCurrent = false;
                        // Para el init del picker:
                        opts.defaultDate = m;
                        // Para el mes mostrado:
                        opts.viewDate = m;

                        if (nodeOpts.prefill_on_edit) {
                            this._setValue(m.format('YYYY-MM-DD'));
                        }
                    }
                }
            } catch (e) {}
            return opts;
        },

        // Se llama cuando el popup se muestra; aquí volvemos a fijar el mes
        _onDateTimePickerShow: function () {
            this._super.apply(this, arguments);
            try {
                const data   = this.recordData || (this.record && this.record.data) || {};
                const resId  = this.res_id || (this.record && this.record.res_id);
                const isNew  = !resId;
                const anchor = data.mes;

                if (!isNew && !this.value && anchor) {
                    const m = moment(anchor, 'YYYY-MM-DD', true);
                    if (m.isValid() && this.$input) {
                        const dp = this.$input.data('DateTimePicker');
                        if (dp && typeof dp.viewDate === 'function') {
                            dp.viewDate(m);            // mueve solo la vista
                        } else if (dp && typeof dp.date === 'function') {
                            // fallback: mover a la fecha y limpiar para no escribir valor
                            dp.date(m, true);          // true = no trigger change
                            dp.clear();
                        }
                    }
                }
            } catch (e) {}
        },
    });

    fieldRegistry.add('date_anchor_control_month', DateAnchorControlMonth);
    return DateAnchorControlMonth;
});
