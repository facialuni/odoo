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

function getItem (t, model, field, res_id, seq) {
    t = t[model] || (t[model] = {});
    t = t[field] || (t[field] = {});
    t = t[res_id] || (t[res_id] = {});
    return t[seq] || (t[seq] = {});
}

var Translate = translate.Class.include({
    events: _.extend({}, translate.Class.prototype.events, {
        'click .o_translation_languages a': 'active_lang',
        'mouseenter .o_translation_languages a': 'mouseenter_lang',
        'mouseleave .o_translation_languages a': 'mouseleave_lang',
    }),
    onTranslateReady: function () {
        if(this.gengo_translate) {
            this.translation_gengo_display();
        }

        var languages = [];
        $('.js_language_selector .js_change_lang').each(function () {
            languages.push([$(this).data('lang'), _.str.strip($(this).text())]);
        });

        var $lang = $(qweb.render('website.TranslatorLanguages', {'languages': languages}));
        $("#web_editor-top-edit form").prepend($lang);

        this._super();
    },
    get_lang: function () {
        var  list = [];
        $('#wrapwrap [data-o-translation-model]').each(function () {
            var $node = $(this);
            var model = $node.data('o-translation-model');
            var field = $node.data('o-translation-field');
            var id = $node.data('o-translation-id');
            var seq = $node.data('o-translation-seq');
            if (seq !== null) {
                list.push({
                    'model': model,
                    'field': field,
                    'res_id': id,
                    'seq': parseInt(seq),
                    '$node': $node,
                });
            }
            _.each(this.attributes, function (attr) {
                var name = attr.name.match(/o-translation-(.*)-seq/);
                if (name) {
                    list.push({
                        'model': model,
                        'field': field,
                        'res_id': id,
                        'seq': parseInt(attr.value),
                        'attr': name[0],
                        '$node': $node,
                    });
                }
            });
        });
        return list;
    },
    save_lang: function () {
        if (this.lang !== this.lang_displayed) {
            return;
        }
        var translations = this.translations[this.lang];
        _.each(this.get_lang(), function (data) {
            if (!data.$node.hasClass('o_dirty')) {
                return;
            }
            var value = data.attr ? data.$node.attr(data.attr) : data.$node.html();
            var item = getItem(translations, data.model, data.field, data.res_id, data.seq);
            item.state = 'translated';
            item.value = value;
        });
    },
    display_lang: function (lang) {
        if (this.lang_displayed === lang) {
            return;
        }
        $('#wrapwrap [data-o-translation-model]').removeClass('o_translation_to_translate o_translation_inprogress o_translation_translated');

        var translations = this.translations[this.lang_displayed = lang];
        _.each(this.get_lang(), function (data) {
            var item = getItem(translations, data.model, data.field, data.res_id, data.seq);
            data.attr ? data.$node.attr(data.attr, item.value || '...') : data.$node.html(item.value || '...');
            data.$node.addClass('o_translation_' + (item.state || 'to_translate'));
        });
    },
    active_lang: function (el) {
        this.save_lang();
        this.lang = $(el.target).data('lang');
        this.display_lang(this.lang);
    },
    mouseenter_lang: function (el) {
        this.save_lang();
        var lang = $(el.target).data('lang');
        this.display_lang(lang);
    },
    mouseleave_lang: function (el) {
        this.display_lang(this.lang);
    },
    edit: function () {
        var self = this;
        var domain = [];
        var list = this.get_lang();
        _.each(list, function (data) {
            if (domain.length) {
                domain.unshift('|');
            }
            domain = domain.concat(['&', '&', ['name', '=', data.model+','+data.field], ['res_id', '=', data.res_id], ['seq', '=', data.seq]]);
        });

        this.translations = {};
        this.lang =  base.get_context().lang;

        ajax.jsonRpc('/web/dataset/call', 'call', {
            model: 'ir.translation',
            method: 'search_read',
            args: [domain, ['name', 'type', 'res_id', 'seq', 'lang', 'value', 'state']],
        }).then(function (datas) {
            _.each(datas, function (data) {
                var t = self.translations;
                var name = data.name.split(',');
                var item = getItem(t[data.lang] || (t[data.lang] = {}), name[0], name[1], data.res_id, data.seq);
                for (var k in data) {
                    item[k] = data[k];
                }
            });
            self.display_lang(self.lang);
        });
        $("#oe_main_menu_navbar").hide();
        return this._super();
    },
    cancel: function () {
        $("#oe_main_menu_navbar").show();
        return this._super();
    }
});


});
