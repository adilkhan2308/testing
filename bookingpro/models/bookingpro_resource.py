# -*- coding: utf-8 -*-
from odoo import fields, models


class BookingProResource(models.Model):
    _name = 'bookingpro.resource'
    _description = 'BookingPro Bookable Resource'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    resource_type = fields.Selection([
        ('room', 'Room'),
        ('equipment', 'Equipment'),
        ('table', 'Table'),
        ('vehicle', 'Vehicle'),
        ('court', 'Court'),
        ('machine', 'Machine'),
        ('other', 'Other'),
    ], default='room', required=True, tracking=True)
    description = fields.Text()
    location = fields.Char()
    capacity = fields.Integer(default=1)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    service_ids = fields.Many2many('bookingpro.service', 'bookingpro_service_resource_rel', 'resource_id', 'service_id')
    appointment_ids = fields.One2many('bookingpro.appointment', 'resource_id')
