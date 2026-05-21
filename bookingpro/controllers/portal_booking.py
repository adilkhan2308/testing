# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import UserError, ValidationError


class BookingProPortal(CustomerPortal):
    """Customer portal + BookingPro workspace portal.

    Customer users see only their own appointments under /my/bookingpro.
    Internal BookingPro users can manage the operational data from website-style
    portal pages under /bookingpro/workspace, so the backend flow is also
    available from a simple portal UI.
    """

    # -------------------------------------------------------------------------
    # Generic helpers
    # -------------------------------------------------------------------------
    def _is_bookingpro_internal_user(self):
        user = request.env.user
        return bool(
            user.has_group('bookingpro.group_bookingpro_manager')
            or user.has_group('bookingpro.group_bookingpro_booking_manager')
            or user.has_group('bookingpro.group_bookingpro_staff')
            or user.has_group('base.group_system')
        )

    def _is_bookingpro_manager(self):
        user = request.env.user
        return bool(
            user.has_group('bookingpro.group_bookingpro_manager')
            or user.has_group('bookingpro.group_bookingpro_booking_manager')
            or user.has_group('base.group_system')
        )

    def _require_bookingpro_internal(self):
        if not self._is_bookingpro_internal_user():
            return request.not_found()
        return False

    def _role_label(self):
        if self._is_bookingpro_manager():
            return _('Admin / Booking Manager')
        if request.env.user.has_group('bookingpro.group_bookingpro_staff'):
            return _('Staff')
        return _('Client')

    def _workspace_company(self):
        return request.env.company.sudo()

    def _workspace_domain(self):
        company = self._workspace_company()
        return [('company_id', '=', company.id)]

    def _to_int(self, value):
        try:
            return int(value) if value not in (None, '', False) else False
        except Exception:
            return False

    def _to_float_time(self, value, default=0.0):
        if value in (None, '', False):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        value = str(value).strip()
        if ':' in value:
            hours, minutes = value.split(':', 1)
            try:
                return int(hours) + (int(minutes[:2]) / 60.0)
            except Exception:
                return default
        try:
            return float(value)
        except Exception:
            return default

    def _checkbox(self, post, name, default=False):
        if name in post:
            return post.get(name) in ('on', 'true', 'True', '1', 'yes')
        return default

    def _parse_datetime_local(self, value):
        if not value:
            return False
        value = value.replace('T', ' ')
        if len(value) == 16:
            value = value + ':00'
        return fields.Datetime.from_string(value)

    def _find_or_create_partner_from_portal(self, post, company):
        Partner = request.env['res.partner'].sudo()
        email = (post.get('customer_email') or '').strip()
        phone = (post.get('customer_phone') or '').strip()
        name = (post.get('customer_name') or email or phone or _('Portal Customer')).strip()
        domain = []
        if email and phone:
            domain = ['|', ('email', '=', email), ('phone', '=', phone)]
        elif email:
            domain = [('email', '=', email)]
        elif phone:
            domain = [('phone', '=', phone)]
        partner = Partner.search(domain, limit=1) if domain else False
        if not partner:
            partner = Partner.create({
                'name': name,
                'email': email,
                'phone': phone,
                'company_type': 'person',
                'company_id': company.id,
            })
        else:
            updates = {}
            if name and not partner.name:
                updates['name'] = name
            if email and not partner.email:
                updates['email'] = email
            if phone and not partner.phone:
                updates['phone'] = phone
            if not partner.company_id:
                updates['company_id'] = company.id
            if updates:
                partner.write(updates)
        return partner

    def _workspace_base_values(self, **extra):
        company = self._workspace_company()
        ICP = request.env['ir.config_parameter'].sudo()
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'bookingpro_workspace',
            'bookingpro_role': self._role_label(),
            'bookingpro_is_manager': self._is_bookingpro_manager(),
            'bookingpro_is_staff': self._is_bookingpro_internal_user(),
            'bookingpro_company': company,
            'bookingpro_public_url': company.bookingpro_public_booking_url,
            'bookingpro_settings': {
                'auto_confirm': ICP.get_param('bookingpro.auto_confirm', default='False') == 'True',
                'require_payment': ICP.get_param('bookingpro.require_payment', default='False') == 'True',
                'create_crm_lead': ICP.get_param('bookingpro.create_crm_lead', default='True') == 'True',
                'auto_followup': ICP.get_param('bookingpro.auto_followup_on_completion', default='True') == 'True',
                'enable_customer_followup': ICP.get_param('bookingpro.enable_customer_followup', default='True') == 'True',
                'auto_customer_followup_on_booking': ICP.get_param('bookingpro.auto_customer_followup_on_booking', default='True') == 'True',
                'send_customer_followup_email_on_booking': ICP.get_param('bookingpro.send_customer_followup_email_on_booking', default='True') == 'True',
                'send_customer_followup_after_completion': ICP.get_param('bookingpro.send_customer_followup_after_completion', default='True') == 'True',
                'create_internal_activity_for_customer_followup': ICP.get_param('bookingpro.create_internal_activity_for_customer_followup', default='True') == 'True',
                'customer_followup_email_delay_hours': ICP.get_param('bookingpro.customer_followup_email_delay_hours', default='0'),
                'customer_followup_interval_hours': ICP.get_param('bookingpro.customer_followup_interval_hours', default='1'),
                'customer_followup_max_emails': ICP.get_param('bookingpro.customer_followup_max_emails', default='3'),
                'enable_reminders': ICP.get_param('bookingpro.enable_email_reminders', default='True') == 'True',
                'send_5h': ICP.get_param('bookingpro.send_5h_reminder', default='True') == 'True',
                'send_1h': ICP.get_param('bookingpro.send_1h_reminder', default='True') == 'True',
                'readai_enabled': ICP.get_param('bookingpro.readai_enabled', default='False') == 'True',
                'readai_api_url': ICP.get_param('bookingpro.readai_api_url', default=''),
                'smtp_mail_server_id': ICP.get_param('bookingpro.mail_server_id.company_%s' % company.id, default=ICP.get_param('bookingpro.mail_server_id', default='')),
                'smtp_from_email': ICP.get_param('bookingpro.smtp_from_email.company_%s' % company.id, default=ICP.get_param('bookingpro.smtp_from_email', default=company.email or '')),
                'smtp_from_name': ICP.get_param('bookingpro.smtp_from_name.company_%s' % company.id, default=ICP.get_param('bookingpro.smtp_from_name', default=company.name or 'BookingPro')),
                'slot_step_minutes': ICP.get_param('bookingpro.slot_step_minutes', default='30'),
                'followup_delay_days': ICP.get_param('bookingpro.followup_delay_days', default='1'),
            },
        })
        values.update(extra)
        return values

    # -------------------------------------------------------------------------
    # Portal home / customer portal
    # -------------------------------------------------------------------------
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'bookingpro_count' in counters:
            Appointment = request.env['bookingpro.appointment'].sudo()
            if self._is_bookingpro_internal_user():
                values['bookingpro_count'] = Appointment.search_count(self._workspace_domain())
            else:
                partner = request.env.user.partner_id
                values['bookingpro_count'] = Appointment.search_count([
                    ('partner_id', 'child_of', partner.commercial_partner_id.id),
                ])
        return values

    @http.route(['/my/bookingpro', '/my/bookingpro/', '/my/bookingpro/page/<int:page>'], type='http', auth='user', website=True, sitemap=False)
    def portal_my_bookingpro(self, page=1, sortby='date', filterby='all', **kw):
        Appointment = request.env['bookingpro.appointment'].sudo()
        partner = request.env.user.partner_id
        domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]
        if filterby != 'all':
            domain.append(('state', '=', filterby))

        sortings = {
            'date': {'label': _('Date'), 'order': 'start_datetime desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'status': {'label': _('Status'), 'order': 'state, start_datetime desc'},
        }
        filters = {
            'all': {'label': _('All')},
            'pending': {'label': _('Pending')},
            'confirmed': {'label': _('Confirmed')},
            'completed': {'label': _('Completed')},
            'cancelled': {'label': _('Cancelled')},
        }
        order = sortings.get(sortby, sortings['date'])['order']
        total = Appointment.search_count(domain)
        base_domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]
        now = fields.Datetime.now()
        customer_portal_stats = {
            'total': Appointment.search_count(base_domain),
            'upcoming': Appointment.search_count(base_domain + [('start_datetime', '>=', now), ('state', 'not in', ['cancelled', 'completed', 'no_show'])]),
            'completed': Appointment.search_count(base_domain + [('state', '=', 'completed')]),
            'followups': Appointment.search_count(base_domain + [('customer_followup_requested', '=', True), ('customer_followup_state', 'not in', ['none', 'done', 'stopped'])]),
        }
        pager = portal_pager(url='/my/bookingpro', total=total, page=page, step=20, url_args={'sortby': sortby, 'filterby': filterby})
        appointments = Appointment.search(domain, order=order, limit=20, offset=pager['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'appointments': appointments,
            'customer_portal_stats': customer_portal_stats,
            'page_name': 'bookingpro',
            'pager': pager,
            'sortings': sortings,
            'filters': filters,
            'sortby': sortby,
            'filterby': filterby,
            'bookingpro_is_internal': self._is_bookingpro_internal_user(),
            'bookingpro_public_url': request.env.company.sudo().bookingpro_public_booking_url,
        })
        return request.render('bookingpro.portal_my_bookingpro', values)

    @http.route('/my/bookingpro/<int:appointment_id>', type='http', auth='user', website=True)
    def portal_bookingpro_detail(self, appointment_id, **kw):
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not appointment or appointment.partner_id.commercial_partner_id != request.env.user.partner_id.commercial_partner_id:
            return request.not_found()
        values = self._prepare_portal_layout_values()
        values.update({
            'appointment': appointment,
            'page_name': 'bookingpro',
            'followup_error': False,
            'followup_saved': kw.get('followup'),
            'bookingpro_public_url': request.env.company.sudo().bookingpro_public_booking_url,
        })
        return request.render('bookingpro.portal_bookingpro_detail', values)

    @http.route('/my/bookingpro/<int:appointment_id>/followup', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bookingpro_followup_request(self, appointment_id, message='', **kw):
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not appointment or appointment.partner_id.commercial_partner_id != request.env.user.partner_id.commercial_partner_id:
            return request.not_found()
        try:
            appointment.action_request_customer_followup(message=message or appointment.customer_followup_message)
        except (UserError, ValidationError) as exc:
            values = self._prepare_portal_layout_values()
            values.update({
                'appointment': appointment,
                'page_name': 'bookingpro',
                'followup_error': str(exc),
                'bookingpro_public_url': request.env.company.sudo().bookingpro_public_booking_url,
            })
            return request.render('bookingpro.portal_bookingpro_detail', values)
        return request.redirect('/my/bookingpro/%s?followup=1' % appointment.id)

    @http.route('/my/bookingpro/<int:appointment_id>/cancel', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bookingpro_cancel(self, appointment_id, reason='', **kw):
        allowed = request.env['ir.config_parameter'].sudo().get_param('bookingpro.allow_portal_cancel', default='True') == 'True'
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not allowed or not appointment or appointment.partner_id.commercial_partner_id != request.env.user.partner_id.commercial_partner_id:
            return request.not_found()
        appointment.write({'state': 'cancelled', 'cancellation_reason': reason})
        return request.redirect('/my/bookingpro/%s' % appointment.id)

    @http.route('/my/bookingpro/<int:appointment_id>/reschedule-request', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bookingpro_reschedule_request(self, appointment_id, reason='', **kw):
        allowed = request.env['ir.config_parameter'].sudo().get_param('bookingpro.allow_portal_reschedule', default='True') == 'True'
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not allowed or not appointment or appointment.partner_id.commercial_partner_id != request.env.user.partner_id.commercial_partner_id:
            return request.not_found()
        appointment.write({'state': 'reschedule_requested', 'reschedule_reason': reason})
        return request.redirect('/my/bookingpro/%s' % appointment.id)

    # -------------------------------------------------------------------------
    # BookingPro workspace portal for internal admin/staff users
    # -------------------------------------------------------------------------
    @http.route(['/bookingpro/workspace', '/my/bookingpro/workspace'], type='http', auth='user', website=True)
    def workspace_dashboard(self, **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        domain = self._workspace_domain()
        Appointment = request.env['bookingpro.appointment'].sudo()
        now = fields.Datetime.now()
        values = self._workspace_base_values(
            page_section='dashboard',
            total_appointments=Appointment.search_count(domain),
            pending_count=Appointment.search_count(domain + [('state', '=', 'pending')]),
            confirmed_count=Appointment.search_count(domain + [('state', 'in', ['confirmed', 'rescheduled', 'paid'])]),
            completed_count=Appointment.search_count(domain + [('state', '=', 'completed')]),
            cancelled_count=Appointment.search_count(domain + [('state', '=', 'cancelled')]),
            upcoming_appointments=Appointment.search(domain + [('start_datetime', '>=', now)], order='start_datetime asc', limit=10),
            pending_appointments=Appointment.search(domain + [('state', 'in', ['pending', 'reschedule_requested'])], order='start_datetime asc', limit=10),
            services=request.env['bookingpro.service'].sudo().search(domain, order='sequence, name', limit=10),
            schedules=request.env['bookingpro.staff.schedule'].sudo().search(domain, order='weekday, hour_from', limit=10),
            leads=request.env['crm.lead'].sudo().search(domain + [('bookingpro_appointment_id', '!=', False)], order='create_date desc', limit=10),
        )
        return request.render('bookingpro.portal_workspace_dashboard', values)

    @http.route('/bookingpro/workspace/services', type='http', auth='user', website=True)
    def workspace_services(self, **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        domain = self._workspace_domain()
        Service = request.env['bookingpro.service'].sudo()
        Category = request.env['bookingpro.category'].sudo()
        selected_service = Service.browse(self._to_int(kw.get('edit_service_id'))).exists()
        if selected_service and selected_service.company_id.id != self._workspace_company().id:
            selected_service = False
        selected_category = Category.browse(self._to_int(kw.get('edit_category_id'))).exists()
        if selected_category and selected_category.company_id.id != self._workspace_company().id:
            selected_category = False
        values = self._workspace_base_values(
            page_section='services',
            services=Service.search(domain, order='sequence, name'),
            categories=Category.search(domain, order='sequence, name'),
            resources=request.env['bookingpro.resource'].sudo().search(domain, order='sequence, name'),
            staff_users=request.env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)], order='name'),
            selected_service=selected_service,
            selected_category=selected_category,
        )
        return request.render('bookingpro.portal_workspace_services', values)

    @http.route('/bookingpro/workspace/category/save', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_category_save(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        Category = request.env['bookingpro.category'].sudo()
        company = self._workspace_company()
        category_id = self._to_int(post.get('category_id'))
        values = {
            'name': post.get('name') or _('New Category'),
            'description': post.get('description') or False,
            'sequence': self._to_int(post.get('sequence')) or 10,
            'website_published': self._checkbox(post, 'website_published', default=False),
            'active': self._checkbox(post, 'active', default=True),
            'company_id': company.id,
        }
        if category_id:
            category = Category.browse(category_id).exists()
            if category and category.company_id.id == company.id:
                category.write(values)
        else:
            Category.create(values)
        return request.redirect('/bookingpro/workspace/services')

    @http.route('/bookingpro/workspace/service/save', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_service_save(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        Service = request.env['bookingpro.service'].sudo()
        company = self._workspace_company()
        service_id = self._to_int(post.get('service_id'))
        staff_ids = [self._to_int(item) for item in request.httprequest.form.getlist('staff_user_ids')]
        resource_ids = [self._to_int(item) for item in request.httprequest.form.getlist('resource_ids')]
        values = {
            'name': post.get('name') or _('New Service'),
            'category_id': self._to_int(post.get('category_id')),
            'description': post.get('description') or False,
            'duration': float(post.get('duration') or 1.0),
            'price': float(post.get('price') or 0.0),
            'buffer_before': float(post.get('buffer_before') or 0.0),
            'buffer_after': float(post.get('buffer_after') or 0.0),
            'capacity': self._to_int(post.get('capacity')) or 1,
            'sequence': self._to_int(post.get('sequence')) or 10,
            'website_published': self._checkbox(post, 'website_published', default=False),
            'active': self._checkbox(post, 'active', default=True),
            'company_id': company.id,
            'staff_user_ids': [(6, 0, [item for item in staff_ids if item])],
            'resource_ids': [(6, 0, [item for item in resource_ids if item])],
        }
        if not values['category_id']:
            raise UserError(_('Category is required.'))
        if service_id:
            service = Service.browse(service_id).exists()
            if service and service.company_id.id == company.id:
                service.write(values)
        else:
            Service.create(values)
        return request.redirect('/bookingpro/workspace/services')

    @http.route('/bookingpro/workspace/resources', type='http', auth='user', website=True)
    def workspace_resources(self, **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        domain = self._workspace_domain()
        Resource = request.env['bookingpro.resource'].sudo()
        selected_resource = Resource.browse(self._to_int(kw.get('edit_resource_id'))).exists()
        if selected_resource and selected_resource.company_id.id != self._workspace_company().id:
            selected_resource = False
        values = self._workspace_base_values(
            page_section='resources',
            resources=Resource.search(domain, order='sequence, name'),
            services=request.env['bookingpro.service'].sudo().search(domain, order='sequence, name'),
            selected_resource=selected_resource,
        )
        return request.render('bookingpro.portal_workspace_resources', values)

    @http.route('/bookingpro/workspace/resource/save', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_resource_save(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        Resource = request.env['bookingpro.resource'].sudo()
        company = self._workspace_company()
        resource_id = self._to_int(post.get('resource_id'))
        service_ids = [self._to_int(item) for item in request.httprequest.form.getlist('service_ids')]
        values = {
            'name': post.get('name') or _('New Resource'),
            'resource_type': post.get('resource_type') or 'room',
            'description': post.get('description') or False,
            'location': post.get('location') or False,
            'capacity': self._to_int(post.get('capacity')) or 1,
            'sequence': self._to_int(post.get('sequence')) or 10,
            'active': self._checkbox(post, 'active', default=True),
            'company_id': company.id,
            'service_ids': [(6, 0, [item for item in service_ids if item])],
        }
        if resource_id:
            resource = Resource.browse(resource_id).exists()
            if resource and resource.company_id.id == company.id:
                resource.write(values)
        else:
            Resource.create(values)
        return request.redirect('/bookingpro/workspace/resources')

    @http.route('/bookingpro/workspace/availability', type='http', auth='user', website=True)
    def workspace_availability(self, **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        domain = self._workspace_domain()
        Schedule = request.env['bookingpro.staff.schedule'].sudo()
        selected_schedule = Schedule.browse(self._to_int(kw.get('edit_schedule_id'))).exists()
        if selected_schedule and selected_schedule.company_id.id != self._workspace_company().id:
            selected_schedule = False
        values = self._workspace_base_values(
            page_section='availability',
            schedules=Schedule.search(domain, order='staff_user_id, weekday, hour_from'),
            staff_users=request.env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)], order='name'),
            weekdays=request.env['bookingpro.staff.schedule']._fields['weekday'].selection,
            selected_schedule=selected_schedule,
        )
        return request.render('bookingpro.portal_workspace_availability', values)

    @http.route('/bookingpro/workspace/availability/save', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_availability_save(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        Schedule = request.env['bookingpro.staff.schedule'].sudo()
        company = self._workspace_company()
        schedule_id = self._to_int(post.get('schedule_id'))
        values = {
            'staff_user_id': self._to_int(post.get('staff_user_id')),
            'weekday': post.get('weekday') or '0',
            'hour_from': self._to_float_time(post.get('hour_from'), 9.0),
            'hour_to': self._to_float_time(post.get('hour_to'), 17.0),
            'break_hour_from': self._to_float_time(post.get('break_hour_from'), 0.0),
            'break_hour_to': self._to_float_time(post.get('break_hour_to'), 0.0),
            'active': self._checkbox(post, 'active', default=True),
            'notes': post.get('notes') or False,
            'company_id': company.id,
        }
        if schedule_id:
            schedule = Schedule.browse(schedule_id).exists()
            if schedule and schedule.company_id.id == company.id:
                schedule.write(values)
        else:
            Schedule.create(values)
        return request.redirect('/bookingpro/workspace/availability')

    @http.route(['/bookingpro/workspace/appointments', '/bookingpro/workspace/appointments/page/<int:page>'], type='http', auth='user', website=True)
    def workspace_appointments(self, page=1, filterby='all', **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        Appointment = request.env['bookingpro.appointment'].sudo()
        domain = self._workspace_domain()
        if not self._is_bookingpro_manager():
            domain += ['|', ('staff_user_id', '=', request.env.user.id), ('staff_user_id', '=', False)]
        if filterby != 'all':
            domain.append(('state', '=', filterby))
        total = Appointment.search_count(domain)
        pager = portal_pager(url='/bookingpro/workspace/appointments', total=total, page=page, step=25, url_args={'filterby': filterby})
        filters = {
            'all': {'label': _('All')},
            'pending': {'label': _('Pending')},
            'confirmed': {'label': _('Confirmed')},
            'reschedule_requested': {'label': _('Reschedule Requested')},
            'completed': {'label': _('Completed')},
            'cancelled': {'label': _('Cancelled')},
        }
        company = self._workspace_company()
        values = self._workspace_base_values(
            page_section='appointments',
            appointments=Appointment.search(domain, order='start_datetime desc', limit=25, offset=pager['offset']),
            pager=pager,
            filters=filters,
            filterby=filterby,
            services=request.env['bookingpro.service'].sudo().search([('company_id', '=', company.id), ('active', '=', True)], order='sequence, name'),
            resources=request.env['bookingpro.resource'].sudo().search([('company_id', '=', company.id), ('active', '=', True)], order='sequence, name'),
            staff_users=request.env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)], order='name'),
        )
        return request.render('bookingpro.portal_workspace_appointments', values)

    @http.route('/bookingpro/workspace/appointment/save', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_appointment_save(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        company = self._workspace_company()
        Appointment = request.env['bookingpro.appointment'].sudo()
        service = request.env['bookingpro.service'].sudo().browse(self._to_int(post.get('service_id'))).exists()
        if not service or service.company_id.id != company.id:
            raise UserError(_('Valid service is required.'))
        partner = self._find_or_create_partner_from_portal(post, company)
        start_dt = self._parse_datetime_local(post.get('start_datetime'))
        end_dt = self._parse_datetime_local(post.get('end_datetime'))
        if not end_dt and start_dt:
            end_dt = start_dt + timedelta(hours=service.duration or 1.0)
        values = {
            'partner_id': partner.id,
            'service_id': service.id,
            'staff_user_id': self._to_int(post.get('staff_user_id')) or False,
            'resource_id': self._to_int(post.get('resource_id')) or False,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'customer_note': post.get('customer_note') or False,
            'customer_followup_requested': self._checkbox(post, 'customer_followup_requested', default=True),
            'customer_followup_message': post.get('customer_followup_message') or False,
            'followup_note': post.get('customer_followup_message') or False,
            'state': post.get('state') or 'pending',
            'company_id': company.id,
        }
        appointment_id = self._to_int(post.get('appointment_id'))
        if appointment_id:
            appointment = Appointment.browse(appointment_id).exists()
            if not appointment or appointment.company_id.id != company.id:
                return request.not_found()
            appointment.write(values)
        else:
            appointment = Appointment.create(values)
        return request.redirect('/bookingpro/workspace/appointment/%s' % appointment.id)

    @http.route('/bookingpro/workspace/appointment/<int:appointment_id>', type='http', auth='user', website=True)
    def workspace_appointment_detail(self, appointment_id, **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not appointment or appointment.company_id.id != self._workspace_company().id:
            return request.not_found()
        if not self._is_bookingpro_manager() and appointment.staff_user_id and appointment.staff_user_id.id != request.env.user.id:
            return request.not_found()
        values = self._workspace_base_values(page_section='appointments', appointment=appointment)
        return request.render('bookingpro.portal_workspace_appointment_detail', values)

    @http.route('/bookingpro/workspace/appointment/<int:appointment_id>/action', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_appointment_action(self, appointment_id, action='', **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not appointment or appointment.company_id.id != self._workspace_company().id:
            return request.not_found()
        if not self._is_bookingpro_manager() and appointment.staff_user_id and appointment.staff_user_id.id != request.env.user.id:
            return request.not_found()
        try:
            if action == 'confirm':
                appointment.action_confirm()
            elif action == 'start':
                appointment.action_start()
            elif action == 'complete':
                appointment.action_complete()
            elif action == 'cancel':
                appointment.write({'cancellation_reason': post.get('reason') or appointment.cancellation_reason})
                appointment.action_cancel()
            elif action == 'no_show':
                appointment.action_no_show()
            elif action == 'followup':
                appointment.write({'followup_note': post.get('followup_note') or appointment.followup_note})
                appointment.action_schedule_followup()
            elif action == 'customer_followup':
                appointment.action_request_customer_followup(message=post.get('customer_followup_message') or appointment.customer_followup_message)
            elif action == 'send_customer_followup_email':
                if post.get('customer_followup_message'):
                    appointment.write({'customer_followup_message': post.get('customer_followup_message')})
                appointment.action_send_customer_followup_email()
            elif action == 'mark_customer_followup_done':
                appointment.action_mark_customer_followup_done()
            elif action == 'mark_followup_done':
                appointment.action_mark_followup_done()
            elif action == 'send_readai':
                if post.get('read_ai_meeting_url'):
                    appointment.write({'read_ai_meeting_url': post.get('read_ai_meeting_url')})
                appointment.action_send_to_readai()
            elif action == 'reschedule':
                new_start = self._parse_datetime_local(post.get('new_start_datetime'))
                new_end = self._parse_datetime_local(post.get('new_end_datetime'))
                if not new_end and new_start:
                    new_end = new_start + timedelta(hours=appointment.service_id.duration or 1.0)
                if not new_start or not new_end:
                    raise UserError(_('New appointment time is required.'))
                if request.env['bookingpro.appointment'].sudo().has_conflict(
                    new_start,
                    new_end,
                    staff_user_id=appointment.staff_user_id.id,
                    resource_id=appointment.resource_id.id,
                    service=appointment.service_id,
                    exclude_appointment_id=appointment.id,
                ):
                    raise UserError(_('The selected new time conflicts with another booking.'))
                request.env['bookingpro.reschedule.history'].sudo().create({
                    'appointment_id': appointment.id,
                    'old_start_datetime': appointment.start_datetime,
                    'old_end_datetime': appointment.end_datetime,
                    'new_start_datetime': new_start,
                    'new_end_datetime': new_end,
                    'reason': post.get('reason') or False,
                    'requested_by_id': request.env.user.id,
                    'approval_state': 'approved',
                })
                appointment.write({
                    'start_datetime': new_start,
                    'end_datetime': new_end,
                    'reschedule_reason': post.get('reason') or False,
                    'state': 'rescheduled',
                })
                appointment._send_template('bookingpro.mail_template_appointment_rescheduled')
        except (UserError, ValidationError) as exc:
            return request.render('bookingpro.portal_workspace_error', self._workspace_base_values(error_message=str(exc)))
        return request.redirect('/bookingpro/workspace/appointment/%s' % appointment.id)

    @http.route('/bookingpro/workspace/appointment/<int:appointment_id>/note', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def workspace_appointment_note(self, appointment_id, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        appointment = request.env['bookingpro.appointment'].sudo().browse(appointment_id).exists()
        if not appointment or appointment.company_id.id != self._workspace_company().id:
            return request.not_found()
        values = {
            'internal_note': post.get('internal_note') or False,
            'customer_note': post.get('customer_note') or False,
            'read_ai_meeting_url': post.get('read_ai_meeting_url') or False,
            'followup_note': post.get('followup_note') or False,
            'customer_followup_message': post.get('customer_followup_message') or False,
            'customer_followup_requested': self._checkbox(post, 'customer_followup_requested', default=appointment.customer_followup_requested),
        }
        appointment.write(values)
        return request.redirect('/bookingpro/workspace/appointment/%s' % appointment.id)

    @http.route('/bookingpro/workspace/leads', type='http', auth='user', website=True)
    def workspace_leads(self, **kw):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        domain = self._workspace_domain() + [('bookingpro_appointment_id', '!=', False)]
        if not self._is_bookingpro_manager():
            domain += ['|', ('user_id', '=', request.env.user.id), ('user_id', '=', False)]
        values = self._workspace_base_values(
            page_section='leads',
            leads=request.env['crm.lead'].sudo().search(domain, order='create_date desc'),
        )
        return request.render('bookingpro.portal_workspace_leads', values)


    # -------------------------------------------------------------------------
    # Portal SMTP / outgoing email configuration
    # -------------------------------------------------------------------------
    def _company_param_name(self, key, company=None):
        company = company or self._workspace_company()
        return 'bookingpro.%s.company_%s' % (key, company.id)

    def _get_selected_mail_server(self, company=None):
        company = company or self._workspace_company()
        ICP = request.env['ir.config_parameter'].sudo()
        server_id = self._to_int(ICP.get_param(self._company_param_name('mail_server_id', company), default=ICP.get_param('bookingpro.mail_server_id', default='')))
        if not server_id:
            return request.env['ir.mail_server'].sudo()
        return request.env['ir.mail_server'].sudo().browse(server_id).exists()

    def _smtp_encryption_selection(self):
        MailServer = request.env['ir.mail_server'].sudo()
        field = MailServer._fields.get('smtp_encryption')
        if field and getattr(field, 'selection', None):
            return field.selection
        return [('none', 'None'), ('starttls', 'TLS (STARTTLS)'), ('ssl', 'SSL/TLS')]

    def _smtp_auth_selection(self):
        MailServer = request.env['ir.mail_server'].sudo()
        field = MailServer._fields.get('smtp_authentication')
        if field and getattr(field, 'selection', None):
            return field.selection
        return [('login', 'Username')]

    def _smtp_server_values_from_post(self, post, existing=False):
        MailServer = request.env['ir.mail_server'].sudo()
        available_fields = MailServer._fields
        vals = {}
        candidate_values = {
            'name': post.get('smtp_name') or 'BookingPro SMTP',
            'smtp_host': post.get('smtp_host') or False,
            'smtp_port': self._to_int(post.get('smtp_port')) or 587,
            'smtp_user': post.get('smtp_user') or False,
            'smtp_encryption': post.get('smtp_encryption') or 'starttls',
            'smtp_authentication': post.get('smtp_authentication') or 'login',
            'from_filter': post.get('smtp_from_filter') or False,
            'sequence': self._to_int(post.get('smtp_sequence')) or 10,
            'active': self._checkbox(post, 'smtp_active', default=True),
        }
        for field_name, field_value in candidate_values.items():
            if field_name in available_fields:
                vals[field_name] = field_value
        # Never overwrite an existing password with an empty value from the portal form.
        if 'smtp_pass' in available_fields and post.get('smtp_pass'):
            vals['smtp_pass'] = post.get('smtp_pass')
        return vals

    def _apply_smtp_to_bookingpro_templates(self, mail_server=False, from_email=False, from_name=False):
        templates = [
            'bookingpro.mail_template_appointment_received',
            'bookingpro.mail_template_appointment_confirmed',
            'bookingpro.mail_template_appointment_rescheduled',
            'bookingpro.mail_template_appointment_cancelled',
            'bookingpro.mail_template_appointment_reminder',
            'bookingpro.mail_template_customer_followup',
        ]
        email_from = False
        if from_email:
            email_from = '%s <%s>' % (from_name or 'BookingPro', from_email) if from_name else from_email
        for xmlid in templates:
            template = request.env.ref(xmlid, raise_if_not_found=False)
            if not template:
                continue
            vals = {}
            if mail_server and 'mail_server_id' in template._fields:
                vals['mail_server_id'] = mail_server.id
            if email_from and 'email_from' in template._fields:
                vals['email_from'] = email_from
            if vals:
                template.sudo().write(vals)
        return True

    @http.route('/bookingpro/workspace/smtp', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def workspace_smtp(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        company = self._workspace_company()
        ICP = request.env['ir.config_parameter'].sudo()
        MailServer = request.env['ir.mail_server'].sudo()
        status = post.get('status')
        message = post.get('message')
        if request.httprequest.method == 'POST':
            action = post.get('action') or 'save'
            try:
                if action in ('save', 'select'):
                    if action == 'save':
                        vals = self._smtp_server_values_from_post(post)
                        if not vals.get('smtp_host'):
                            raise UserError(_('SMTP Host is required.'))
                        server = MailServer.browse(self._to_int(post.get('mail_server_id'))).exists()
                        if server:
                            server.write(vals)
                        else:
                            server = MailServer.create(vals)
                    else:
                        server = MailServer.browse(self._to_int(post.get('mail_server_id'))).exists()
                        if not server:
                            raise UserError(_('Please select a valid outgoing mail server.'))
                    from_email = (post.get('smtp_from_email') or company.email or '').strip()
                    from_name = (post.get('smtp_from_name') or company.name or 'BookingPro').strip()
                    ICP.set_param(self._company_param_name('mail_server_id', company), str(server.id))
                    ICP.set_param(self._company_param_name('smtp_from_email', company), from_email)
                    ICP.set_param(self._company_param_name('smtp_from_name', company), from_name)
                    # Compatibility global fallback for older code paths.
                    ICP.set_param('bookingpro.mail_server_id', str(server.id))
                    ICP.set_param('bookingpro.smtp_from_email', from_email)
                    ICP.set_param('bookingpro.smtp_from_name', from_name)
                    self._apply_smtp_to_bookingpro_templates(server, from_email, from_name)
                    return request.redirect('/bookingpro/workspace/smtp?status=saved')
                if action == 'test':
                    server = MailServer.browse(self._to_int(post.get('mail_server_id'))).exists() or self._get_selected_mail_server(company)
                    test_email = (post.get('test_email') or request.env.user.email or company.email or '').strip()
                    if not server:
                        raise UserError(_('Please save/select an SMTP server before testing.'))
                    if not test_email:
                        raise UserError(_('Please enter a test recipient email.'))
                    from_email = (post.get('smtp_from_email') or ICP.get_param(self._company_param_name('smtp_from_email', company), default=company.email or '')).strip()
                    from_name = (post.get('smtp_from_name') or ICP.get_param(self._company_param_name('smtp_from_name', company), default=company.name or 'BookingPro')).strip()
                    email_from = '%s <%s>' % (from_name, from_email) if from_email else (company.email or request.env.user.email or False)
                    mail_vals = {
                        'subject': 'BookingPro SMTP test',
                        'body_html': '<p>This is a BookingPro SMTP test email sent from the portal workspace.</p>',
                        'email_to': test_email,
                    }
                    MailMail = request.env['mail.mail'].sudo()
                    if email_from and 'email_from' in MailMail._fields:
                        mail_vals['email_from'] = email_from
                    if 'mail_server_id' in MailMail._fields:
                        mail_vals['mail_server_id'] = server.id
                    mail = MailMail.create(mail_vals)
                    mail.send()
                    return request.redirect('/bookingpro/workspace/smtp?status=test_sent')
            except Exception as exc:
                # Keep the portal page usable even if SMTP credentials are wrong.
                status = 'error'
                message = str(exc)
        selected_server = self._get_selected_mail_server(company)
        servers = MailServer.search([], order='sequence, id')
        smtp_settings = {
            'selected_id': selected_server.id if selected_server else False,
            'from_email': ICP.get_param(self._company_param_name('smtp_from_email', company), default=ICP.get_param('bookingpro.smtp_from_email', default=company.email or '')),
            'from_name': ICP.get_param(self._company_param_name('smtp_from_name', company), default=ICP.get_param('bookingpro.smtp_from_name', default=company.name or 'BookingPro')),
            'status': status,
            'message': message,
        }
        values = self._workspace_base_values(
            page_section='smtp',
            smtp_servers=servers,
            smtp_selected_server=selected_server,
            smtp_settings=smtp_settings,
            smtp_encryption_selection=self._smtp_encryption_selection(),
            smtp_auth_selection=self._smtp_auth_selection(),
        )
        return request.render('bookingpro.portal_workspace_smtp', values)

    @http.route('/bookingpro/workspace/settings', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def workspace_settings(self, **post):
        denied = self._require_bookingpro_internal()
        if denied:
            return denied
        if not self._is_bookingpro_manager():
            return request.not_found()
        company = self._workspace_company()
        ICP = request.env['ir.config_parameter'].sudo()
        if request.httprequest.method == 'POST':
            company.bookingpro_slug = post.get('bookingpro_slug') or company.bookingpro_slug
            ICP.set_param('bookingpro.slot_step_minutes', str(self._to_int(post.get('slot_step_minutes')) or 30))
            ICP.set_param('bookingpro.followup_delay_days', str(self._to_int(post.get('followup_delay_days')) or 1))
            interval_hours = self._to_int(post.get('customer_followup_interval_hours')) or 1
            if interval_hours not in (1, 5):
                interval_hours = 1 if interval_hours <= 1 else 5
            ICP.set_param('bookingpro.customer_followup_interval_hours', str(interval_hours))
            ICP.set_param('bookingpro.customer_followup_max_emails', str(self._to_int(post.get('customer_followup_max_emails')) or 3))
            ICP.set_param('bookingpro.customer_followup_email_delay_hours', str(interval_hours))
            for key in ['auto_confirm', 'require_payment', 'create_crm_lead', 'auto_followup_on_completion', 'enable_customer_followup', 'auto_customer_followup_on_booking', 'send_customer_followup_email_on_booking', 'send_customer_followup_after_completion', 'create_internal_activity_for_customer_followup', 'enable_email_reminders', 'send_5h_reminder', 'send_1h_reminder', 'readai_enabled']:
                form_name = 'bookingpro_%s' % key
                param_name = 'bookingpro.%s' % key
                ICP.set_param(param_name, 'True' if self._checkbox(post, form_name, default=False) else 'False')
            ICP.set_param('bookingpro.readai_api_url', post.get('readai_api_url') or '')
            ICP.set_param('bookingpro.readai_api_key', post.get('readai_api_key') or '')
            return request.redirect('/bookingpro/workspace/settings?saved=1')
        return request.render('bookingpro.portal_workspace_settings', self._workspace_base_values(page_section='settings', saved=post.get('saved')))
