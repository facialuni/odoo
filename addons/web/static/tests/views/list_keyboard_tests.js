odoo.define('web.list_keyboard_tests', function (require) {
"use strict";

var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [
                    {name: "Tyrion Lannister",},
                    {name: "Oliver Queen"},
                    {name: "Michael Scofield"},
                    {name: "Barry Allen"},
                    {name: "Bruce Wayne"},
                    {name: "Andrew Lincoln"},
                ]
            },
        };
    }
}, function () {

    QUnit.module('ListView Keyboard');

    QUnit.test('Listview selection', function (assert) {
        assert.expect(8);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
        });

        var shiftKeyPress = function (direction) {
            var e = $.Event("keydown");
            e.which = direction;
            e.shiftKey = true;
            $firstRecord.find('input').trigger(e);
        };

        var controlKeyPress = function (direction) {
            var e = $.Event("keydown");
            e.which = direction;
            e.ctrlKey = true;
            var $activeElement = getActiveRow();
            $activeElement.find('input').trigger(e);
        };

        var getActiveRow = function () {
            return $(document.activeElement).closest('.o_data_row');
        };

        var upDownKey = function (direction) {
            var e = $.Event("keydown");
            e.which = direction;
            return e;
        }

        var lastActiveRow;
        $('.o_data_row input').on('blur', function(e){
            lastActiveRow = $(e.currentTarget).closest('.o_data_row');
        });

        var $firstRecord = list.$el.find('.o_data_row').first();
        $firstRecord.find('input').trigger('click').focus();

        assert.ok($firstRecord.hasClass('o_row_selected'),'First record selected');

        // Press down key will select next record
        $firstRecord.find('input').trigger(upDownKey(40));
        assert.ok(!$firstRecord.hasClass('o_row_selected'), 'First record unselected');
        assert.ok($(lastActiveRow.next()).hasClass('o_row_selected'), 'Second record selected');

        // On shift + down select currrent and next record
        shiftKeyPress(40);
        assert.ok($(lastActiveRow,lastActiveRow.next()).hasClass('o_row_selected'), "Select currrent and next record");

        // On Ctrl + down will transfer focus to next record but don't select it
        controlKeyPress(40);
        assert.ok($(lastActiveRow.next()).hasClass('o_row_focused'), "Next record is focused");

        // On Ctrl + up will transfer focus to previous record but don't select it
        controlKeyPress(38);
        assert.ok($(lastActiveRow.prev()).hasClass('o_row_focused'), "previous record is focused");

        // On shift + up unselect previous record
        shiftKeyPress(38);
        assert.ok(!$(lastActiveRow.prev()).hasClass('o_row_selected'), "Unselect previous record");

        // On up(arrow) key it will select previous record
        var $activeElement = getActiveRow();
        $activeElement.find('input').trigger(upDownKey(38));
        assert.ok($(lastActiveRow.prev()).hasClass('o_row_selected'), "Select previous record");

        list.destroy();
    });
});

});
