odoo.define('om_control_interno.DateAnchorControlMonth', function (require) {
    'use strict';

    const fieldRegistry = require('web.field_registry');
    const basic_fields = require('web.basic_fields');
    const FieldDate = basic_fields.FieldDate;

    const DateAnchorControlMonth = FieldDate.extend({
        /**
         * Odoo 14 usa _getPickerOptions; agregamos también getPickerOptions como fallback.
         */
        _getPickerOptions: function () {
            const opts = this._super.apply(this, arguments);
            return this._patchPickerOptions(opts);
        },
        getPickerOptions: function () { // fallback por si tu build llama este
            const opts = this._super.apply(this, arguments);
            return this._patchPickerOptions(opts);
        },

        _patchPickerOptions: function (opts) {
            try {
                // En v14 suele existir recordData/res_id; dejamos fallback por si acaso
                const data = this.recordData || (this.record && this.record.data) || {};
                const resId = this.res_id || (this.record && this.record.res_id);
                const isNew = !resId;

                // 'mes' es related al padre y debe estar presente (invisible) en la vista de la línea
                const anchor = data.mes;  // formato YYYY-MM-DD
                const nodeOpts = this.nodeOptions || {}; // opciones del <field ... options="{}">

                // Solo al EDITAR, y si el campo está vacío -> anclar calendario al 1ro del mes
                if (!isNew && !this.value && anchor) {
                    const m = moment(anchor, moment.ISO_8601).startOf('month');
                    opts.defaultDate = m;
                    opts.useCurrent = false; // no autocolocar hoy

                    // Si quieres también prellenar el valor al editar, usa options="{'prefill_on_edit': true}"
                    if (nodeOpts.prefill_on_edit) {
                        this._setValue(m.format('YYYY-MM-DD'));
                    }
                }
            } catch (e) {
                // Nunca romper la vista por un error aquí
                // console.warn('date_anchor_control_month error', e);
            }
            return opts;
        },
    });

    fieldRegistry.add('date_anchor_control_month', DateAnchorControlMonth);
    return DateAnchorControlMonth;
});
