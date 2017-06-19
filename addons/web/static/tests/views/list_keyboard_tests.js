odoo.define('web.list_keyboard_tests', function (require) {
"use strict";

var config = require('web.config');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    date: {string: "Some Date", type: "date"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "my float", type: "float"},
                    m2o: {string: "M2O field", type: "many2one", relation: "bar"},
                    m2m: {string: "M2M field", type: "many2many", relation: "bar"},
                    amount: {string: "Monetary field", type: "monetary"},
                    currency_id: {string: "Currency", type: "many2one",
                                  relation: "res_currency", default: 1},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                },
                records: [
                    {
                        id: 1,
                        bar: true,
                        foo: "yop",
                        int_field: 10,
                        qux: 0.4,
                        m2o: 1,
                        m2m: [1, 2],
                        amount: 1200,
                        currency_id: 2,
                        date: "2017-01-25",
                        datetime: "2016-12-12 10:55:05",
                    },
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13,
                     m2o: 2, m2m: [1, 2, 3], amount: 500},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3,
                     m2o: 1, m2m: [], amount: 300},
                    {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9,
                     m2o: 1, m2m: [1], amount: 0},
                ]
            },
            bar: {
                fields: {},
                records: [
                    {id: 1, display_name: "Value 1"},
                    {id: 2, display_name: "Value 2"},
                    {id: 3, display_name: "Value 3"},
                ]
            },
            res_currency: {
                fields: {
                    symbol: {string: "Symbol", type: "char"},
                    position: {
                        string: "Position",
                        type: "selection",
                        selection: [['after', 'A'], ['before', 'B']],
                    },
                },
                records: [
                    {id: 1, display_name: "USD", symbol: '$', position: 'before'},
                    {id: 2, display_name: "EUR", symbol: '€', position: 'after'},
                ],
            },
            event: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "name", type: "char"},
                },
                records: [
                    {id: "2-20170808020000", name: "virtual"},
                ]
            },
        };
    }
}, function () {

    QUnit.module('ListView Keyboard');


});

});