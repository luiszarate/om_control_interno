odoo.define('om_control_interno.conciliacion_dialog', function (require) {
    "use strict";

    // Widen the modal when it contains the conciliation wizard form.
    // We listen to Bootstrap's shown.bs.modal event which fires after
    // the modal is fully visible and its content is rendered, then
    // poll briefly for the form view to appear inside it.
    $(document).on('shown.bs.modal', '.modal', function () {
        var $modal = $(this);
        var checks = 0;
        var interval = setInterval(function () {
            checks++;
            // Look for the conciliation wizard form view inside this modal
            if ($modal.find('.o_form_view').length &&
                $modal.find('[name="filtro_fecha_inicio"]').length) {
                $modal.find('.modal-dialog').css('max-width', '1200px');
                clearInterval(interval);
            }
            if (checks >= 20) {
                clearInterval(interval);
            }
        }, 50);
    });
});
