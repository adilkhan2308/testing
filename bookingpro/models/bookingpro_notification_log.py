# -*- coding: utf-8 -*-
from odoo import fields, models


class BookingProNotificationLog(models.Model):
    _name = 'bookingpro.notification.log'
    _description = 'BookingPro Notification Log'
    _order = 'create_date desc'
    _check_company_auto = True

    appointment_id = fields.Many2one('bookingpro.appointment', ondelete='cascade')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner')
    notification_type = fields.Char(required=True)
    channel = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('internal', 'Internal'),
        ('read_ai', 'Read.ai'),
    ], default='email', required=True)
    recipient = fields.Char()
    state = fields.Selection([
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], default='queued')
    sent_date = fields.Datetime()
    error_message = fields.Text()
