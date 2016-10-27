odoo.define('website.translator', function (require) {
'use strict';

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var translate = require('web_editor.translate');
var website = require('website.website');
var local_storage = require('web.local_storage');

var qweb = core.qweb;

ajax.loadXML('/website/static/src/xml/website.translator.xml', qweb);
var nodialog = 'website_translator_nodialog';

website.TopBar.include({
    events: _.extend({}, website.TopBar.prototype.events, {
        'click [data-action="translate"]': 'translate',
    }),
    translate: function (ev) {
        ev.preventDefault();
        if (!local_storage.getItem(nodialog)) {
            var dialog = new TranslatorDialog();
            dialog.appendTo($(document.body));
            dialog.on('activate', this, function () {
                if (dialog.$('input[name=do_not_show]').prop('checked')) {
                    local_storage.setItem(nodialog, true);
                } else {
                    local_storage.removeItem(nodialog);
                }
                dialog.$el.modal('hide');
            });
        }
        new translate.Class(this, $('#wrapwrap')).prependTo(document.body);
    },
});

var TranslatorDialog = Widget.extend({
    events: _.extend({}, website.TopBar.prototype.events, {
        'hidden.bs.modal': 'destroy',
        'click button[data-action=activate]': function (ev) {
            this.trigger('activate');
        },
    }),
    template: 'website.TranslatorDialog',
    start: function () {
        this.$el.modal();
    },
});

var Translate = translate.Class.include({
    onTranslateReady: function () {
        if(this.gengo_translate) {
            this.translation_gengo_display();
        }
        this._super();
    },
    edit: function () {
        $("#oe_main_menu_navbar").hide();
        return this._super();
    },
    cancel: function () {
        $("#oe_main_menu_navbar").show();
        return this._super();
    }
});


});
