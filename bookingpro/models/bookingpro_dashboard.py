# -*- coding: utf-8 -*-
from odoo import fields, models, _


class BookingProDashboard(models.Model):
    _name = 'bookingpro.dashboard'
    _description = 'BookingPro Dashboard'

    total_appointments = fields.Integer(string='Total Appointments', compute='_compute_dashboard_counts')
    upcoming_appointments = fields.Integer(string='Upcoming Appointments', compute='_compute_dashboard_counts')
    pending_appointments = fields.Integer(string='Pending Appointments', compute='_compute_dashboard_counts')
    completed_appointments = fields.Integer(string='Completed Appointments', compute='_compute_dashboard_counts')
    cancelled_appointments = fields.Integer(string='Cancelled Appointments', compute='_compute_dashboard_counts')
    active_services = fields.Integer(string='Active Services', compute='_compute_dashboard_counts')
    active_categories = fields.Integer(string='Service Categories', compute='_compute_dashboard_counts')
    active_resources = fields.Integer(string='Resources', compute='_compute_dashboard_counts')

    def _bookingpro_company_domain(self):
        company_ids = self.env.companies.ids or [self.env.company.id]
        return [('company_id', 'in', company_ids)]

    def _compute_dashboard_counts(self):
        Appointment = self.env['bookingpro.appointment'].sudo()
        Service = self.env['bookingpro.service'].sudo()
        Category = self.env['bookingpro.category'].sudo()
        Resource = self.env['bookingpro.resource'].sudo()
        domain = self._bookingpro_company_domain()
        now = fields.Datetime.now()
        for rec in self:
            rec.total_appointments = Appointment.search_count(domain)
            rec.upcoming_appointments = Appointment.search_count(domain + [('start_datetime', '>=', now), ('state', 'not in', ['cancelled', 'completed', 'no_show'])])
            rec.pending_appointments = Appointment.search_count(domain + [('state', 'in', ['pending', 'reschedule_requested'])])
            rec.completed_appointments = Appointment.search_count(domain + [('state', '=', 'completed')])
            rec.cancelled_appointments = Appointment.search_count(domain + [('state', '=', 'cancelled')])
            rec.active_services = Service.search_count(domain + [('active', '=', True)])
            rec.active_categories = Category.search_count(domain + [('active', '=', True)])
            rec.active_resources = Resource.search_count(domain + [('active', '=', True)])

    def action_open_admin_portal(self):
        return {
            'type': 'ir.actions.act_url',
            'name': _('BookingPro Admin Portal'),
            'url': '/bookingpro/workspace',
            'target': 'self',
        }

    def action_open_public_booking(self):
        return {
            'type': 'ir.actions.act_url',
            'name': _('Public Booking Page'),
            'url': '/bookingpro',
            'target': 'new',
        }

    def action_open_appointments(self):
        return self.env.ref('bookingpro.action_bookingpro_appointment').read()[0]

    def action_open_services(self):
        return self.env.ref('bookingpro.action_bookingpro_service').read()[0]
