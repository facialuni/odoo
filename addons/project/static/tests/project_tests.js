odoo.define('project.project_kanban_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('project', {
    beforeEach: function () {
        this.data = {
            'ir.attachment': {
                fields: {
                    name: {
                        string: "Name",
                        type: "char"
                    },
                },
                records: [{
                        id: 1,
                        name: "1.png"
                    },
                    {
                        id: 2,
                        name: "2.png"
                    },
                ]
            },
            'project.task': {
                fields: {
                    name: {
                        string: "Task Title",
                        type: "char"
                    },
                    sequence: {
                        string: "sequence",
                        type: "integer"
                    },
                    displayed_image_id: {
                        string: "cover",
                        type: "many2one",
                        relation: "ir.attachment"
                    },
                    kanban_state: {
                        string: "State",
                        type: "selection",
                        selection: [
                            ["normal", "In Dev"],
                            ["done", "Dev Done"],
                            ["blocked", "Need Help"]
                        ]
                    },
                    product_id: {
                        string: "something_id",
                        type: "many2one",
                        relation: "product"
                    },
                },
                records: [
                    {id: 1, name: "task1 fix", sequence: 1, kanban_state: "blocked", product_id: 3},
                    {id: 2, name: "task2 issue", sequence: 2, kanban_state: "done", product_id: 3},
                    {id: 3, name: "task3 improvement", sequence: 2, kanban_state: "done", product_id: 5},
                    {id: 4, name: "task4 clone", sequence: 2, kanban_state: "normal", product_id: 5}
                ]
            },
            product: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "Display Name", type: "char"},
                },
                records: [
                    {id: 3, name: "chagan"},
                    {id: 5, name: "magan"},
                ]
            },
        };
    }
});

QUnit.test('cover_image_test', function (assert) {
    assert.expect(6);
    var kanban = createView({
        View: KanbanView,
        model: 'project.task',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                            '<div class="o_dropdown_kanban dropdown">' +
                                '<a class="dropdown-toggle btn" data-toggle="dropdown" href="#">' +
                                    '<span class="fa fa-bars fa-lg"/>' +
                                '</a>' +
                                '<ul class="dropdown-menu" role="menu" aria-labelledby="dLabel">' +
                                    '<li>' +
                                        '<a type="set_cover">Set Cover Image</a>'+
                                    '</li>' +
                                '</ul>' +
                            '</div>' +
                            '<div>'+
                                '<field name="displayed_image_id" widget="attachment_image"/>'+
                            '</div>'+
                        '</div>' +
                    '</t>' +
                '</templates>' +
            '</kanban>',
        mockRPC: function(route, args) {
            if (args.model === 'ir.attachment' && args.method === 'search_read') {
                return $.when([{
                    id: 1,
                    name: "1.png"
                },{
                    id: 2,
                    name: "2.png"
                }]);
            }
            if (args.model === 'project.task' && args.method === 'write') {
                assert.step(args.args[0][0]);
                return this._super(route, args);
            }
            return this._super(route, args);
        },
    });
    assert.strictEqual(kanban.$('img').length, 0, "Initially there is no image.");
    kanban.$('.o_dropdown_kanban [data-type=set_cover]').eq(0).click();
    // single click on image
    $('.modal').find("img[data-id='1']").click();
    $('.modal-footer .btn-primary').click();
    assert.strictEqual(kanban.$('img[src*="/web/image/1"]').length, 1, "Image inserted in record");
    $('.o_dropdown_kanban [data-type=set_cover]').eq(1).click();
    // double click on image
    $('.modal').find("img[data-id='2']").dblclick();
    assert.strictEqual(kanban.$('img[src*="/web/image/2"]').length, 1, "Image inserted after double click");
    // varify write on both kanban record
    assert.verifySteps([1,2]);
    kanban.destroy();
});

QUnit.test('Project Kanban Progress Bar Test', function (assert) {
    assert.expect(3);
    var kanban = createView({
        View: KanbanView,
        model: 'project.task',
        data: this.data,
        arch: '<kanban on_create="quick_create">' +
                    '<field name="product_id"/>' +
                    "<progressbar field='kanban_state' colors='{\"done\": \"success\", \"blocked\": \"danger\"}'/>" +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="name"/><br/>' +
                        '<field name="kanban_state" widget="state_selection"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
        groupBy: ['product_id'],
    });
    kanban.appendTo('body');
    assert.strictEqual(kanban.$('.o_kanban_counter').length,this.data.product.records.length, "Kanban counter should be created.");
    var record_length = kanban.$('.o_kanban_group')[0];
    assert.strictEqual(parseInt(kanban.$('.o_kanban_counter_side')[0].innerText), kanban.$('.o_kanban_group')[0].childNodes.length - 5, "Kanban counter should be display correct no of records");
    kanban.$('.o_progress_success')[0].click();
    assert.strictEqual(kanban.$('.oe_kanban_card_danger').css('opacity'),'0.5', "Kanban Record Opacity should be decrease");
    kanban.destroy();
});

});