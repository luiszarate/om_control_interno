odoo.define('om_control_interno.DateControlMonth', function (require) {
    'use strict';

    const fieldRegistry = require('web.field_registry');
    const basic_fields = require('web.basic_fields');
    const FieldDate = basic_fields.FieldDate;

    const DateControlMonth = FieldDate.extend({
        /**
         * Inyecta defaultDate en el picker para abrirlo en el mes deseado
         * sin establecer valor. Opcionalmente, puede prefillear si así se pide.
         */
        _getPickerOptions: function () {
            const opts = this._super.apply(this, arguments);
            try {
                const ctx = this.record && this.record.getContext
                    ? this.record.getContext(this.recordParams)
                    : (this.getSession && this.getSession().user_context) || {};

                const onlyOnEdit = !!ctx.only_on_edit;              // true => solo cuando es registro existente
                const prefillOnEdit = !!ctx.prefill_on_edit;        // true => sí escribir el valor si está vacío
                const baseDate = ctx.control_month_first_day;       // 'YYYY-MM-DD'
                const isNew = !(this.record && this.record.res_id); // sin id real => nuevo

                if (onlyOnEdit && isNew) {
                    return opts; // no hacer nada al crear
                }
                if (!this.value && baseDate) {
                    // 1) GUIAR el calendario (no escribe valor)
                    opts.defaultDate = moment(baseDate, moment.ISO_8601);
                    opts.useCurrent = false;

                    // 2) OPCIONAL: prefillear al editar si está vacío
                    if (prefillOnEdit) {
                        // Establece el valor del campo (el usuario lo puede cambiar)
                        // Formato ISO (Date field):
                        const iso = moment(baseDate, moment.ISO_8601).format('YYYY-MM-DD');
                        this._setValue(iso);
                    }
                }
            } catch (e) {
                // nunca romper la vista por un problema de contexto
            }
            return opts;
        },
    });

    fieldRegistry.add('date_control_month', DateControlMonth);
    return DateControlMonth;
});
