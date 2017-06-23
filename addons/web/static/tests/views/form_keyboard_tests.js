odoo.define('web.form_keyboard_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var core = require('web.core');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var _t = core._t;
var createView = testUtils.createView;
var createAsyncView = testUtils.createAsyncView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1] },
                    htmldata : {string: "HTML Field" , type: "html"},
                    p: {string: "one2many field", type: "one2many", relation: 'partner'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    priority: {
                        string: "Priority",
                        type: "selection",
                        selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
                        default: 1,
                    },
                    state: {string: "State", type: "selection", selection: [["ab", "AB"], ["cd", "CD"], ["ef", "EF"]]},
                    date: {string: "Some Date", type: "date"},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                    product_ids: {string: "one2many product", type: "one2many", relation: "product"},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    bar: true,
                    foo: "yop",
                    int_field: 10,
                    qux: 0.44,
                    p: [],
                    timmy: [],
                    trululu: 4,
                    state: "ab",
                    date: "2017-01-25",
                    datetime: "2016-12-12 10:55:05",
                }, {
                    id: 2,
                    display_name: "second record",
                    bar: true,
                    foo: "blip",
                    int_field: 9,
                    qux: 13,
                    p: [],
                    timmy: [],
                    trululu: 1,
                    state: "cd",
                }, {
                    id: 3,
                    display_name: "Third record",
                    foo: "",
                    bar: true,
                    trululu: 2,

                }, {
                    id: 4,
                    display_name: "aaa",
                    state: "ef",
                }],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"},
                    partner_type_id: {string: "Partner type", type: "many2one", relation: "partner_type"},
                },
                records: [{
                    id: 37,
                    display_name: "xphone",
                }, {
                    id: 41,
                    display_name: "xpad",
                }, {
                    id: 42,
                    display_name: "xtab",
                },{
                    id: 43,
                    display_name: "xelec",
                },{
                    id: 44,
                    display_name: "xtrimemer",
                },{
                    id: 45,
                    display_name: "xipad",
                },{
                    id: 46,
                    display_name: "xphone1",
                },{
                    id: 47,
                    display_name: "xphone2",
                },{
                    id: 48,
                    display_name: "xphone3",
                },{
                    id: 59,
                    display_name: "xphone4",
                },{
                    id: 62,
                    display_name: "xphone5",
                },{
                    id: 69,
                    display_name: "xphone6",
                }]
            },
            partner_type: {
                fields: {
                    name: {string: "Partner Type", type: "char"},
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 12, display_name: "gold", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                ]
            },
        };
    }
}, function () {

    QUnit.module('FormView Keyboard');

    QUnit.test('m2o autocomplete when open and press escape, it should not discard form changes', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="product_id"/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.ok(form.$buttons.find(".o_form_buttons_edit").hasClass("o_hidden"), 'the record should be saved on pressing SHIFT + ENTER');
        form.$buttons.find('.o_form_button_edit').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        assert.strictEqual($dropdown.find('li:first()').text(), 'xphone', 'the click on m2o widget should open a dropdown');
        form.$('.o_field_many2one input').trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ESCAPE}));
        assert.ok(!form.$buttons.find(".o_form_buttons_edit").hasClass("o_hidden"), 'm2o autocomplete when open and press escape it should not discard form changes');
        assert.ok($(document.activeElement).hasClass('o_input'),
            "Focus should be set on input field");
        form.destroy();
    });

    QUnit.test('test dialog selectCreate popup, Form popup', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,search':
                    '<form string="Products">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="name"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
                'product,false,list': '<tree><field name="display_name"/></tree>'
            },
        });
        form.$buttons.find('.o_form_button_edit').click();
        var upkeyPress = $.Event("keydown", { keyCode: 38 });
        var enterkeyPress = $.Event("keydown", { keyCode: 13 });
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.trigger(upkeyPress);
        $dropdown.trigger(upkeyPress);
        $dropdown.trigger(enterkeyPress);
        assert.strictEqual($('.modal').length, 1,
            "One FormViewDialog should be opened");
        assert.ok($(document.activeElement).hasClass('o_searchview_input'),
            "Focus should be set on search view");
        var firstModel = $('.modal');
        $(firstModel).find('input[class="o_searchview_input"]').trigger($.Event("keyup", { which: $.ui.keyCode.DOWN }));
        assert.strictEqual($(document.activeElement).find('.o_row_selected').text(), 'xphone', 'the selected row must have the same name as shown view');
        var value = $(firstModel).find('.o_list_view li:first()').text();
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.ENTER })));
        assert.strictEqual($dropdown.val(), value, "the value should equal to the value that is selected from form dialog");
        form.destroy();
    });

    QUnit.test('keyboard navigation on form view', function(assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux" required="1"/>' +
                            '<field name="foo"/>' +
                            '<field name="trululu"/>' +
                            '<field name="state"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 3,
        });

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        assert.strictEqual($(document.activeElement).attr('name'),'qux',"First Element Focused");
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual(document.activeElement, form.$('input[name="qux"]')[0], "required field is empty and after pressing the TAB it should't leave the focus from current field");
        form.$('input[name="qux"]').val("qux");
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'),'foo',"Second Element Focused");
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).closest('.o_field_widget').attr('name'),'trululu',"Third Element Focused");
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'),'state',"Fourth Element Focused");
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).hasClass('o_form_button_save'),true,"Save button focused");
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB, shiftKey: true}));
        assert.strictEqual($(document.activeElement).attr('name'),'state',"Last Element Focused");
        form.destroy();
    });

    QUnit.test('escape key on all widget should show discard warning or call history_back', function(assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                            '<field name="foo"/>' +
                            '<field name="trululu"/>' +
                            '<field name="state"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').focus();

        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.strictEqual($(document.activeElement).hasClass('o_form_button_edit'),true,"data discard in float field");

        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).val("Hello").trigger('input');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.ok($('.modal').length, 'discard message show in char field');
        $('.modal .modal-footer .btn-primary').click();

        $(document.activeElement).trigger('click');
        form.$el.find('[name="qux"]').focus();
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.strictEqual($(document.activeElement).hasClass('o_form_button_edit'),true,"Data discard in many2one field");

        $(document.activeElement).trigger('click');
        form.$el.find('[name="state"]').focus();
        form.$el.find('[name="state"] option:eq(2)').prop('selected', true).trigger('change');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.ok($('.modal').length, 'discard message show in selection field');
        $('.modal .modal-footer .btn-primary').click();
        assert.strictEqual($(document.activeElement).hasClass('o_form_button_edit'),true,"data saved in selection field");

        form.destroy();
    });

    QUnit.test('save form view using shift enter', function(assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                            '<field name="foo"/>' +
                            '<field name="state"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.strictEqual($('.o_form_buttons_edit').hasClass('o_hidden'),true,"data saved in float field");

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.strictEqual($('.o_form_buttons_edit').hasClass('o_hidden'),true,"data saved in char field");

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger(jQuery.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.strictEqual($('.o_form_buttons_edit').hasClass('o_hidden'),true,"data saved in selection field");

        form.destroy();
    });

   QUnit.test('required field test and last field widget test', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo" required="1" />' +
                        '<field name="bar" />' +
                        '<field name="trululu" />' +
                '</form>',
            res_id: 3,
        });
        var tabKey = $.Event("keydown", { which: $.ui.keyCode.TAB });
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').trigger(tabKey);
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "required field is empty and after pressing the TAB it should't leave the focus from current field");
        form.$('input[name="foo"]').val("foooo");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).hasClass('btn-primary'), true,
            "focus shoud be on primary button after pressing the tab on last field");
        form.destroy();
    });

    QUnit.test('Basic fields test', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo" />' +
                        '<field name="bar" />' +
                        '<field name="int_field" />' +
                        '<field name="priority" />' +
                        '<field name="date" />' +
                        '<field name="datetime" />' +
                '</form>',
            res_id: 1,
        });
        var tabKey = $.Event("keydown", { which: $.ui.keyCode.TAB });
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').trigger(tabKey);
        assert.strictEqual($(document.activeElement).attr('type'), 'checkbox',
            "focus shoud be on checkbox");
        $(document.activeElement).click();
        assert.ok(!$(document.activeElement)[0].checked, "check box shoud unchecked after clicking on it");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement)[0], form.$('input[name="int_field"]')[0],
            "focus shoud be on int field");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement)[0], form.$('select[name="priority"]')[0],
            "focus shoud be on selection field");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement)[0], form.$('input[name="date"]')[0],
            "focus shoud be on date field");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement)[0], form.$('input[name="datetime"]')[0],
            "focus shoud be on datetime field");
        form.destroy();
    });

    QUnit.test('keyboard navigation on html field', function(assert) {
        assert.expect(2);

        var done = assert.async();

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="htmldata"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        concurrency.delay(0).then(function() { // content area of html field having timeout in summernote itself
            assert.strictEqual($(document.activeElement).hasClass('note-editable'),true,"next element is html field");
        });
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB , shiftKey : true }));
        concurrency.delay(0).then(function() { // content area of html field having timeout in summernote itself
            assert.strictEqual($(document.activeElement).hasClass('note-editable'),true,"previous element is html field");
        });
        concurrency.delay(0).then(function() { // content area of html field having timeout in summernote itself
            form.destroy();
            done();
        });
    });

    QUnit.test('tab and shift tab shoud change the focus on html field', function(assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="htmldata"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        $('.note-editable').focus();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'),"foo","tab shoud be change focus on next field");
        $('.note-editable').focus();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB, shiftKey : true }));
        assert.strictEqual($(document.activeElement).attr('name'),"display_name","tab shoud be change focus on previous field");

        concurrency.delay(0).then(function() { // content area of html field having timeout in summernote itself
            form.destroy();
        });
    });

    QUnit.test('navigation on header buttons in edit mode', function(assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="confirm" class="btn-primary confirm" string="Confirm"/>' +
                        '<button name="doit" class="btn-primary doit" string="Do it"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));

        assert.strictEqual($(document.activeElement).hasClass('o_form_button_save'),true,"Save button focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).hasClass('confirm'),true,"Confirm button focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).hasClass('doit'),true,"Do It button focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'),'display_name',"first button focused");

        form.destroy();
    });

    QUnit.test('navigation on header buttons in readonly mode', function(assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="confirm" class="btn-primary confirm" string="Confirm"/>' +
                        '<button name="doit" class="btn-primary doit" string="Do it"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$el.find('.confirm').focus();
        assert.strictEqual($(document.activeElement).hasClass('confirm'),true,"Confirm button focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).hasClass('doit'),true,"Do It button focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).hasClass('o_form_button_edit'),true,"Edit button focused");

        form.destroy();
    });

    QUnit.test('when press enter on create and edit it shoud open FormViewDialog', function (assert) {
        assert.expect(3);
        this.data.product.fields.product_ids = {
            string: "one2many product", type: "one2many", relation: "product",
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form':
                    '<form string="Products">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="name"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
            },
        });
        form.$buttons.find('.o_form_button_edit').click();
        var upKey = $.Event("keydown", { keyCode: 38 });
        var enterKey = $.Event("keydown", { keyCode: 13 });
        var tabKey = $.Event("keydown", { which: $.ui.keyCode.TAB });
        form.$el.find('.o_input_dropdown input').trigger(upKey);
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        $dropdown.trigger(upKey);
        $dropdown.trigger(enterKey);
        var firstModel = $('.modal-dialog');
        assert.strictEqual($(document.activeElement)[0], $(firstModel[0]).find('input[name="name"]')[0],
        "focus should be on first input field in FormViewDialog");
        $(document.activeElement).trigger(tabKey);
        assert.strictEqual($(document.activeElement)[0].innerText, 'SAVE',
        "if it is last element and tab pressed the focus should be on SAVE button");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement)[0], $(firstModel[0]).find('input[name="name"]')[0],
        "again focus should be on first input field");
        $(firstModel).trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
        concurrency.delay(100).then(function() { // content area of html field having timeout in summernote itself
            assert.ok($(document.activeElement).hasClass('o_input'), "focus should be on first input field after pressing the ESCAPE");
            form.destroy();
        });
    });

        QUnit.test('ESCAPE key with editable listview, it should discard editable listview record', function (assert) {
        assert.expect(4);
        this.data.partner.records[0].p = [1];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree default_order="foo desc" editable="bottom" >' +
                                '<field name="display_name"/>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                        '</field>' +
                        '<group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();
        form.$buttons.find('.o_form_button_save').trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.strictEqual($(document.activeElement)[0], $(".o_field_widget[name='display_name']")[0], "Focus should be on o2m input");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.ESCAPE })));
        assert.ok(!form.$buttons.find(".o_form_buttons_edit").hasClass("o_hidden"), 'o2m when press escape it should not discard form changes');
        assert.strictEqual($(document.activeElement).find('.o_list_view tbody').children().length, 4, "the number of rows should be 4");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        form.$buttons.find('.o_form_button_save').trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        $(document.activeElement).val('suh');
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.strictEqual($(document.activeElement).val(), 'My little Foo Value', "The focus should be on next editable field");
        form.destroy();
    });

    QUnit.test('O2m check dialog form popup, close and check behaviour of o2m field when it is empty and non empty when TAB is pressed', function (assert) {
        assert.expect(6);
        this.data.partner.records[0].p = [1];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<field name="p">' +
                            '<tree default_order="foo desc">' +
                                '<field name="display_name"/>' +
                                '<field name="foo"/>' +
                                '</tree>' +
                        '</field>' +
                        '<group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
            },
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();
        assert.ok($(document.activeElement).hasClass('ui-autocomplete-input'), "Focus should be on m2o widget");
        assert.strictEqual($(document.activeElement).val(), '', 'the input should not have any value');
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.strictEqual($('.modal').length, 1,
            "One FormViewDialog should be opened");
        assert.ok($(document.activeElement).hasClass('o_field_widget'),
            "Focus should be on input of FormViewDialog");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.ok($(document.activeElement).hasClass('o_form_button_save'),
            "Focus should be on save button of FormViewDialog");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        //the the tab key should work on primary button
        $('.modal .modal-footer').children()[1].focus();
        assert.strictEqual(document.activeElement, $('.modal .modal-footer').children()[1], "Focus should be on save & new button of FormViewDialog");
        $('.modal').trigger(($.Event("keydown", { which: $.ui.keyCode.ESCAPE})));
        concurrency.delay(100).then(function() {
            assert.ok($(document.activeElement).hasClass('o_field_one2many'), "focus should be on first input field after pressing the ESCAPE");
            form.destroy();
        });
    });
});

});
