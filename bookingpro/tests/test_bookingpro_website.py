# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBookingProWebsite(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.staff_user = cls.env.user
        cls.target_date = fields.Date.today() + timedelta(days=8)
        cls.category = cls.env['bookingpro.category'].create({
            'name': 'HTTP Test Consultation',
            'company_id': cls.company.id,
            'website_published': True,
        })
        cls.resource = cls.env['bookingpro.resource'].create({
            'name': 'HTTP Test Room',
            'resource_type': 'room',
            'company_id': cls.company.id,
        })
        cls.service = cls.env['bookingpro.service'].create({
            'name': 'HTTP Test Appointment',
            'category_id': cls.category.id,
            'duration': 1.0,
            'price': 50.0,
            'company_id': cls.company.id,
            'website_published': True,
            'staff_user_ids': [(6, 0, [cls.staff_user.id])],
            'resource_ids': [(6, 0, [cls.resource.id])],
        })
        cls.env['bookingpro.staff.schedule'].create({
            'staff_user_id': cls.staff_user.id,
            'weekday': str(cls.target_date.weekday()),
            'hour_from': 9.0,
            'hour_to': 17.0,
            'company_id': cls.company.id,
        })

    def test_public_booking_pages_render(self):
        listing = self.url_open('/bookingpro')
        self.assertEqual(listing.status_code, 200)
        self.assertIn(self.service.name, listing.text)

        detail = self.url_open('/bookingpro/service/%s' % self.service.id)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(self.service.name, detail.text)

    def test_slots_jsonrpc_endpoint_returns_available_slots(self):
        response = self.url_open('/bookingpro/slots', json={'params': {
            'service_id': self.service.id,
            'selected_date': fields.Date.to_string(self.target_date),
            'staff_id': self.staff_user.id,
            'resource_id': self.resource.id,
        }})
        payload = json.loads(response.content)
        result = payload.get('result') or {}
        self.assertTrue(result.get('success'))
        self.assertTrue(result.get('slots'))
