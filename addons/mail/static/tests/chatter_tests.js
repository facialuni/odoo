odoo.define('mail.chatter_tests', function (require) {
"use strict";

var Composers = require('mail.composer');

var Bus = require('web.Bus');
var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var BasicComposer = Composers.BasicComposer;

var createView = testUtils.createView;

QUnit.module('mail', {}, function () {

QUnit.module('Chatter', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    message_follower_ids: {
                        string: "Followers",
                        type: "one2many",
                        relation: 'mail.followers',
                        relation_field: "res_id"
                    },
                    message_ids: {
                        string: "messages",
                        type: "one2many",
                        relation: 'mail.message',
                        relation_field: "res_id",
                    },
                    activity_ids: {
                        string: 'Activities',
                        type: 'one2many',
                        relation: 'mail.activity',
                        relation_field: 'res_id',
                    },
                    activity_state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                },
                records: [{
                    id: 2,
                    display_name: "first partner",
                    foo: "HELLO",
                    message_follower_ids: [],
                    message_ids: [],
                    activity_ids: [],
                }]
            },
            'mail.message':{
                fields: {
                    attachment_ids: {
                        string: 'Attachments',
                        type: 'many2many',
                        relation: 'ir.attachment',
                    },
                },
            },
            'ir.attachment': {
                fields: {
                    name: { string: "Name", type: "char"},
                    datas_fname: { string: "File name", type: "char"},
                    datas: { type: "base64"},
                    mimetype: {type: "char"},
                },
            },
            'mail.activity': {
                fields: {
                    activity_type_id: { string: "Activity type", type: "many2one", relation: "mail.activity.type" },
                    create_uid: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                },
            },
            'mail.activity.type': {
                fields: {
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 1, name: "Type 1" },
                    { id: 2, name: "Type 2" },
                ],
            }
        };
    }
});

QUnit.test('basic rendering', function (assert) {
    assert.expect(9);

    var count = 0;
    var unwanted_read_count = 0;
    // var msgRpc = 0;

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if ('/web/dataset/call_kw/mail.followers/read' === route) {
                unwanted_read_count++;
            }
            if (route === '/mail/read_followers') {
                count++;
                return $.when({
                    followers: [],
                    subtypes: [],
                });
            }
            return this._super(route, args);
        },
        intercepts: {
            get_messages: function (event) {
                // msgRpc++;
                event.stopPropagation();
                event.data.callback($.when([{
                    attachment_ids: [{
                        id: 34,
                        name: "test1",
                        datas_fname: "test1.jpeg",
                        datas:"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAeAB4AAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAGXAmMDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9/KKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKDwDRQRkUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUdKKOtABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRR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nd+RhTw8qUnGWzbf36v13uvK3Q/V7/g9c+Pfww8afEn4S+BNHn0vVPin4RS9uddmtGV5tIsZ1iMFpcMp4d2VpVjb5kU78KJgX4n/AIMnfhvrGr/t2/FTxZAso0HQvBA0y8cZ8s3F1fQSQKeeu20nI4/hPTv8C/sW/wDBFn9pn9vTXtEi8C/CfxTB4f12JLuHxVrllLpXh5bUypG1wt5MoSdVL7ilv5srKjlI32kV/Vb/AMEgv+CV/hP/AIJK/soW3gDQrx9c1/Vbgap4m12SPy21W+MaoSi/8s4EVQsaZOBkklmYm8vo/VI1Kk3rLmsttZLlenRJXfnLzbIx1X6zyU4LRcuu+kXzb9W3suifkr/VNeSft+f8mKfGj/sRdb/9IJ69bry/9tzw/f8Aiz9jL4t6XpVld6nqepeDNYtbSztYWmnupnsplSONFBZ3ZiAFAJJIAryc0TeCrJfyy/JnpZc0sXSb/mj+aP4bPh1/yUHQv+wjb/8Ao1a/vesP+PGD/rmv8q/id8Bf8Epv2o7Pxzos037Nvx8iiiv4Hd3+H2rKqKJFJJJt+ABX9sVkpSyhBBBCKCD24r3ZtfU4L+9L8oHjJP623/dX5slooorhO0KKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKOlFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFB5FFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFB6Gig8g0AFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFIXUHBIH40eYv95fzoAWik8xf7y/nR5i/wB5fzoAWik8xf7y/nR5i/3l/OgBaKTzF/vL+dHmL/eX86AFopPMX+8v50eYv95fzoAWik8xf7y/nR5i/wB5fzoAWik8xf7y/nR5i/3l/OgBaKTzF/vL+dHmL/eX86AFopPMX+8v50eYv95fzoAWik8xf7y/nR5i/wB5fzoAWik8xf7y/nR5i/3l/OgBaKTzF/vL+dHmL/eX86AFopPMX+8v50eYv95fzoAWik8xf7y/nR5i/wB5fzoAWik8xf7y/nR5i/3l/OgBaKTzF/vL+dHmL/eX86AFopPMX+8v50eYv95fzoAWik8xf7y/nR5i/wB5fzoAWik8xf7y/nR5i/3l/OgBaKTzF/vL+dHmL/eX86AFopAwboQaWgAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigCtcf640yn3H+uNMoAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAJrb+L8KmqG2/i/CpqACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAK1x/rjTKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigCa2/i/CpqKKACiiigAooooA//Z",
                        mimetype: "image/jpeg",
                    }],
                    body: "",
                    date: moment("2016-12-20 09:35:40"),
                    id: 34,
                    res_id: 3,
                    author_id: ["3", "Fu Ck Mil Grom"],
                }]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
            get_session: function (event) {
                event.stopPropagation();
                event.data.callback({uid: 1});
            },
        },
    });

    assert.ok(form.$('.o_mail_activity').length, "there should be an activity widget");
    assert.ok(form.$('.o_chatter_topbar .o_chatter_button_schedule_activity').length,
        "there should be a 'Schedule an activity' button in the chatter's topbar");
    assert.ok(form.$('.o_chatter_topbar .o_followers').length,
        "there should be a followers widget, moved inside the chatter's topbar");
    assert.ok(form.$('.o_chatter').length, "there should be a chatter widget");
    assert.ok(form.$('.o_mail_thread').length, "there should be a mail thread");
    assert.ok(!form.$('.o_chatter_topbar .o_chatter_button_log_note').length,
        "log note button should not be available");
    // assert.strictEqual(msgRpc, 1, "should have fetched messages once");

    form.$buttons.find('.o_form_button_edit').click();
    // assert.strictEqual(msgRpc, 1, "should still have fetched messages only once");
    assert.strictEqual(count, 0, "should have done no read_followers rpc as there are no followers");
    assert.strictEqual(unwanted_read_count, 0, "followers should only be fetched with read_followers route");
    form.$('.o_attachment_popup').click();
    return concurrency.delay(200).then(function () {
        assert.ok($('.o_attachment_carousel').length, "on clicking attachments image should be popuped");
    });
    form.destroy();
});

QUnit.test('chatter is not rendered in mode === create', function (assert) {
    assert.expect(4);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            return this._super(route, args);
        },
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when([]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
        },
    });

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    form.$buttons.find('.o_form_button_create').click();

    assert.strictEqual(form.$('.o_chatter').length, 0,
        "chatter should not be displayed");

    form.$('.o_field_char').val('coucou').trigger('input');
    form.$buttons.find('.o_form_button_save').click();

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    // check if chatter buttons still work
    form.$('.o_chatter_button_new_message').click();
    assert.strictEqual(form.$('.o_chat_composer:visible').length, 1,
        "chatter should be opened");

    form.destroy();
});

QUnit.test('kanban activity widget with no activity', function (assert) {
    assert.expect(4);

    var rpcCount = 0;
    var kanban = createView({
        View: KanbanView,
        model: 'partner',
        data: this.data,
        arch: '<kanban>' +
                    '<field name="activity_state"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="activity_ids" widget="kanban_activity"/></div>' +
                    '</t></templates>' +
                '</kanban>',
        mockRPC: function (route, args) {
            rpcCount++;
            return this._super(route, args);
        },
        session: {uid: 2},
    });

    var $record = kanban.$('.o_kanban_record').first();
    assert.ok($record.find('.o_mail_activity .o_activity_color_default').length,
        "activity widget should have been rendered correctly");
    assert.strictEqual(rpcCount, 1, '1 RPC (search_read) should have been done');

    // click on the activity button
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 1, 'no RPC should have been done as there is no activity');
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    // fixme: it would be nice to be able to test the scheduling of a new activity, but not
    // possible for now as we can't mock a fields_view_get (required by the do_action)
    kanban.destroy();
});

QUnit.test('kanban activity widget with an activity', function (assert) {
    assert.expect(11);

    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 1,
    }];
    var rpcCount = 0;
    var kanban = createView({
        View: KanbanView,
        model: 'partner',
        data: this.data,
        arch: '<kanban>' +
                    '<field name="activity_state"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="activity_ids" widget="kanban_activity"/></div>' +
                    '</t></templates>' +
                '</kanban>',
        mockRPC: function (route, args) {
            rpcCount++;
            if (route === '/web/dataset/call_kw/mail.activity/action_done') {
                var current_ids = this.data.partner.records[0].activity_ids;
                var done_ids = args.args[0];
                this.data.partner.records[0].activity_ids = _.difference(current_ids, done_ids);
                this.data.partner.records[0].activity_state = false;
                return $.when();
            }
            return this._super(route, args);
        },
        session: {uid:2},
    });

    var $record = kanban.$('.o_kanban_record').first();
    assert.ok($record.find('.o_mail_activity .o_activity_color_today').length,
        "activity widget should have been rendered correctly");
    assert.strictEqual(rpcCount, 1, '1 RPC (search_read) should have been done');

    // click on the activity button
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 2, 'a read should have been done to fetch the activity details');
    assert.strictEqual($record.find('.o_activity_title').length, 1, "should have an activity scheduled");
    var label_text = $record.find('.o_activity_label .o_activity_color_today').text();
    assert.ok(label_text.indexOf('Today (1)') >= 0, "should display the correct label and count");

    // click on the activity button to close the dropdown
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 2, 'no RPC should be done when closing the dropdown');

    // click on the activity button to re-open dropdown
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 2, 'no RPC should be done as the activities are now in cache');

    // mark activity as done
    $record.find('.o_mark_as_done').click();
    $record = kanban.$('.o_kanban_record').first(); // the record widget has been reset
    assert.strictEqual(rpcCount, 4, 'should have done an RPC to mark activity as done, and a read');
    assert.ok($record.find('.o_mail_activity .o_activity_color_default:not(.o_activity_color_today)').length,
        "activity widget should have been updated correctly");
    assert.strictEqual($record.find('.o_mail_activity.open').length, 1,
        "dropdown should remain open when marking an activity as done");
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    kanban.destroy();
});

QUnit.test('chatter: post, receive and star messages', function (assert) {
    var done = assert.async();
    assert.expect(27);

    // Remove the mention throttle to speed up the test
    var mentionThrottle = BasicComposer.prototype.MENTION_THROTTLE;
    BasicComposer.prototype.MENTION_THROTTLE = 1;

    this.data.partner.records[0].message_ids = [1];
    var messages = [{
        attachment_ids: [],
        author_id: ["1", "John Doe"],
        body: "A message",
        date: moment("2016-12-20 09:35:40"),
        displayed_author: "John Doe",
        id: 1,
        is_note: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];
    var bus = new Bus();
    var getSuggestionsDef = $.Deferred();
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'message_get_suggested_recipients') {
                return $.when({2: []});
            }
            if (args.method === 'get_mention_suggestions') {
                getSuggestionsDef.resolve();
                return $.when([{email: "test@odoo.com", id: 1, name: "Test User"}]);
            }
            return this._super(route, args);
        },
        session: {},
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                var requested_msgs = _.filter(messages, function (msg) {
                    return _.contains(event.data.options.ids, msg.id);
                });
                event.data.callback($.when(requested_msgs));
            },
            post_message: function (event) {
                event.stopPropagation();
                var msg_id = messages[messages.length-1].id + 1;
                messages.push({
                    attachment_ids: [],
                    author_id: ["42", "Me"],
                    body: event.data.message.content,
                    date: moment(), // now
                    displayed_author: "Me",
                    id: msg_id,
                    is_note: event.data.message.subtype === 'mail.mt_note',
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                bus.trigger('new_message', {
                    id: msg_id,
                    model: event.data.options.model,
                    res_id: event.data.options.res_id,
                });
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(bus);
            },
            toggle_star_status: function (event) {
                event.stopPropagation();
                assert.strictEqual(event.data.message_id, 2,
                    "toggle_star_status should have been triggered for message 2 (twice)");
                var msg = _.findWhere(messages, {id: event.data.message_id});
                msg.is_starred = !msg.is_starred;
                bus.trigger('update_message', msg);
            },
        },
    });

    assert.ok(form.$('.o_chatter_topbar .o_chatter_button_log_note').length,
        "log note button should be available");
    assert.strictEqual(form.$('.o_thread_message').length, 1, "thread should contain one message");
    assert.ok(!form.$('.o_thread_message:first() .o_mail_note').length,
        "the message shouldn't be a note");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('A message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('John Doe') >= 0,
        "the message's author should be correct");

    // send a message
    form.$('.o_chatter_button_new_message').click();
    assert.ok(!$('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be opened");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.ok($('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be closed");
    assert.strictEqual(form.$('.o_thread_message').length, 2, "thread should contain two messages");
    assert.ok(!form.$('.o_thread_message:first() .o_mail_note').length,
        "the last message shouldn't be a note");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('Me') >= 0,
        "the message's author should be correct");

    // log a note
    form.$('.o_chatter_button_log_note').click();
    assert.ok(!$('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be opened");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first note");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.ok($('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be closed");
    assert.strictEqual(form.$('.o_thread_message').length, 3, "thread should contain three messages");
    assert.ok(form.$('.o_thread_message:first() .o_mail_note').length,
        "the last message should be a note");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first note') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('Me') >= 0,
        "the message's author should be correct");

    // star message 2
    assert.ok(form.$('.o_thread_message[data-message-id=2] .o_thread_message_star.fa-star-o').length,
        "message 2 should not be starred");
    form.$('.o_thread_message[data-message-id=2] .o_thread_message_star').click();
    assert.ok(form.$('.o_thread_message[data-message-id=2] .o_thread_message_star.fa-star').length,
        "message 2 should be starred");

    // unstar message 2
    form.$('.o_thread_message[data-message-id=2] .o_thread_message_star').click();
    assert.ok(form.$('.o_thread_message[data-message-id=2] .o_thread_message_star.fa-star-o').length,
        "message 2 should not be starred");

    // very basic test of mention
    form.$('.o_chatter_button_new_message').click();
    var $input = form.$('.oe_chatter .o_composer_text_field:first()');
    $input.val('@');
    // the cursor position must be set for the mention manager to detect that we are mentionning
    $input[0].selectionStart = 1;
    $input[0].selectionEnd = 1;
    $input.trigger('keyup');

    assert.strictEqual(getSuggestionsDef.state(), "pending",
        "the mention suggestion RPC should be throttled");

    getSuggestionsDef
        .then(concurrency.delay.bind(concurrency, 0))
        .then(function () {
            assert.strictEqual(form.$('.o_mention_proposition:visible').length, 1,
                "there should be one mention suggestion");
            assert.strictEqual(form.$('.o_mention_proposition').data('id'), 1,
                "suggestion's id should be correct");
            assert.strictEqual(form.$('.o_mention_proposition .o_mention_name').text(), 'Test User',
                "suggestion should be displayed correctly");
            assert.strictEqual(form.$('.o_mention_proposition .o_mention_info').text(), '(test@odoo.com)',
                "suggestion should be displayed correctly");

            BasicComposer.prototype.MENTION_THROTTLE = mentionThrottle;
            form.destroy();
            done();
        });
});

QUnit.test('form activity widget: schedule next activity', function (assert) {
    assert.expect(4);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 2,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_done') {
                assert.ok(_.isEqual(args.args[0], [1]), "should call 'action_done' for id 1");
                assert.strictEqual(args.kwargs.feedback, 'everything is ok',
                    "the feedback should be sent correctly");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when([]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
            do_action: function (event) {
                assert.deepEqual(event.data.action, {
                    context: {
                        default_res_id: 2,
                        default_res_model: "partner",
                        default_previous_activity_type_id: 2,
                    },
                    res_id: false,
                    res_model: 'mail.activity',
                    type: 'ir.actions.act_window',
                    target: "new",
                    view_mode: "form",
                    view_type: "form",
                    views: [[false, "form"]],
                }, "should do a do_action with correct parameters");
            },
        },
    });
    //Schedule next activity
    form.$('.o_mail_activity .o_activity_done[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 1,
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    form.$('.o_activity_popover_done_next').click(); // schedule next activity
    form.destroy();
});

QUnit.test('form activity widget: mark as done and remove', function (assert) {
    assert.expect(14);

    var self = this;

    var nbReads = 0;
    var messages = [];
    this.data.partner.records[0].activity_ids = [1, 2];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 1,
    }, {
        id: 2,
        display_name: "A second activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 1,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                assert.ok(_.isEqual(args.args[0], [1]), "should call 'unlink' for id 1");
            } else if (route === '/web/dataset/call_kw/mail.activity/action_done') {
                assert.ok(_.isEqual(args.args[0], [2]), "should call 'action_done' for id 2");
                assert.strictEqual(args.kwargs.feedback, 'everything is ok',
                    "the feedback should be sent correctly");
                // should generate a message and unlink the activity
                self.data.partner.records[0].message_ids = [1];
                messages.push({
                    attachment_ids: [],
                    author_id: ["1", "John Doe"],
                    body: "The activity has been done",
                    date: moment("2016-12-20 09:35:40"),
                    displayed_author: "John Doe",
                    id: 1,
                    is_note: true,
                });
                route = '/web/dataset/call_kw/mail.activity/unlink';
                args.method = 'unlink';
            } else if (route === '/web/dataset/call_kw/partner/read') {
                nbReads++;
                if (nbReads === 1) { // first read
                    assert.strictEqual(args.args[1].length, 4, 'should read all fiels the first time');
                } else if (nbReads === 2) { // second read: after the unlink
                    assert.ok(_.isEqual(args.args[1], ['activity_ids']),
                        'should only read the activities after an unlink');
                } else { // third read: after marking an activity done
                    assert.ok(_.isEqual(args.args[1], ['activity_ids', 'message_ids']),
                        'should read the activities and messages after marking an activity done');
                }
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when(messages));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            }
        },
    });

    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 2,
        "there should be two activities");

    // remove activity 1
    form.$('.o_mail_activity .o_activity_unlink[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "there should be one remaining activity");
    assert.ok(!form.$('.o_mail_activity .o_activity_unlink[data-activity-id=1]').length,
        "activity 1 should have been removed");

    // mark activity done
    assert.ok(!form.$('.o_mail_thread .o_thread_message').length,
        "there should be no chatter message");
    form.$('.o_mail_activity .o_activity_done[data-activity-id=2]').click();
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 1,
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    form.$('.o_activity_popover_done').click(); // send feedback
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 0,
        "the feedback popover should be closed");
    assert.ok(!form.$('.o_mail_activity .o_thread_message').length,
        "there should be no more activity");
    assert.strictEqual(form.$('.o_mail_thread .o_thread_message').length, 1,
        "a chatter message should have been generated");
    form.destroy();
});

QUnit.test('followers widget: follow/unfollow, edit subtypes', function (assert) {
    assert.expect(24);

    var resID = 2;
    var partnerID = 1;
    var followers = [];
    var nbReads = 0;
    var subtypes = [
        {id: 1, name: "First subtype", followed: true},
        {id: 2, name: "Second subtype", followed: true},
        {id: 3, name: "Third subtype", followed: false},
    ];
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                '</div>' +
            '</form>',
        res_id: resID,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/partner/message_subscribe') {
                assert.strictEqual(args.args[0][0], resID, 'should call route for correct record');
                assert.ok(_.isEqual(args.kwargs.partner_ids, [partnerID]),
                    'should call route for correct partner');
                if (args.kwargs.subtype_ids) {
                    // edit subtypes
                    assert.ok(_.isEqual(args.kwargs.subtype_ids, [1]),
                        'should call route with the correct subtypes');
                    _.each(subtypes, function (subtype) {
                        subtype.followed = _.contains(args.kwargs.subtype_ids, subtype.id);
                    });
                    // hack: the server creates a new follower each time the subtypes are updated
                    // so we need here to mock that weird behavior here, as the followers widget
                    // relies on that behavior
                    this.data.partner.records[0].message_follower_ids = [2];
                    followers[0].id = 2;
                } else {
                    // follow
                    this.data.partner.records[0].message_follower_ids = [1];
                    followers.push({
                        id: 1,
                        is_uid: true,
                        name: "Admin",
                        email: "admin@example.com",
                        res_id: resID,
                        res_model: 'partner',
                    });
                }
                return $.when(true);
            }
            if (route === '/mail/read_followers') {
                return $.when({
                    followers: followers,
                    subtypes: subtypes,
                });
            }
            if (route === '/web/dataset/call_kw/partner/message_unsubscribe') {
                assert.strictEqual(args.args[0][0], resID, 'should call route for correct record');
                assert.ok(_.isEqual(args.args[1], [partnerID]), 'should call route for correct partner');
                this.data.partner.records[0].message_follower_ids = [];
                followers = [];
                return $.when(true);
            }
            if (route === '/web/dataset/call_kw/partner/read') {
                nbReads++;
                if (nbReads === 1) { // first read: should read all fields
                    assert.strictEqual(args.args[1].length, 3,
                        'should read "foo", "message_follower_ids" and "display_name"');
                } else { // three next reads: only read 'message_follower_ids' field
                    assert.ok(_.isEqual(args.args[1], ['message_follower_ids']),
                        'should only read "message_follower_ids"');
                }
            }
            return this._super.apply(this, arguments);
        },
        session: {partner_id: partnerID},
    });

    assert.strictEqual(form.$('.o_followers_count').text(), "0", 'should have no followers');
    assert.ok(form.$('.o_followers_follow_button.o_followers_notfollow').length,
        'should display the "Follow" button');

    // click to follow the document
    form.$('.o_followers_follow_button').click();
    assert.strictEqual(form.$('.o_followers_count').text(), "1", 'should have one follower');
    assert.ok(form.$('.o_followers_follow_button.o_followers_following').length,
        'should display the "Following/Unfollow" button');
    assert.strictEqual(form.$('.o_followers_list .o_partner').length, 1,
        "there should be one follower in the follower dropdown");

    // edit the subtypes
    assert.strictEqual(form.$('.o_subtypes_list .o_subtype').length, 3,
        'subtype list should contain 3 subtypes');
    assert.strictEqual(form.$('.o_subtypes_list .o_subtype_checkbox:checked').length, 2,
        'two subtypes should be checked by default');
    form.$('.o_subtypes_list .dropdown-toggle').click(); // click to open the dropdown
    assert.ok(form.$('.o_subtypes_list.open').length, 'dropdown should be opened');
    form.$('.o_subtypes_list .o_subtype input[data-id=2]').click(); // uncheck second subtype
    assert.ok(form.$('.o_subtypes_list.open').length, 'dropdown should remain opened');
    assert.ok(!form.$('.o_subtypes_list .o_subtype_checkbox[data-id=2]:checked').length,
        'second subtype should now be unchecked');

    // click to unfollow
    form.$('.o_followers_follow_button').click(); // click to open the dropdown
    assert.ok($('.modal').length, 'a confirm modal should be opened');
    $('.modal .modal-footer .btn-primary').click(); // click on 'OK'
    assert.strictEqual(form.$('.o_followers_count').text(), "0", 'should have no followers');
    assert.ok(form.$('.o_followers_follow_button.o_followers_notfollow').length,
        'should display the "Follow" button');

    form.destroy();
});

QUnit.test('followers widget: do not display follower duplications', function (assert) {
    assert.expect(2);

    this.data.partner.records[0].message_follower_ids = [1];
    var resID = 2;
    var followers = [{
        id: 1,
        name: "Admin",
        email: "admin@example.com",
        res_id: resID,
        res_model: 'partner',
    }];
    var def;
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form>' +
                '<sheet></sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                '</div>' +
            '</form>',
        mockRPC: function (route, args) {
            if (route === '/mail/read_followers') {
                return $.when(def).then(function () {
                    return {
                        followers: _.filter(followers, function (follower) {
                            return _.contains(args.follower_ids, follower.id);
                        }),
                        subtypes: [],
                    };
                });
            }
            return this._super.apply(this, arguments);
        },
        res_id: resID,
        session: {partner_id: 1},
    });


    followers.push({
        id: 2,
        is_uid: false,
        name: "A follower",
        email: "follower@example.com",
        res_id: resID,
        res_model: 'partner',
    });
    this.data.partner.records[0].message_follower_ids.push(2);

    // simulate concurrent calls to read_followers and check that those followers
    // are not added twice in the dropdown
    def = $.Deferred();
    form.reload();
    form.reload();
    def.resolve();

    assert.strictEqual(form.$('.o_followers_count').text(), '2',
        "should have 2 followers");
    assert.strictEqual(form.$('.o_followers_list .o_partner').length, 2,
        "there should be 2 followers in the follower dropdown");

    form.destroy();
});

});
});
