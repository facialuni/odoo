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
            $(document.activeElement).trigger(e);
        };

        var $firstRecord = list.$el.find('.o_data_row').first();
        $firstRecord.find('input').trigger('click').focus();

        assert.ok($firstRecord.hasClass('o_row_selected'),'First record selected');

        // Press down key will select next record
        $firstRecord.find('input').trigger($.Event('keydown', {which: $.ui.keyCode.DOWN}));
        var $lastActiveRow = $firstRecord;
        assert.ok(!$firstRecord.hasClass('o_row_selected'), 'First record unselected');
        assert.ok($($lastActiveRow.next()).hasClass('o_row_selected'), 'Second record selected');

        // On shift + down select currrent and next record
        shiftKeyPress(40);
        $lastActiveRow = $lastActiveRow.next();
        assert.ok($($lastActiveRow,$lastActiveRow.next()).hasClass('o_row_selected'), "Select currrent and next record");

        // On Ctrl + down will transfer focus to next record but don't select it
        controlKeyPress(40);
        $lastActiveRow = $lastActiveRow.next();
        assert.ok($($lastActiveRow.next()).hasClass('o_row_focused'), "Next record is focused");

        // On Ctrl + up will transfer focus to previous record but don't select it
        controlKeyPress(38);
        assert.ok($lastActiveRow.hasClass('o_row_focused'), "Previous record is focused");

        // On shift + up unselect previous record
        $lastActiveRow = $lastActiveRow.prev();
        shiftKeyPress(38);
        assert.ok(!$($lastActiveRow).hasClass('o_row_selected'), "Unselect previous record");
        $lastActiveRow = $lastActiveRow.prev();

        // On up(arrow) key it will select previous record
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.UP}));
        assert.ok($($lastActiveRow).hasClass('o_row_selected'), "Select previous record");

        list.destroy();
    });
});

});
