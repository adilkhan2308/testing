# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # IMPORTANT FOR ODOO 19:
    # Do not store this field as a DB column. During module upgrade Odoo may read
    # res.company before the column is created, which causes:
    # psycopg2.errors.UndefinedColumn: column res_company.bookingpro_slug does not exist
    # We keep it as a computed/inverse field backed by ir.config_parameter.
    bookingpro_slug = fields.Char(
        string='BookingPro Client Slug',
        compute='_compute_bookingpro_slug',
        inverse='_inverse_bookingpro_slug',
        search='_search_bookingpro_slug',
        readonly=False,
        help='Unique slug used in the public booking link, for example /bookingpro/c/my-company.'
    )
    bookingpro_public_booking_url = fields.Char(
        string='BookingPro Public Booking URL',
        compute='_compute_bookingpro_public_booking_url',
        readonly=True,
    )

    def _bookingpro_slug_param_key(self):
        self.ensure_one()
        return 'bookingpro.company.%s.slug' % self.id

    def _bookingpro_slugify(self, value):
        value = (value or '').strip().lower()
        value = re.sub(r'[^a-z0-9]+', '-', value)
        value = value.strip('-')
        return value or 'company-%s' % (self.id or 'new')

    def _get_bookingpro_slug_from_param(self):
        self.ensure_one()
        param = self.env['ir.config_parameter'].sudo()
        slug = param.get_param(self._bookingpro_slug_param_key())
        if not slug:
            slug = self._bookingpro_slugify(self.name)
        return slug

    @api.depends('name')
    def _compute_bookingpro_slug(self):
        for company in self:
            company.bookingpro_slug = company._get_bookingpro_slug_from_param()

    def _inverse_bookingpro_slug(self):
        param = self.env['ir.config_parameter'].sudo()
        for company in self:
            slug = company._bookingpro_slugify(company.bookingpro_slug or company.name)
            # Keep slugs unique across companies by appending the company id when needed.
            for other in self.env['res.company'].sudo().search([('id', '!=', company.id)]):
                if other._get_bookingpro_slug_from_param() == slug:
                    slug = '%s-%s' % (slug, company.id)
                    break
            param.set_param(company._bookingpro_slug_param_key(), slug)

    def _normalise_slug_search_values(self, value):
        # Odoo 19 domain optimisation can call computed-field search methods with
        # non-string values such as OrderedSet. Keep this method defensive so the
        # public website never crashes while resolving client booking links.
        if value is False or value is None:
            return ['']
        if isinstance(value, str):
            return [value.strip().lower()]
        try:
            values = list(value)
        except TypeError:
            values = [value]
        return [str(item or '').strip().lower() for item in values]

    def _search_bookingpro_slug(self, operator, value):
        values = self._normalise_slug_search_values(value)
        matched_ids = []
        for company in self.env['res.company'].sudo().search([]):
            slug = (company._get_bookingpro_slug_from_param() or '').strip().lower()
            if operator in ('=', '==', 'in') and slug in values:
                matched_ids.append(company.id)
            elif operator in ('!=', '<>', 'not in') and slug not in values:
                matched_ids.append(company.id)
            elif operator in ('ilike', 'like') and any(item in slug for item in values):
                matched_ids.append(company.id)
            elif operator in ('not ilike', 'not like') and all(item not in slug for item in values):
                matched_ids.append(company.id)
        return [('id', 'in', matched_ids)]

    def bookingpro_find_by_slug(self, slug):
        slug = self._bookingpro_slugify(slug)
        for company in self.sudo().search([]):
            if (company._get_bookingpro_slug_from_param() or '').strip().lower() == slug:
                return company
        return self.browse()

    @api.depends('bookingpro_slug')
    def _compute_bookingpro_public_booking_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for company in self:
            slug = company.bookingpro_slug or company._bookingpro_slugify(company.name)
            company.bookingpro_public_booking_url = '%s/bookingpro/c/%s' % (base_url.rstrip('/'), slug)

    def action_bookingpro_open_public_link(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.bookingpro_public_booking_url or '/bookingpro',
            'target': 'new',
        }
