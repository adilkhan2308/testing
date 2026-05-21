# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BookingProCategory(models.Model):
    _name = 'bookingpro.category'
    _description = 'BookingPro Service Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    service_ids = fields.One2many('bookingpro.service', 'category_id', string='Services')
    service_count = fields.Integer(compute='_compute_service_count')
    website_published = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(default=0)

    _name_company_unique = models.Constraint(
        'UNIQUE(name, company_id)',
        'The service category must be unique per company.',
    )

    @api.depends('service_ids')
    def _compute_service_count(self):
        for rec in self:
            rec.service_count = len(rec.service_ids)
