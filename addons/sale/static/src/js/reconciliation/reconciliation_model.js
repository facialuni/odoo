odoo.define('sale.ReconciliationModel', function (require) {
"use strict";

var ReconciliationModel = require('account.ReconciliationModel');

ReconciliationModel.StatementModel.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} handle
     * @param {Object[]}
     */
    addMultiPropositions: function (handle, props) {
        var line = this.getLine(handle);
        this._formatLineProposition(line, props);
        if (!line.reconciliation_proposition) {
            line.reconciliation_proposition = [];
        }
        line.reconciliation_proposition.push.apply(line.reconciliation_proposition, props);
        return this._computeLine(line);
    },
});

return ReconciliationModel;
});
