odoo.define('web_settings_dashboard.dashboard_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Dashboard = require('web_settings_dashboard');
var Widget = require('web.Widget');

QUnit.module('Settings', {}, function () {

    QUnit.test('Dashboard: Invite new user', function (assert) {
        assert.expect(1);
        var self = this;

        function createParent(params) {
            var widget = new Dashboard.Dashboard();
            testUtils.addMockEnvironment(widget,{
                mockRPC: function (route, args) {
                    if (route === '/web_settings_dashboard/data') {
                        return $.when(params['data']);
                }
                return this._super(route, args);
                },
            });
            return widget;
        }

        this.data = {
            'active_users': 1,
            'pending_counts': 1,
            'pending_users':[{'id': 1, 'email': 'xyz@odoo.com'}],
        }

        var parent = createParent({
            'data': {'apps':{},
                    'share':{},
                    'users_info': self.data,
                    }
        });

        var dashboard_invitations = new Dashboard.DashboardInvitations(parent, self.data);
        testUtils.addMockEnvironment(dashboard_invitations, {
            mockRPC: function (route, args) {
                if (args.method === 'web_dashboard_create_users') {
                    self.data.active_users++;
                    self.data.pending_counts++;
                    self.data.pending_users.push({'id': 2, 'email': args['args'][0][0]});
                    return $.when();
                }
            return this._super(route, args);
            },
        });

        dashboard_invitations.appendTo($('#qunit-fixture'));
        var inputbox = dashboard_invitations.$el.find('#user_emails').val("abc@odoo.com");
        var event = jQuery.Event("keypress");
        event.keyCode = 13;
        if(inputbox.trigger(event)) {
            dashboard_invitations.$el.find('.o_web_settings_dashboard_invitations').trigger('click');
            assert.strictEqual(dashboard_invitations.data['pending_users'].length, 2, "New user created");
        }
});

});
});
