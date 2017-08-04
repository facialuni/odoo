from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon

from odoo.tools import mute_logger

from lxml import objectify


class PaypalExpressCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(PaypalExpressCommon, self).setUp()
        self.paypal = self.env.ref('payment.payment_acquirer_paypal')


class PaypalExpressForm(PaypalExpressCommon):

    def test_10_paypal_express_checkout_url(self):
        if self.paypal.paypal_payment_method == 'express':
            # be sure not to do stupid things
            self.assertEqual(self.paypal.environment, 'test', 'test without test environment')

            # self.assertEqual(self.paypal.website_published, True, 'paypal should be active and published on website')
            val = {
                'business': self.paypal.paypal_email_account,
                'amount': 1.0,
                'currency_code': 'USD'
            }

            url = self.paypal._get_paypal_express_urls(self.paypal.environment, val)
            self.assertEqual(url['paypal_form_url'], 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=' + url['token'], 'f')

    def test_11_paypal_express_form_with_fees(self):
        if self.paypal.paypal_payment_method == 'express':
            # be sure not to do stupid things
            self.assertEqual(self.paypal.environment, 'test', 'test without test environment')

            # update acquirer: compute fees
            self.paypal.write({
                'fees_active': True,
                'fees_dom_fixed': 1.0,
                'fees_dom_var': 0.35,
                'fees_int_fixed': 1.5,
                'fees_int_var': 0.50,
            })

            # render the button
            res = self.paypal.render(
                'test_ref0', 1.0, self.currency_euro.id,
                values=self.buyer_values)

            # check form result
            handling_found = False
            tree = objectify.fromstring(res)
            for form_input in tree.input:
                if form_input.get('name') in ['handling']:
                    handling_found = True
                    self.assertEqual(form_input.get('value'), '1.51', 'paypal: wrong computed fees')
            self.assertTrue(handling_found, 'paypal: fees_active did not add handling input in rendered form')

    @mute_logger('odoo.addons.payment_paypal.models.payment', 'ValidationError')
    def test_20_paypal_express_form_management(self):
        if self.paypal.paypal_payment_method == 'express':
            # be sure not to do stupid things
            self.assertEqual(self.paypal.environment, 'test', 'test without test environment')

            # typical data posted by paypal after client has successfully paid
            paypal_post_data = {
                'PAYMENTINFO_0_TRANSACTIONTYPE': u'expresscheckout',
                'ACK': u'Success',
                'PAYMENTINFO_0_PAYMENTTYPE': u'instant',
                'PAYMENTINFO_0_ERRORCODE': u'0',
                'PAYMENTINFO_0_REASONCODE': u'None',
                'PAYMENTINFO_0_ACK': u'Success',
                'PAYMENTINFO_0_PROTECTIONELIGIBILITYTYPE': u'None',
                'PAYMENTINFO_0_TAXAMT': u'0.00',
                'PAYMENTINFO_0_CURRENCYCODE': u'EUR',
                'PAYMENTINFO_0_TRANSACTIONID': u'9MU67603JN6100323',
                'VERSION': u'93',
                'PAYMENTINFO_0_PENDINGREASON': u'unilateral',
                'PAYMENTINFO_0_AMT': 1.95,
                'PAYMENTINFO_0_PROTECTIONELIGIBILITY': u'Ineligible',
                'PAYMENTINFO_0_PAYMENTSTATUS': u'Pending',
                'item_number': u'test_ref_2',
                'TIMESTAMP': u'03:21:19 Nov 18, 2013 PST',
            }

            # should raise error about unknown tx
            with self.assertRaises(ValidationError):
                self.env['payment.transaction'].form_feedback(paypal_post_data, 'paypal')
            # create tx
            tx = self.env['payment.transaction'].create({
                'amount': 1.95,
                'acquirer_id': self.paypal.id,
                'currency_id': self.currency_euro.id,
                'reference': 'test_ref_2',
                'partner_name': 'Norbert Buyer',
                'partner_country_id': self.country_france.id})

            # validate it
            tx.form_feedback(paypal_post_data, 'paypal')
            # check
            self.assertEqual(tx.state, 'pending', 'paypal: wrong state after receiving a valid pending notification')
            self.assertEqual(tx.state_message, 'unilateral', 'paypal: wrong state message after receiving a valid pending notification')
            self.assertEqual(tx.acquirer_reference, '9MU67603JN6100323', 'paypal: wrong txn_id after receiving a valid pending notification')
            self.assertFalse(tx.date_validate, 'paypal: validation date should not be updated whenr receiving pending notification')

            # update tx
            tx.write({
                'state': 'draft',
                'acquirer_reference': False})

            # update notification from paypal
            paypal_post_data['PAYMENTINFO_0_PAYMENTSTATUS'] = 'Completed'
            # validate it
            tx.form_feedback(paypal_post_data, 'paypal')
            # check
            self.assertEqual(tx.state, 'done', 'paypal: wrong state after receiving a valid pending notification')
            self.assertEqual(tx.acquirer_reference, '9MU67603JN6100323', 'paypal: wrong txn_id after receiving a valid pending notification')
