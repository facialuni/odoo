odoo.define('sale_payment.quotation_view', function (require) {
'use strict';

    var ajax = require('web.ajax');
    var Widget = require('web.Widget');
    var QuotationPayment = require('payment.transaction');

    // Accept Modal, with jSignature
    var AcceptModal = Widget.extend({
        events: {
            'shown.bs.modal': 'initSignature',
            'click #sign_clean': 'clearSignature',
            'submit #accept': 'submitForm',
        },
        initSignature: function(ev){
            this.$("#signature").empty().jSignature({'decor-color' : '#D1D0CE', 'color': '#000', 'background-color': '#fff'});
            this.empty_sign = this.$("#signature").jSignature("getData",'image');
        },
        clearSignature: function(ev){
            this.$("#signature").jSignature('reset');
        },
        submitForm: function(ev){
            // extract data
            var self = this,
                $confirm_btn = self.$el.find('button[type="submit"]');

            // Support 2 routes:
            // - <form id="accept" method="POST" t-attf-action="/quote/accept/#{quotation.id}/?token=#{quotation.access_token}" ...>
            // - <form id="accept" method="POST" t-att-data-order-id="quotation.id" t-att-data-token="quotation.access_token" ...>
            // The first route is deprecated but might still be used if the template is not updated
            var href = self.$el.find('form').attr("action");
            if (href) {
                var action = href.match(/quote\/([a-z]+)/)[1],
                    order_id = parseInt(href.match(/quote\/[a-z]+\/([0-9]+)/)[1]),
                    token = href.match(/token=(.*)/) && href.match(/token=(.*)/)[1];
            }
            else {
                var action = 'accept',
                    order_id = self.$el.find('form').data("order-id"),
                    token = self.$el.find('form').data("token");
            }

            if (action == 'accept') {
                ev.preventDefault();
                // process : display errors, or submit
                var signer_name = self.$("#name").val(),
                    signature = self.$("#signature").jSignature("getData",'image'),
                    is_empty = signature ? this.empty_sign[1] == signature[1] : false;

                self.$('#signer').toggleClass('has-error', !signer_name);
                self.$('#drawsign').toggleClass('panel-danger', is_empty).toggleClass('panel-default', !is_empty);
                if (is_empty || ! signer_name){
                    setTimeout(function () {
                        self.$('button[type="submit"], a.a-submit').removeAttr('data-loading-text').button('reset');
                    })
                    return false;
                }
                $confirm_btn.prepend('<i class="fa fa-spinner fa-spin"></i> ');
                $confirm_btn.attr('disabled', true);
                ajax.jsonRpc("/quote/"+action, 'call', {
                    'order_id': order_id,
                    'token': token,
                    'signer': signer_name,
                    'sign': signature?JSON.stringify(signature[1]):false,
                }).then(function (data) {
                    var message_id = (data) ? 3 : 4;
                    self.$el.modal('hide');
                    window.location.href = '/quote/'+order_id.toString()+'/'+token+'?message='+message_id;
                });
                return false;
            }
        },
    });

    $(document).ready(function () {

        var accept_modal = new AcceptModal();
        accept_modal.setElement($('#modalpayment'));
        accept_modal.start();
        if($("#online_qoutation_payment").length || $("#website_quote_payment").length){
            var quote_payment = new QuotationPayment();
            if ($("#online_qoutation_payment").length){
                quote_payment.attachTo($("#online_qoutation_payment"));
            }
            if ($("#website_quote_payment").length){
                quote_payment.attachTo($("#website_quote_payment"));
            }
        }

        if($(".o_quote_report_html").length){
            var href = $(location).attr("href"),
                order_id = href.match(/quote\/([0-9]+)/)[1],
                access_token = href.match(/quote\/[0-9]+\/([^\/?]*)/),
                params = {};

            params.token = access_token ? access_token[1] : '';
            params.order_id = order_id;
            ajax.jsonRpc('/quote/report/html', 'call', params).then(function (data) {
                var $iframe = $('iframe#print_quote')[0];
                $iframe.contentWindow.document.open('text/htmlreplace');
                $iframe.contentWindow.document.write(data);
            });
        }
        $('a#print_quote_iframe').on('click', function(event){
            event.preventDefault();
            event.stopPropagation();
            $('iframe#print_quote')[0].contentWindow.print();
        });
    });
});
