# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase


class TestBookingPro(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env['bookingpro.category'].create({'name': 'Consultation'})
        self.service = self.env['bookingpro.service'].create({
            'name': 'General Consultation',
            'category_id': self.category.id,
            'duration': 1.0,
            'price': 50,
            'company_id': self.env.company.id,
        })
        self.partner = self.env['res.partner'].create({'name': 'Test Customer', 'email': 'customer@example.com'})

    def test_appointment_creation(self):
        start = datetime.now() + timedelta(days=1)
        appointment = self.env['bookingpro.appointment'].create({
            'partner_id': self.partner.id,
            'service_id': self.service.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
            'company_id': self.env.company.id,
        })
        self.assertTrue(appointment.name)
        self.assertEqual(appointment.state, 'pending')
