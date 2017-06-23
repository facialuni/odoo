odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');
var Widget = require('web.Widget');
var web_editor_base = require('web_editor.base')

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({
    start: function() {
        var self = this;
        var res = this._super.apply(this.arguments).then(function() {
            $('#registration_form .a-submit')
                .off('click')
                .removeClass('a-submit')
                .click(function (ev) {
                    self.on_click(ev);
                });
        });
        return res
    },
    on_click: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var post = {};
        $("#registration_form select").each(function() {
            post[$(this).attr('name')] = $(this).val();
        });
        var tickets_ordered = _.some(_.map(post, function(value, key) { return parseInt(value) }));
        if (! tickets_ordered) {
            return $('#registration_form table').after(
                '<div class="alert alert-info">Please select at least one ticket.</div>'
            );
        }
        else {
            return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.appendTo($form).modal();
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                });
            });
        }
    },
});

var TimeZoneForm = Widget.extend({
    start: function() {
        var self = this;
        var res = this._super.apply(this.arguments).then(function() {
            $('.o_user_timezone')
                .off('click')
                .click(function (ev) {
                    self.on_click(ev);
                });
        });
        return res
    },
    on_click: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form'), post = {};
        return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
            var $modal = $(modal), tzContainer = $modal.find('#timezone-container');
            $modal.appendTo('body').modal();
            ajax.jsonRpc('/event/get_all_timezone', 'call', {}).done(function(data) {
                _.each(data, function(value, key) {
                    $('<option>'+ value +'</option>').appendTo(tzContainer);
                });
            });
            $modal.on('click', '.o_set_timezone_btn', function () {
                var another_timezone = tzContainer.val(), newData = null;
                _.each($('.o_visitor_timezone'), function (el) {
                    $(el).text(another_timezone);
                    $modal.modal('hide');
                });
                _.each($('[data-event-visitor-date]'), function (el) {
                    ajax.jsonRpc("/event/set_timezone", 'call', {
                        timezone: another_timezone,
                        date_time: $(el).data('event-visitor-date')
                    }).done(function(data) {
                        if(newData === null) {
                            newData = data;
                            $('.starting_date').text(newData);
                        }
                        else {
                            $('.ending_date').text(data);
                        }
                    });
                });
            });
            $modal.on('click', '.js_goto_event', function () {
                $modal.modal('hide');
            });
        });
    },
});

web_editor_base.ready().then(function(){
    _.each($('[data-event-visitor-date]'), function (el) {
        var utc_date = $(el).data('event-visitor-date');
        $(el).text(moment.utc(utc_date).utcOffset(moment().utcOffset()).format("L HH:mm"));
   });
    _.each($('.o_visitor_timezone'), function (el) {
        var visitor_system_timezone = jstz.determine().name()
        $(el).text = $(el).text(visitor_system_timezone);
    });
    var event_registration_form = new EventRegistrationForm().appendTo($('#registration_form'));
    var timezone_selection_form = new TimeZoneForm().appendTo($('.o_user_timezone'));
});

return { EventRegistrationForm: EventRegistrationForm };

});
