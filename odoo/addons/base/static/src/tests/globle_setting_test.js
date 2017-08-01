odoo.define('web.globle_setting_test', function (require) {
"use strict";

var core = require('web.core');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var GlobleSetting = require('base.globle_settings');
console.log("GlobleSetting", GlobleSetting);

var createView = testUtils.createView;
var _t = core._t;

QUnit.module('globle_settings_tests', {
    beforeEach: function () {
        this.data = {
            project: {
                fields: {
                    foo: {string: "Foo", type: "boolean"},
                    bar: {string: "Bar", type: "boolean"},
                },
            },
        };
    }
}, function () {

    QUnit.module('GlobleSetting');

    QUnit.test('change setting on nav bar click in globle settings', function (assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'project',
            data: this.data,
            arch: '<form string="Settings" class="oe_form_configuration globleSettings" js_class="globle_settings">' +
                    '<div class="o_panel">' + 
                        '<div class="setting_search">' + 
                            '<input type="text" class="searchInput" placeholder="Search..."/>' +
                        '</div> ' + 
                    '</div> ' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Cancel" type="object" name="cancel" class="oe_link" />' +
                    '</header>' +
                    '<div class="row new_setting">' +
                        '<div class="col-md-2 leftpan">' +
                            '<div class="apps">' +
                                '<div class="appContainer" setting="project" groups="project.group_project_manager">' +
                                    '<div class="logo project"/> <span class="app_name">Project</span>'+
                                '</div>'+
                            '</div>' +
                        '</div>' +
                        '<div class="col-md-10 rightpan">' +
                           '<div class="notFound o_hidden">No Record Found</div>' +
                           '<div class="settings">' +
                                '<div class="project_setting_view o_hidden" groups="project.group_project_manager">' +
                                    '<div class="row mt16 o_settings_container">'+
                                        '<div class="col-xs-12 col-md-6 o_setting_box">'+
                                            '<div class="o_setting_left_pane">' +
                                                '<field name="bar"/>'+
                                            '</div>'+
                                            '<div class="o_setting_right_pane">'+
                                                '<label for="bar"/>'+
                                                '<div class="text-muted">'+
                                                    'this is bar'+
                                                '</div>'+
                                            '</div>' +
                                        '</div>'+
                                        '<div class="col-xs-12 col-md-6 o_setting_box">'+
                                            '<div class="o_setting_left_pane">' +
                                                '<field name="foo"/>'+
                                            '</div>'+
                                            '<div class="o_setting_right_pane">'+
                                                '<label for="foo"/>'+
                                                '<div class="text-muted">'+
                                                    'this is foo'+
                                                '</div>'+
                                            '</div>' +
                                        '</div>'+
                                    '</div>' +    
                                '</div>' +
                           '</div>' +
                        '</div>' +
                    '</div>' +
                '</form>',
        });

        assert.strictEqual(form.$('.selected').length,0,"default focused");
        form.$("div[setting='project']").click();
        assert.strictEqual(form.$('.selected').attr('setting'),"project","project setting selected");
        assert.strictEqual(form.$(".project_setting_view").hasClass('show'),true,"project settings show");
        form.$('.searchInput').val('b').trigger('keyup');
        assert.strictEqual($('.hiliterWord').html(),"B","b word hilited");
        form.$('.searchInput').val('bx').trigger('keyup');
        assert.strictEqual(form.$('.notFound').hasClass('o_hidden'),false,"record not found message shown");
        form.destroy();
    });
});
});
