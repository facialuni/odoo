odoo.define('web_editor.translate', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var rte = require('web_editor.rte');
var editor_widget = require('web_editor.widget');

var _t = core._t;
var qweb = core.qweb;

var edit_translations = !!$('html').data('edit_translations');

$.fn.extend({
  prependEvent: function (events, selector, data, handler) {
    this.on(events, selector, data, handler);
    events = events.split(' ');
    this.each(function () {
        var el = this;
        _.each(events, function (event) {
            var handler = $._data(el, 'events')[event].pop();
            $._data(el, 'events')[event].unshift(handler);
        });
    });
    return this;
  }
});

var RTE_Translate = rte.Class.extend({
    editable: function () {
        return $('#wrapwrap [data-o-translation-seq]');
    },
});

var Translate_Modal = editor_widget.Dialog.extend({
    init: function (p, options, parent, node) {
        this._super(p, _.extend({}, {
            title: _t("Translate Attribute"),
            buttons: [
                {text:  _t("Close"), classes: "btn-primary o_save_button", close: true, click: this.save}
            ]
        }, options || {}));
        this.parent = parent;
        this.$target = $(node);
        this.translation = $(node).data('translation');
    },
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        var $group = $("<div/>", {"class": "form-group"}).appendTo(this.$el);
        _.each(this.translation, function (node, attr) {
            var $node = $(node);
            var $label = $('<label class="control-label"></label>').text(attr);
            var $input = $('<input class="form-control"/>').val($node.html());
            $input.on('change keyup', function () {
                var value = $input.val();
                $node.html(value).trigger('change', node);
                $node.data('$node').attr($node.data('attribute'), value).trigger('translate');
                self.parent.rte_changed(node);
            });
            $group.append($label).append($input);
        });
        return def;
    }
});

function getItem (t, lang, model, field, res_id, seq) {
    t = t[lang] || (t[lang] = {});
    t = t[model] || (t[model] = {});
    t = t[field] || (t[field] = {});
    t = t[res_id] || (t[res_id] = {});
    return t[seq] || (t[seq] = {});
}

var Translate = Widget.extend({
    events: {
        'click [data-action="save"]': 'save',
        'click [data-action="cancel"]': 'cancel',
        'click .o_translation_languages a': 'active_lang',
        'mouseenter .o_translation_languages a': 'mouseenter_lang',
        'mouseleave .o_translation_languages a': 'mouseleave_lang',
    },
    template: 'web_editor.editorbar',
    init: function (parent, $target, lang) {
        this.parent = parent;
        this.ir_translation = new Model('ir.translation');
        this.lang = lang || base.get_context().lang;
        this.setTarget($target);
        this._super.apply(this, arguments);

        this.rte = new RTE_Translate(this, this.config);
    },
    start: function () {
        this._super();

        var languages = [];
        $('.js_language_selector .js_change_lang').each(function () {
            languages.push([$(this).data('lang'), _.str.strip($(this).text())]);
        });

        var $lang = $(qweb.render('website.TranslatorLanguages', {'languages': languages}));
        $("#web_editor-top-edit form").prepend($lang);

        return this.edit();
    },
    setTarget: function ($target) {
        this.$target = $target.find('[data-o-translation-seq]');

        // attributes

        var attrs = ['placeholder', 'title', 'alt'];
        _.each(attrs, function (attr) {
            $target.find('[data-o-translation-' + attrs.join('-seq], [data-o-translation-') + '-seq]').filter(':empty, input, select, textarea, img').each(function () {
                var $node = $(this);
                var translation = $node.data('translation') || {};
                var trans = $node.attr(attr);
                var $trans = $('<span/>').addClass('hidden o_editable o_editable_translatable_attribute').appendTo('body');
                $trans.data('$node', $node).data('attribute', attr);
                translation[attr] = $trans[0];
                $node.attr(attr, match[2]);

                var select2 = $node.data('select2');
                if (select2) {
                    select2.blur();
                    $node.on('translate', function () {
                        select2.blur();
                    });
                    $node = select2.container.find('input');
                }
                $node.addClass('o_translatable_attribute').data('translation', translation);
            });
        });
        this.$target_attr = $target.find('.o_translatable_attribute');
        this.$target_attribute = $('.o_editable_translatable_attribute');
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
    save_change: function () {
        var self = this;
        if (this.lang !== this.lang_displayed) {
            return;
        }
        _.each(this.get_lang(), function (data) {
            if (!data.$node.hasClass('o_dirty')) {
                return;
            }
            var value = data.attr ? data.$node.attr(data.attr) : data.$node.html();
            var item = getItem(self.translations, self.lang, data.model, data.field, data.res_id, data.seq);
            if (item.value && item.value.replace(/[ \t\n\r]+/, ' ') === value.replace(/[ \t\n\r]+/, ' ')) {
                return;
            } else if (!item.model) {
                item.model = data.model;
                item.field = data.field;
                item.res_id = data.res_id;
                item.seq = data.seq;
                item.lang = self.lang;
                item.type = 'model';
            }
            item.state = 'translated';
            item.value = value;
            item.changed = true;
        });
    },
    display_lang: function (lang, getDefault) {
        var self = this;
        if (!getDefault && this.lang_displayed === lang) {
            return;
        }
        this.$target.add(this.$target_attr).removeClass('o_translation_to_translate o_translation_inprogress o_translation_translated');
        if (this.$target.attr('class') === '') {
            this.$target.removeAttr('class');
        }

        this.lang_displayed = lang;
        _.each(this.get_lang(), function (data) {
            var item = getItem(self.translations, lang, data.model, data.field, data.res_id, data.seq);
            var value = getDefault ? item.default : item.value;
            if (value) {
                data.attr ? data.$node.attr(data.attr, value) : data.$node.html(value);
            }
            if (!getDefault) {
                data.$node.addClass('o_translation_' + (item.state || 'to_translate'));
            }
        });
    },
    active_lang: function (el) {
        this.save_change();
        this.lang = $(el.target).data('lang');
        this.display_lang(this.lang);
    },
    mouseenter_lang: function (el) {
        this.save_change();
        var lang = $(el.target).data('lang');
        this.display_lang(lang);
    },
    mouseleave_lang: function (el) {
        this.display_lang(this.lang);
    },
    edit: function () {
        var self = this;
        var flag = false;
        var domain = [];
        var list = this.get_lang();

        window.onbeforeunload = function (event) {
            if ($('.o_editable.o_dirty').length && !flag) {
                flag = true;
                setTimeout(function () {flag=false;},0);
                return _t('This document is not saved!');
            }
        };

        this.$target.addClass("o_editable");
        this.rte.start();

        _.each(list, function (data) {
            if (domain.length) {
                domain.unshift('|');
            }
            domain = domain.concat(['&', '&', ['name', '=', data.model+','+data.field], ['res_id', '=', data.res_id], ['seq', '=', data.seq]]);
        });
        domain.unshift(['type', '=', 'model']);

        this.translations = {};
        this.defaultLang =  this.lang;

        return ajax.jsonRpc('/web/dataset/call', 'call', {
            model: 'ir.translation',
            method: 'search_read',
            args: [domain, ['name', 'type', 'res_id', 'seq', 'lang', 'value', 'state']],
        }).then(function (datas) {
            _.each(datas, function (data) {
                var name = data.name.split(',');
                var item = getItem(self.translations, data.lang, name[0], name[1], data.res_id, data.seq);
                if (data.value) {
                    data.value = data.value.replace('&amp;', '&');
                }
                item.default = data.value;
                for (var k in data) {
                    item[k] = data[k];
                }
            });
            self.display_lang(self.lang);
            self.onTranslateReady();
        });
    },
    onTranslateReady: function (datas) {
        this.$el.show();
        this.trigger("edit");
        $('body').addClass('translation_enable');
        this.$target.parent().prependEvent('click', this.__unbind_click);
        this.$target_attr.prependEvent('mousedown click mouseup', this, this.__translate_attribute);
        console.info('Click on CTRL when you click in an translatable area to have the default behavior');
    },
    __unbind_click: function (event) {
        if (event.ctrlKey || !$(event.target).is(':o_editable')) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
    },
    __translate_attribute: function (event) {
        if (event.ctrlKey) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (event.type !== 'mousedown') {
            return;
        }

        new Translate_Modal(null, {}, event.data, event.target).open();
    },
    close: function () {
        this.rte.cancel();
        $('body').removeClass('translation_enable');
        this.$target.add(this.$target_attr).removeClass('o_editable o_is_inline_editable o_dirty');
        this.$target.removeAttr('data-note-id').removeAttr('contentEditable');
        this.$target.parent().off('click', this.__unbind_click);
        this.$target_attr.off('mousedown click mouseup', this, this.__translate_attribute);
        this.$el.hide();
        window.onbeforeunload = null;
    },
    save: function () {
        this.save_change();
        var translations = _.chain(this.translations).values()
            .map(_.values).flatten() // model
            .map(_.values).flatten() // field
            .map(_.values).flatten() // res_id
            .map(_.values).flatten() // seq
            .value();
        console.log('save !!! TODO parse server side to xml', translations);

        for (var k in translations) {
            var trans = translations[k];
            if (!trans.changed) continue;
            var value = _.pick(trans, 'type', 'res_id', 'seq', 'lang', 'value', 'state');
            value.name = trans.model+','+trans.field;
            value.src = ''+value.seq;

            console.log(trans, '=>', value);
            if (trans.id) {
                ajax.jsonRpc('/web/dataset/call', 'call', {
                    model: 'ir.translation',
                    method: 'write',
                    args: [[trans.id], value],
                });
            } else {
                ajax.jsonRpc('/web/dataset/call', 'call', {
                    model: 'ir.translation',
                    method: 'create',
                    args: [value],
                });
            }
        }
        this.close();
    },
    cancel: function () {
        var self = this;
        this.display_lang(this.defaultLang, true);
        this.close();
        this.trigger("cancel");
    },
    destroy: function () {
        this.cancel();
        this.$el.remove();
        this._super.apply(this, arguments);
    },

    config: function ($editable) {
        if ($editable.data('oe-model')) {
            return {
                'airMode' : true,
                'focus': false,
                'airPopover': [
                    ['history', ['undo', 'redo']],
                ],
                'styleWithSpan': false,
                'inlinemedia' : ['p'],
                'lang': "odoo",
                'onChange': function (html, $editable) {
                    $editable.trigger("content_changed");
                }
            };
        }
        return {
            'airMode' : true,
            'focus': false,
            'airPopover': [
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['history', ['undo', 'redo']],
            ],
            'styleWithSpan': false,
            'inlinemedia' : ['p'],
            'lang': "odoo",
            'onChange': function (html, $editable) {
                $editable.trigger("content_changed");
            }
        };
    }
});


if (edit_translations) {
    base.ready().then(function () {
        data.instance = new Translate(this, $('#wrapwrap'));
        data.instance.prependTo(document.body);

        $('a[href*=edit_translations]').each(function () {
            this.href = this.href.replace(/[$?]edit_translations[^&?]+/, '');
        });
        $('form[action*=edit_translations]').each(function () {
            this.action = this.action.replace(/[$?]edit_translations[^&?]+/, '');
        });

        $('title').html($('title').html().replace(/&lt;span data-oe-model.+?&gt;(.+?)&lt;\/span&gt;/, '\$1'));
    });
}

var data = {
    'edit_translations': edit_translations,
    'Class': Translate,
};
return data;

});
