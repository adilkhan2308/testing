# -*- coding: utf-8 -*-
from odoo import fields, models


class BookingProRescheduleHistory(models.Model):
    _name = 'bookingpro.reschedule.history'
    _description = 'BookingPro Reschedule History'
    _order = 'create_date desc'
    _check_company_auto = True

    appointment_id = fields.Many2one('bookingpro.appointment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='appointment_id.company_id', store=True, readonly=True)
    old_start_datetime = fields.Datetime(required=True)
    old_end_datetime = fields.Datetime(required=True)
    new_start_datetime = fields.Datetime(required=True)
    new_end_datetime = fields.Datetime(required=True)
    requested_by_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    reason = fields.Text()
    approval_state = fields.Selection([
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='approved')
