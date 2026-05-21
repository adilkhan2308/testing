# -*- coding: utf-8 -*-

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBookingProAuth(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = 'bookingpro-test-password'
        login = 'bookingpro_auth_manager'
        email = 'bookingpro.auth.manager@example.test'
        group_ids = [
            cls.env.ref('base.group_user').id,
            cls.env.ref('bookingpro.group_bookingpro_manager').id,
        ]
        user = cls.env['res.users'].search(['|', ('login', '=', login), ('email', '=ilike', email)], limit=1)
        user_values = {
            'name': 'BookingPro Auth Manager',
            'login': login,
            'email': email,
            'password': cls.password,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, group_ids)],
        }
        if user:
            user.with_context(no_reset_password=True).write(user_values)
            cls.user = user
        else:
            cls.user = cls.env['res.users'].with_context(no_reset_password=True).create(user_values)
        customer_login = 'bookingpro_customer_user'
        customer_email = 'bookingpro.customer.user@example.test'
        customer = cls.env['res.users'].search([
            '|', ('login', '=', customer_login), ('email', '=ilike', customer_email),
        ], limit=1)
        customer_values = {
            'name': 'BookingPro Customer User',
            'login': customer_login,
            'email': customer_email,
            'password': cls.password,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        }
        if customer:
            customer.with_context(no_reset_password=True).write(customer_values)
            cls.customer_user = customer
        else:
            cls.customer_user = cls.env['res.users'].with_context(no_reset_password=True).create(customer_values)

    def test_custom_login_accepts_username_credentials(self):
        response = self.url_open('/web/login', data={
            'login': self.user.login,
            'password': self.password,
            'redirect': '/bookingpro/post-login',
        }, allow_redirects=False)

        self.assertIn(response.status_code, (302, 303))
        self.assertIn('/bookingpro/workspace', response.headers.get('Location', ''))

    def test_custom_login_accepts_email_credentials(self):
        response = self.url_open('/web/login', data={
            'login': self.user.email,
            'password': self.password,
            'redirect': '/bookingpro/post-login',
        }, allow_redirects=False)

        self.assertIn(response.status_code, (302, 303))
        self.assertIn('/bookingpro/workspace', response.headers.get('Location', ''))

    def test_customer_login_opens_customer_portal(self):
        response = self.url_open('/web/login', data={
            'login': self.customer_user.email,
            'password': self.password,
            'redirect': '/bookingpro/post-login',
        }, allow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('BookingPro Customer Portal', response.text)
        self.assertIn('My Appointments', response.text)

    def test_custom_login_rejects_wrong_password(self):
        response = self.url_open('/web/login', data={
            'login': self.user.login,
            'password': 'not-the-password',
            'redirect': '/bookingpro/post-login',
        }, allow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Wrong login or password', response.text)
