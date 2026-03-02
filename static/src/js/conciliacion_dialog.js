odoo.define('om_control_interno.conciliacion_dialog', function (require) {
    "use strict";

    // Use a MutationObserver on <body> to detect when a modal containing
    // the conciliation wizard form is inserted into the DOM.  This is the
    // most reliable approach because it fires regardless of the timing
    // between the Dialog widget, the ActionManager and the FormController.

    function widenIfConciliacionWizard(node) {
        if (node.nodeType !== 1) return;  // only Element nodes
        // The node itself might be the .modal, or it could be nested
        var modals = [];
        if (node.classList && node.classList.contains('modal')) {
            modals.push(node);
        }
        if (node.querySelectorAll) {
            modals = modals.concat(
                Array.prototype.slice.call(node.querySelectorAll('.modal'))
            );
        }
        modals.forEach(function (modal) {
            // Poll briefly for the form to render inside the modal
            var checks = 0;
            var interval = setInterval(function () {
                checks++;
                var form = modal.querySelector(
                    '.o_field_widget[name="movimiento_id"]'
                );
                if (form) {
                    var dialog = modal.querySelector('.modal-dialog');
                    if (dialog) {
                        dialog.style.maxWidth = '1200px';
                    }
                    clearInterval(interval);
                }
                if (checks >= 40) {  // 2 seconds max
                    clearInterval(interval);
                }
            }, 50);
        });
    }

    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(widenIfConciliacionWizard);
        });
    });

    // Start observing once the DOM is ready
    $(function () {
        observer.observe(document.body, {childList: true, subtree: true});
    });
});
