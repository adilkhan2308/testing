# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    bookingpro_appointment_id = fields.Many2one('bookingpro.appointment', string='BookingPro Appointment', ondelete='set null')
    bookingpro_service_id = fields.Many2one(related='bookingpro_appointment_id.service_id', string='BookingPro Service', store=True, readonly=True)
    bookingpro_start_datetime = fields.Datetime(related='bookingpro_appointment_id.start_datetime', string='BookingPro Appointment Time', store=True, readonly=True)
