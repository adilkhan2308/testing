# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BookingProFeedback(models.Model):
    _name = 'bookingpro.feedback'
    _description = 'BookingPro Customer Feedback'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _check_company_auto = True

    appointment_id = fields.Many2one('bookingpro.appointment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='appointment_id.company_id', store=True, readonly=True)
    partner_id = fields.Many2one(related='appointment_id.partner_id', store=True, readonly=True)
    rating = fields.Integer(default=5, tracking=True)
    comments = fields.Text()

    @api.constrains('rating')
    def _check_rating(self):
        for rec in self:
            if rec.rating < 1 or rec.rating > 5:
                raise ValidationError(_('Rating must be between 1 and 5.'))
