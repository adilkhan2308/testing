# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bookingpro_appointment_ids = fields.One2many('bookingpro.appointment', 'partner_id', string='Appointments')
    bookingpro_appointment_count = fields.Integer(compute='_compute_bookingpro_appointment_count')
    bookingpro_last_appointment_id = fields.Many2one('bookingpro.appointment', compute='_compute_bookingpro_last_appointment')
    bookingpro_preferred_service_ids = fields.Many2many(
        'bookingpro.service',
        'bookingpro_partner_service_rel',
        'partner_id',
        'service_id',
        string='Preferred Booking Services',
    )
    bookingpro_customer_note = fields.Text(string='BookingPro Internal Customer Note')

    @api.depends('bookingpro_appointment_ids')
    def _compute_bookingpro_appointment_count(self):
        for partner in self:
            partner.bookingpro_appointment_count = len(partner.bookingpro_appointment_ids)

    def _compute_bookingpro_last_appointment(self):
        Appointment = self.env['bookingpro.appointment']
        for partner in self:
            partner.bookingpro_last_appointment_id = Appointment.search([
                ('partner_id', '=', partner.id),
            ], order='start_datetime desc', limit=1)

    def action_view_bookingpro_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'bookingpro.appointment',
            'view_mode': 'list,calendar,form,kanban,pivot,graph',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
