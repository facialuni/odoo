odoo.define('im_livechat.copy_text_tests', function (require) {
"use strict";

var core = require('web.core');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var createAsyncView = testUtils.createAsyncView;


var _t = core._t;
var createView = testUtils.createView;

QUnit.module('im_livechat', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    script_external: {string: "Script External", type: "char"},
                },
                records: [{
                    id: 1,
                    script_external:'Random Useless Text',
                },],
            },
        };
    }
}, function () {

    QUnit.test('copy_text_button', function (assert) {
        var done = assert.async();
        assert.expect(1);

        createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                            '<group>' +
                                '<field name="script_external" widget="CopyClipboard"/>' +
                                '<field name="web_page" widget="CopyClipboard"/>' +
                            '</group>' +
                    '</sheet>' +
                '</form>',
        }).then(function(form){
        var buttons = form.$el.find('.o_clipboard_button');
        assert.strictEqual(form.$('.o_clipboard_button').length, 1,"should contain a 1 button with some html");
        form.destroy();
        done();
        });
    });
});
});
