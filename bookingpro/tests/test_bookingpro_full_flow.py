# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBookingProFullFlow(TransactionCase):
    """Functional unit coverage for the BookingPro MVP flow.

    Run inside Odoo with:
        odoo-bin -d <db> -u bookingpro --test-enable --stop-after-init
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.icp = cls.env['ir.config_parameter'].sudo()
        cls.icp.set_param('bookingpro.create_crm_lead', 'True')
        cls.icp.set_param('bookingpro.auto_followup_on_completion', 'True')
        cls.icp.set_param('bookingpro.followup_delay_days', '1')
        cls.icp.set_param('bookingpro.enable_email_reminders', 'True')
        cls.icp.set_param('bookingpro.send_5h_reminder', 'True')
        cls.icp.set_param('bookingpro.send_1h_reminder', 'True')
        cls.icp.set_param('bookingpro.readai_enabled', 'False')

        cls.company = cls.env.company
        cls.staff_user = cls.env.user
        cls.category = cls.env['bookingpro.category'].create({
            'name': 'Unit Test Consultation',
            'company_id': cls.company.id,
            'website_published': True,
        })
        cls.resource = cls.env['bookingpro.resource'].create({
            'name': 'Unit Test Room',
            'resource_type': 'room',
            'company_id': cls.company.id,
        })
        cls.service = cls.env['bookingpro.service'].create({
            'name': 'Unit Test General Appointment',
            'category_id': cls.category.id,
            'duration': 1.0,
            'price': 50.0,
            'buffer_before': 0.0,
            'buffer_after': 0.0,
            'company_id': cls.company.id,
            'website_published': True,
            'staff_user_ids': [(6, 0, [cls.staff_user.id])],
            'resource_ids': [(6, 0, [cls.resource.id])],
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Unit Test Customer',
            'email': 'bookingpro.unit@example.com',
            'phone': '03000000000',
            'company_id': cls.company.id,
        })

    def _target_date(self, days=7):
        return fields.Date.today() + timedelta(days=days)

    def _ensure_schedule_for_date(self, target_date):
        weekday = str(target_date.weekday())
        return self.env['bookingpro.staff.schedule'].create({
            'staff_user_id': self.staff_user.id,
            'weekday': weekday,
            'hour_from': 9.0,
            'hour_to': 17.0,
            'break_hour_from': 12.0,
            'break_hour_to': 13.0,
            'company_id': self.company.id,
        })

    def _start_dt(self, target_date, hour=9):
        return datetime.combine(target_date, time(hour, 0, 0))

    def _create_appointment(self, start_dt=None, state='confirmed', resource=True):
        start_dt = start_dt or self._start_dt(self._target_date(), 9)
        return self.env['bookingpro.appointment'].create({
            'partner_id': self.partner.id,
            'service_id': self.service.id,
            'staff_user_id': self.staff_user.id,
            'resource_id': self.resource.id if resource else False,
            'start_datetime': start_dt,
            'end_datetime': start_dt + timedelta(hours=1),
            'state': state,
            'company_id': self.company.id,
        })

    def test_01_service_schedule_generates_public_slots(self):
        target_date = self._target_date(8)
        self._ensure_schedule_for_date(target_date)
        slots = self.service.get_available_slots(target_date, staff_user=self.staff_user, resource=self.resource)
        self.assertTrue(slots, 'Expected website slots for scheduled staff/date/resource.')
        self.assertEqual(slots[0]['staff_id'], self.staff_user.id)
        self.assertEqual(slots[0]['resource_id'], self.resource.id)

    def test_02_appointment_creates_calendar_and_crm_lead(self):
        appointment = self._create_appointment(start_dt=self._start_dt(self._target_date(9), 9), state='pending')
        self.assertTrue(appointment.name.startswith('BP/'), 'Appointment sequence should be generated.')
        self.assertTrue(appointment.calendar_event_id, 'Appointment should create/sync a calendar event.')
        self.assertTrue(appointment.crm_lead_id, 'Appointment should create a CRM lead when enabled.')
        self.assertEqual(appointment.crm_lead_id.bookingpro_appointment_id, appointment)

    def test_03_conflict_detection_blocks_same_staff_or_resource_overlap(self):
        start_dt = self._start_dt(self._target_date(10), 9)
        self._create_appointment(start_dt=start_dt, state='confirmed')
        with self.assertRaises(ValidationError):
            self._create_appointment(start_dt=start_dt + timedelta(minutes=30), state='confirmed')

    def test_04_state_flow_completion_schedules_followup(self):
        appointment = self._create_appointment(start_dt=self._start_dt(self._target_date(11), 9), state='confirmed')
        appointment.action_start()
        self.assertEqual(appointment.state, 'in_progress')
        appointment.action_complete()
        self.assertEqual(appointment.state, 'completed')
        self.assertEqual(appointment.followup_state, 'scheduled')
        self.assertTrue(appointment.followup_activity_id)

    def test_05_reschedule_wizard_updates_time_and_history(self):
        appointment = self._create_appointment(start_dt=self._start_dt(self._target_date(12), 9), state='confirmed')
        wizard = self.env['bookingpro.reschedule.wizard'].with_context(
            active_model='bookingpro.appointment', active_id=appointment.id
        ).create({
            'appointment_id': appointment.id,
            'new_start_datetime': appointment.start_datetime + timedelta(hours=2),
            'new_end_datetime': appointment.end_datetime + timedelta(hours=2),
            'reason': 'Unit test reschedule',
        })
        wizard.action_apply_reschedule()
        self.assertEqual(appointment.state, 'rescheduled')
        self.assertEqual(len(appointment.reschedule_history_ids), 1)

    def test_06_reminder_cron_marks_5h_and_1h_flags(self):
        now = fields.Datetime.now()
        appointment_5h = self._create_appointment(start_dt=now + timedelta(hours=4, minutes=30), state='confirmed')
        appointment_1h = self._create_appointment(start_dt=now + timedelta(minutes=45), state='confirmed')
        self.env['bookingpro.appointment'].cron_send_reminders()
        self.assertTrue(appointment_5h.reminder_5h_sent)
        self.assertTrue(appointment_1h.reminder_1h_sent)

    def test_07_readai_requires_configuration(self):
        appointment = self._create_appointment(start_dt=self._start_dt(self._target_date(13), 9), state='confirmed')
        with self.assertRaises(UserError):
            appointment.action_send_to_readai()

    def test_08_company_slug_public_link_resolver(self):
        self.company.bookingpro_slug = 'unit-test-client'
        found = self.env['res.company'].bookingpro_find_by_slug('unit-test-client')
        self.assertEqual(found, self.company)
        self.assertIn('/bookingpro/c/unit-test-client', self.company.bookingpro_public_booking_url)

    def test_09_portal_domain_matches_customer_commercial_partner(self):
        appointment = self._create_appointment(start_dt=self._start_dt(self._target_date(14), 9), state='confirmed')
        domain = [('partner_id', 'child_of', self.partner.commercial_partner_id.id)]
        found = self.env['bookingpro.appointment'].sudo().search(domain)
        self.assertIn(appointment, found)
