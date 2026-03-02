odoo.define('om_control_interno.conciliacion_dialog', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.modelName === 'estado.cuenta.bancario.line') {
                    // Use setTimeout to ensure the DOM is fully mounted
                    // inside the modal before querying parent elements.
                    setTimeout(function () {
                        var $modal = self.$el.closest('.modal-dialog');
                        if ($modal.length) {
                            $modal.css('max-width', '1200px');
                        }
                    }, 0);
                }
            });
        },
    });
});
