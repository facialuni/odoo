odoo.define('crm.crm_team_customer', function (require) {
"use strict";

var core = require('web.core');
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');

var GoogleMapAddress = relational_fields.FieldMany2One.extend({
	/**
	 * This widget redirects from opportunity form to customer's address on Google maps.
	 *
     * @private
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        if (this.mode === 'readonly' && this.nodeOptions.always_reload) {
            var partner_data = this.record.data;
            var partner_country = partner_data.country_id.data.display_name;
            if (partner_country){
                event.preventDefault();
                event.stopPropagation();
                var queryObj = {
                    'q': (partner_data.street || '')+(partner_data.city || '')+(partner_data.zip || '')+(partner_country || ''),
                    'z': 10,
                }
                var redirect_url = 'https://maps.google.com/maps?'+$.param(queryObj);
                window.open(redirect_url, '_blank');
            }
            else {
                this._super.apply(this, arguments);
            }
        }
    },

});

field_registry.add('google_map_address', GoogleMapAddress);

});