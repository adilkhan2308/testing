# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, http, _
from odoo.http import request
from odoo.exceptions import ValidationError


class BookingProWebsite(http.Controller):

    def _get_booking_company(self, company_slug=None):
        if company_slug:
            # Do not search directly on bookingpro_slug here. It is a computed
            # config-parameter-backed value in Odoo 19, and direct domain search
            # can trigger domain optimizer errors in website routes.
            company = request.env['res.company'].sudo().bookingpro_find_by_slug(company_slug)
            return company.exists()
        return request.env.company.sudo()

    def _booking_base_url(self, company=None, company_slug=None):
        if company_slug:
            return '/bookingpro/c/%s' % company_slug
        if company and company.bookingpro_slug:
            return '/bookingpro/c/%s' % company.bookingpro_slug
        return '/bookingpro'

    @http.route([
        '/bookingpro',
        '/bookingpro/services',
        '/bookingpro/c/<string:company_slug>',
        '/bookingpro/c/<string:company_slug>/services',
    ], type='http', auth='public', website=True, sitemap=True)
    def booking_services(self, company_slug=None, **kwargs):
        company = self._get_booking_company(company_slug)
        if not company:
            return request.not_found()
        categories = request.env['bookingpro.category'].sudo().search([
            ('active', '=', True),
            ('website_published', '=', True),
            ('company_id', '=', company.id),
        ])
        services = request.env['bookingpro.service'].sudo().search([
            ('active', '=', True),
            ('website_published', '=', True),
            ('company_id', '=', company.id),
        ])
        return request.render('bookingpro.bookingpro_service_page', {
            'categories': categories,
            'services': services,
            'booking_company': company,
            'booking_base_url': self._booking_base_url(company, company_slug),
        })

    @http.route([
        '/bookingpro/service/<int:service_id>',
        '/bookingpro/c/<string:company_slug>/service/<int:service_id>',
    ], type='http', auth='public', website=True, sitemap=True)
    def booking_service_detail(self, service_id, company_slug=None, **kwargs):
        company = self._get_booking_company(company_slug)
        if not company:
            return request.not_found()
        service = request.env['bookingpro.service'].sudo().browse(service_id).exists()
        if not service or not service.active or not service.website_published or service.company_id.id != company.id:
            return request.not_found()
        staff_users = service.staff_user_ids.sudo()
        resources = service.resource_ids.sudo()
        return request.render('bookingpro.bookingpro_booking_form', {
            'service': service,
            'staff_users': staff_users,
            'resources': resources,
            'today': fields.Date.today(),
            'booking_company': company,
            'booking_base_url': self._booking_base_url(company, company_slug),
        })

    @http.route([
        '/bookingpro/slots',
        '/bookingpro/c/<string:company_slug>/slots',
    ], type='jsonrpc', auth='public', website=True, csrf=False)
    def booking_slots(self, service_id, selected_date, company_slug=None, staff_id=False, resource_id=False, **kwargs):
        company = self._get_booking_company(company_slug)
        if not company:
            return {'success': False, 'error': _('Company not found.')}
        service = request.env['bookingpro.service'].sudo().browse(int(service_id)).exists()
        if not service or service.company_id.id != company.id:
            return {'success': False, 'error': _('Service not found.')}
        try:
            date_obj = fields.Date.from_string(selected_date)
        except Exception:
            return {'success': False, 'error': _('Invalid date.')}
        staff = request.env['res.users'].sudo().browse(int(staff_id)).exists() if staff_id else False
        resource = request.env['bookingpro.resource'].sudo().browse(int(resource_id)).exists() if resource_id else False
        slots = service.get_available_slots(date_obj, staff_user=staff, resource=resource)
        return {'success': True, 'slots': slots}

    @http.route([
        '/bookingpro/confirm',
        '/bookingpro/c/<string:company_slug>/confirm',
    ], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def booking_confirm(self, company_slug=None, **post):
        company = self._get_booking_company(company_slug)
        if not company:
            return request.not_found()
        booking_base_url = self._booking_base_url(company, company_slug)
        required = ['service_id', 'start_datetime', 'end_datetime', 'customer_name', 'customer_email']
        missing = [field for field in required if not post.get(field)]
        if missing:
            return request.render('bookingpro.bookingpro_error_page', {'error': _('Missing required fields: %s') % ', '.join(missing), 'booking_base_url': booking_base_url})

        service = request.env['bookingpro.service'].sudo().browse(int(post.get('service_id'))).exists()
        if not service or service.company_id.id != company.id:
            return request.render('bookingpro.bookingpro_error_page', {'error': _('Service not found.'), 'booking_base_url': booking_base_url})

        partner = self._find_or_create_partner(post, company)
        staff_id = post.get('staff_id') or post.get('slot_staff_id')
        resource_id = post.get('resource_id') or post.get('slot_resource_id')
        staff = request.env['res.users'].sudo().browse(int(staff_id)).exists() if staff_id else False
        resource = request.env['bookingpro.resource'].sudo().browse(int(resource_id)).exists() if resource_id else False

        if staff and service.staff_user_ids and staff not in service.staff_user_ids:
            return request.render('bookingpro.bookingpro_error_page', {'error': _('Selected staff is not allowed for this service.'), 'booking_base_url': booking_base_url})
        if resource and service.resource_ids and resource not in service.resource_ids:
            return request.render('bookingpro.bookingpro_error_page', {'error': _('Selected resource is not allowed for this service.'), 'booking_base_url': booking_base_url})

        try:
            start_dt = fields.Datetime.from_string(post.get('start_datetime'))
            end_dt = fields.Datetime.from_string(post.get('end_datetime'))
        except Exception:
            return request.render('bookingpro.bookingpro_error_page', {'error': _('Invalid appointment time.'), 'booking_base_url': booking_base_url})

        if start_dt >= end_dt:
            return request.render('bookingpro.bookingpro_error_page', {'error': _('Appointment start time must be before end time.'), 'booking_base_url': booking_base_url})

        if request.env['bookingpro.appointment'].sudo().has_conflict(
            start_dt - timedelta(hours=service.buffer_before or 0.0),
            end_dt + timedelta(hours=service.buffer_after or 0.0),
            staff_user_id=staff.id if staff else False,
            resource_id=resource.id if resource else False,
            service=service,
        ):
            return request.render('bookingpro.bookingpro_error_page', {'error': _('This slot is no longer available. Please choose another slot.'), 'booking_base_url': booking_base_url})

        values = {
            'partner_id': partner.id,
            'service_id': service.id,
            'staff_user_id': staff.id if staff else False,
            'resource_id': resource.id if resource else False,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'customer_note': post.get('customer_note'),
            'customer_followup_requested': post.get('customer_followup_requested') in ('on', 'true', 'True', '1', 'yes'),
            'customer_followup_message': post.get('customer_followup_message') or False,
            'followup_note': post.get('customer_followup_message') or False,
            'company_id': company.id,
        }
        require_payment = request.env['ir.config_parameter'].sudo().get_param('bookingpro.require_payment', default='False') == 'True'
        auto_confirm = request.env['ir.config_parameter'].sudo().get_param('bookingpro.auto_confirm', default='False') == 'True'
        values['state'] = 'payment_pending' if require_payment else ('confirmed' if auto_confirm else 'pending')
        values['payment_state'] = 'pending' if require_payment else 'not_required'

        try:
            appointment = request.env['bookingpro.appointment'].sudo().create(values)
            if appointment.state == 'confirmed':
                appointment._send_template('bookingpro.mail_template_appointment_confirmed')
            else:
                appointment._send_template('bookingpro.mail_template_appointment_received')
        except ValidationError as exc:
            return request.render('bookingpro.bookingpro_error_page', {'error': str(exc), 'booking_base_url': booking_base_url})

        return request.redirect('%s/thanks/%s' % (booking_base_url, appointment.id))

    @http.route([
        '/bookingpro/thanks/<int:appointment_id>',
        '/bookingpro/c/<string:company_slug>/thanks/<int:appointment_id>',
    ], type='http', auth='public', website=True, sitemap=False)
    def booking_thanks(self, appointment_id, company_slug=None, **kwargs):
        company = self._get_booking_company(company_slug)
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not appointment or (company and appointment.company_id.id != company.id):
            return request.not_found()
        return request.render('bookingpro.bookingpro_thanks_page', {
            'appointment': appointment,
            'booking_base_url': self._booking_base_url(company, company_slug),
        })

    def _find_or_create_partner(self, post, company):
        Partner = request.env['res.partner'].sudo()
        email = post.get('customer_email')
        phone = post.get('customer_phone')
        identity_domain = []
        if email and phone:
            identity_domain = ['|', ('email', '=', email), ('phone', '=', phone)]
        elif email:
            identity_domain = [('email', '=', email)]
        elif phone:
            identity_domain = [('phone', '=', phone)]
        domain = ['&', '|', ('company_id', '=', False), ('company_id', '=', company.id)] + identity_domain if identity_domain else []
        partner = Partner.search(domain, limit=1) if domain else False
        if not partner:
            partner = Partner.create({
                'name': post.get('customer_name'),
                'email': email,
                'phone': phone,
                'company_type': 'person',
                'company_id': company.id,
            })
        else:
            updates = {}
            if email and not partner.email:
                updates['email'] = email
            if phone and not partner.phone:
                updates['phone'] = phone
            if not partner.company_id:
                updates['company_id'] = company.id
            if updates:
                partner.write(updates)
        return partner
