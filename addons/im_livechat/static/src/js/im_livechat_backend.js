odoo.define('im_livechat.chat_client_action', function (require) {
"use strict";

require('mail.chat_client_action');
var chat_manager = require('mail.chat_manager');
var core = require('web.core');
var field_registry = require('web.field_registry');

var qweb = core.qweb;
var _t = core._t;

core.action_registry.get('mail.chat.instant_messaging').include({
    _renderSidebar: function (options) {
        // Override to sort livechat channels by last message's date
        var channel_partition = _.partition(options.channels, function (channel) {
            return channel.type === 'livechat';
        });
        channel_partition[0].sort(function (c1, c2) {
            return c2.last_message_date.diff(c1.last_message_date);
        });
        options.channels = channel_partition[0].concat(channel_partition[1]);
        return this._super(options);
    },
});

chat_manager.bus.on('new_message', null, function (msg) {
    _.each(msg.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.last_message_date = msg.date; // update the last message's date of the channel
        }
    });
});

var FieldText = field_registry.get('text');
var FieldChar = field_registry.get('char');

var CopyClipboard = {
    add_clipboard: function (event) {
        var self = this;
        var $clipboardBtn = this.$('.o_clipboard_button');
        $clipboardBtn.tooltip({title: _t('Copied !'), trigger: 'manual', placement: 'right'});
        this.clipboard = new Clipboard($clipboardBtn.get(0), {
            text: function () {
                return self.get_copy_text();
            }
        });
        this.clipboard.on('success', function () {
            _.defer(function () {
                $clipboardBtn.tooltip('show');
                _.delay(function () {
                    $clipboardBtn.tooltip('hide');
                }, 800);
            });
        });
    },
    get_copy_text: function () {
        return this.value.trim();
    },
    destory: function() {
        this._super.apply(this, arguments);
        this.clipboard.destory();
    }
};

var TextCopyClipboard = FieldText.extend(CopyClipboard, {
    _render: function() {
        this._super.apply(this, arguments);
        this.$el.addClass('o_field_copy');
        this.$el.append($(qweb.render('CopyClipboardText')));
        this.add_clipboard();
    }
});

var CharCopyClipboard = FieldChar.extend(CopyClipboard, {
    _render: function() {
        this._super.apply(this, arguments);
        this.$el.addClass('o_field_copy');
        this.$el.append($(qweb.render('CopyClipboardChar')));
        this.add_clipboard();
    }
});

field_registry
    .add('CopyClipboardText', TextCopyClipboard)
    .add('CopyClipboardChar', CharCopyClipboard);
});
