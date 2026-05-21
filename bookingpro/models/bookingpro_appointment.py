# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BookingProAppointment(models.Model):
    _name = 'bookingpro.appointment'
    _description = 'BookingPro Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'start_datetime desc, id desc'
    _check_company_auto = True

    name = fields.Char(default='New', copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean(default=True)

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    customer_email = fields.Char(related='partner_id.email', readonly=False)
    customer_phone = fields.Char(related='partner_id.phone', readonly=False)

    category_id = fields.Many2one(related='service_id.category_id', store=True, readonly=True)
    service_id = fields.Many2one('bookingpro.service', required=True, tracking=True, check_company=True)
    staff_user_id = fields.Many2one('res.users', string='Assigned Staff', domain="[('share','=',False)]", tracking=True)
    resource_id = fields.Many2one('bookingpro.resource', check_company=True, tracking=True)

    start_datetime = fields.Datetime(required=True, tracking=True)
    end_datetime = fields.Datetime(required=True, tracking=True)
    duration = fields.Float(related='service_id.duration', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Confirmation'),
        ('payment_pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('confirmed', 'Confirmed'),
        ('reschedule_requested', 'Reschedule Requested'),
        ('rescheduled', 'Rescheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No-show'),
        ('cancelled', 'Cancelled'),
        ('invoiced', 'Invoiced'),
    ], default='pending', required=True, tracking=True)

    payment_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refund_pending', 'Refund Pending'),
        ('refunded', 'Refunded'),
    ], default='not_required', tracking=True)

    price = fields.Monetary(related='service_id.price', readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    internal_note = fields.Html(string='Internal Notes')
    customer_note = fields.Text(string='Customer Notes')
    cancellation_reason = fields.Text()
    reschedule_reason = fields.Text()

    calendar_event_id = fields.Many2one('calendar.event', readonly=True, copy=False)
    crm_lead_id = fields.Many2one('crm.lead', string='CRM Lead', readonly=True, copy=False)
    sale_order_id = fields.Many2one('sale.order', readonly=True, copy=False)
    invoice_id = fields.Many2one('account.move', readonly=True, copy=False)

    followup_state = fields.Selection([
        ('none', 'No Follow-up'),
        ('scheduled', 'Scheduled'),
        ('done', 'Done'),
    ], default='none', tracking=True)
    followup_user_id = fields.Many2one('res.users', string='Follow-up Responsible', domain="[('share','=',False)]")
    followup_date = fields.Date(string='Next Follow-up Date')
    followup_note = fields.Text(string='Follow-up Notes')
    followup_activity_id = fields.Many2one('mail.activity', string='Follow-up Activity', readonly=True, copy=False)

    customer_followup_requested = fields.Boolean(string='Customer Follow-up Requested', default=True, tracking=True, copy=False)
    customer_followup_requested_at = fields.Datetime(string='Customer Follow-up Requested At', copy=False)
    customer_followup_message = fields.Text(string='Customer Follow-up Message')
    customer_followup_state = fields.Selection([
        ('none', 'No Follow-up'),
        ('requested', 'Requested'),
        ('scheduled', 'Scheduled'),
        ('email_queued', 'Email Queued'),
        ('stopped', 'Max Emails Sent'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='none', string='Customer Follow-up Status', tracking=True, copy=False)
    customer_followup_due_datetime = fields.Datetime(string='Customer Follow-up Due At', copy=False)
    customer_followup_email_sent = fields.Boolean(string='Customer Follow-up Email Queued', copy=False)
    customer_followup_email_sent_datetime = fields.Datetime(string='Customer Follow-up Email Queued At', copy=False)
    customer_followup_email_error = fields.Text(string='Customer Follow-up Email Error', copy=False)
    customer_followup_interval_hours = fields.Integer(
        string='Customer Follow-up Interval Hours',
        default=1,
        copy=False,
        help='Customer follow-up email repeat interval. Use 1 or 5 hours depending on the client flow.',
    )
    customer_followup_max_emails = fields.Integer(
        string='Customer Follow-up Max Emails',
        default=3,
        copy=False,
        help='Maximum number of automatic customer follow-up emails for this appointment.',
    )
    customer_followup_email_count = fields.Integer(string='Customer Follow-up Emails Sent', default=0, copy=False)
    customer_followup_last_email_datetime = fields.Datetime(string='Last Customer Follow-up Email At', copy=False)
    customer_followup_next_email_datetime = fields.Datetime(string='Next Customer Follow-up Email At', copy=False)

    reminder_5h_sent = fields.Boolean(string='5 Hour Reminder Sent', copy=False)
    reminder_1h_sent = fields.Boolean(string='1 Hour Reminder Sent', copy=False)

    read_ai_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], default='not_sent', string='Read.ai Status', copy=False)
    read_ai_external_id = fields.Char(string='Read.ai External ID', copy=False)
    read_ai_meeting_url = fields.Char(string='Read.ai Meeting URL / Recording URL')
    read_ai_response = fields.Text(string='Read.ai Last Response', readonly=True, copy=False)

    reschedule_history_ids = fields.One2many('bookingpro.reschedule.history', 'appointment_id')
    notification_log_ids = fields.One2many('bookingpro.notification.log', 'appointment_id')
    feedback_ids = fields.One2many('bookingpro.feedback', 'appointment_id')
    feedback_count = fields.Integer(compute='_compute_feedback_count')

    color = fields.Integer(compute='_compute_color', store=False)

    _appointment_time_valid = models.Constraint(
        'CHECK(start_datetime < end_datetime)',
        'Appointment start time must be before end time.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence'].sudo()
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('bookingpro.appointment') or 'New'
        records = super().create(vals_list)
        for appointment in records:
            appointment._sync_calendar_event()
            appointment._create_crm_lead_if_needed()
            appointment._handle_customer_followup_on_booking()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'start_datetime', 'end_datetime', 'staff_user_id', 'resource_id', 'service_id'}.intersection(vals.keys()):
            self._sync_calendar_event()
        return result

    @api.depends('feedback_ids')
    def _compute_feedback_count(self):
        for rec in self:
            rec.feedback_count = len(rec.feedback_ids)

    def _compute_color(self):
        color_map = {
            'draft': 1,
            'pending': 3,
            'payment_pending': 4,
            'paid': 5,
            'confirmed': 10,
            'reschedule_requested': 2,
            'rescheduled': 2,
            'in_progress': 7,
            'completed': 6,
            'no_show': 9,
            'cancelled': 1,
            'invoiced': 8,
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    @api.constrains('service_id', 'staff_user_id', 'resource_id')
    def _check_service_assignments(self):
        for rec in self:
            if rec.service_id.staff_user_ids and rec.staff_user_id and rec.staff_user_id not in rec.service_id.staff_user_ids:
                raise ValidationError(_('Selected staff is not assigned to this service.'))
            if rec.service_id.resource_ids and rec.resource_id and rec.resource_id not in rec.service_id.resource_ids:
                raise ValidationError(_('Selected resource is not allowed for this service.'))

    @api.constrains('service_id', 'start_datetime', 'end_datetime', 'staff_user_id', 'resource_id', 'state')
    def _check_conflicts(self):
        for rec in self:
            if rec.state in rec._conflict_states() and rec.start_datetime and rec.end_datetime:
                buffer_before = rec.start_datetime - timedelta(hours=rec.service_id.buffer_before or 0.0)
                buffer_after = rec.end_datetime + timedelta(hours=rec.service_id.buffer_after or 0.0)
                if self.has_conflict(
                    buffer_before,
                    buffer_after,
                    staff_user_id=rec.staff_user_id.id or False,
                    resource_id=rec.resource_id.id or False,
                    service=rec.service_id,
                    exclude_appointment_id=rec.id,
                ):
                    raise ValidationError(_('This appointment conflicts with another confirmed booking for the same staff/resource.'))

    @api.model
    def _conflict_states(self):
        return ['pending', 'payment_pending', 'paid', 'confirmed', 'rescheduled', 'in_progress']

    @api.model
    def has_conflict(self, start_dt, end_dt, staff_user_id=False, resource_id=False, service=None, exclude_appointment_id=False):
        domain = [
            ('state', 'in', self._conflict_states()),
            ('start_datetime', '<', end_dt),
            ('end_datetime', '>', start_dt),
        ]
        if exclude_appointment_id:
            domain.append(('id', '!=', exclude_appointment_id))
        if service and service.company_id:
            domain.append(('company_id', '=', service.company_id.id))

        staff_domain = list(domain)
        resource_domain = list(domain)
        conflict = False
        if staff_user_id:
            staff_domain.append(('staff_user_id', '=', staff_user_id))
            conflict = bool(self.sudo().search_count(staff_domain))
        if resource_id:
            resource_domain.append(('resource_id', '=', resource_id))
            conflict = conflict or bool(self.sudo().search_count(resource_domain))
        return conflict

    def _sync_calendar_event(self):
        Calendar = self.env['calendar.event'].sudo()
        for rec in self:
            if not rec.start_datetime or not rec.end_datetime:
                continue
            values = {
                'name': '%s - %s' % (rec.service_id.name, rec.partner_id.name),
                'start': rec.start_datetime,
                'stop': rec.end_datetime,
                'description': rec.customer_note or '',
                'partner_ids': [(6, 0, [rec.partner_id.id] if rec.partner_id else [])],
                'user_id': rec.staff_user_id.id or self.env.user.id,
            }
            if rec.calendar_event_id:
                rec.calendar_event_id.write(values)
            else:
                rec.calendar_event_id = Calendar.create(values).id

    def _create_crm_lead_if_needed(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param('bookingpro.create_crm_lead', default='True') == 'True'
        if not enabled:
            return False
        Lead = self.env['crm.lead'].sudo()
        for rec in self:
            if rec.crm_lead_id:
                continue
            lead = Lead.create({
                'name': '%s - %s' % (rec.service_id.name, rec.partner_id.name),
                'type': 'lead',
                'partner_id': rec.partner_id.id,
                'contact_name': rec.partner_id.name,
                'email_from': rec.partner_id.email,
                'phone': rec.partner_id.phone,
                'user_id': rec.staff_user_id.id or False,
                'company_id': rec.company_id.id,
                'description': _('BookingPro appointment lead\nReference: %s\nService: %s\nAppointment: %s\nNotes: %s') % (
                    rec.name, rec.service_id.name, rec.start_datetime, rec.customer_note or ''),
                'bookingpro_appointment_id': rec.id,
            })
            rec.crm_lead_id = lead.id
        return True

    def action_create_crm_lead(self):
        self._create_crm_lead_if_needed()
        return True

    def action_view_crm_lead(self):
        self.ensure_one()
        if not self.crm_lead_id:
            raise UserError(_('No CRM lead linked yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('CRM Lead'),
            'res_model': 'crm.lead',
            'res_id': self.crm_lead_id.id,
            'view_mode': 'form',
        }

    def _get_followup_user(self):
        self.ensure_one()
        return self.followup_user_id or self.staff_user_id or self.env.user

    def _schedule_followup_activity(self, summary=None, days=None):
        Activity = self.env['mail.activity'].sudo()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return False
        model_id = self.env['ir.model']._get(self._name).id
        for rec in self:
            delay_days = days
            if delay_days is None:
                delay_days = int(self.env['ir.config_parameter'].sudo().get_param('bookingpro.followup_delay_days', default=1) or 1)
            deadline = fields.Date.context_today(rec) + timedelta(days=max(delay_days, 0))
            user = rec._get_followup_user()
            values = {
                'activity_type_id': activity_type.id,
                'summary': summary or _('BookingPro customer follow-up'),
                'note': rec.followup_note or _('Follow up with customer about appointment %s.') % rec.name,
                'date_deadline': deadline,
                'user_id': user.id,
                'res_model_id': model_id,
                'res_id': rec.id,
            }
            activity = Activity.create(values)
            rec.write({
                'followup_state': 'scheduled',
                'followup_activity_id': activity.id,
                'followup_date': deadline,
                'followup_user_id': user.id,
            })
        return True

    def action_schedule_followup(self):
        self._schedule_followup_activity()
        return True

    def action_mark_followup_done(self):
        self.write({'followup_state': 'done'})
        return True

    def _bookingpro_param_is_true(self, key, default='True'):
        return self.env['ir.config_parameter'].sudo().get_param(key, default=default) == 'True'

    def _bookingpro_param_int(self, key, default=0):
        value = self.env['ir.config_parameter'].sudo().get_param(key, default=str(default))
        try:
            return int(value or default)
        except Exception:
            return default

    def _customer_followup_interval_hours(self):
        interval = self._bookingpro_param_int('bookingpro.customer_followup_interval_hours', 1)
        if interval not in (1, 5):
            interval = 1 if interval <= 1 else 5
        return interval

    def _customer_followup_max_emails(self):
        return max(self._bookingpro_param_int('bookingpro.customer_followup_max_emails', 3), 1)

    def _customer_followup_next_due(self, base_dt=None):
        base_dt = base_dt or fields.Datetime.now()
        return base_dt + timedelta(hours=self._customer_followup_interval_hours())

    def _prepare_customer_followup_schedule_values(self, base_dt=None):
        interval = self._customer_followup_interval_hours()
        max_emails = self._customer_followup_max_emails()
        due_dt = (base_dt or fields.Datetime.now()) + timedelta(hours=interval)
        return {
            'customer_followup_interval_hours': interval,
            'customer_followup_max_emails': max_emails,
            'customer_followup_due_datetime': due_dt,
            'customer_followup_next_email_datetime': due_dt,
            'customer_followup_state': 'scheduled',
        }

    def _handle_customer_followup_on_booking(self):
        if not self._bookingpro_param_is_true('bookingpro.enable_customer_followup', 'True'):
            return False
        auto_all = self._bookingpro_param_is_true('bookingpro.auto_customer_followup_on_booking', 'True')
        auto_activity = self._bookingpro_param_is_true('bookingpro.create_internal_activity_for_customer_followup', 'True')
        now = fields.Datetime.now()
        for rec in self:
            requested = bool(rec.customer_followup_requested or auto_all)
            if not requested:
                continue
            values = rec._prepare_customer_followup_schedule_values(base_dt=now)
            values.update({
                'customer_followup_requested': True,
                'customer_followup_requested_at': rec.customer_followup_requested_at or now,
            })
            if not rec.customer_followup_message:
                values['customer_followup_message'] = _('Customer requested follow-up during booking.')
            rec.write(values)
            if auto_activity and rec.followup_state == 'none':
                rec._schedule_followup_activity(summary=_('BookingPro booking follow-up'), days=0)
        return True

    def action_request_customer_followup(self, message=None):
        if not self._bookingpro_param_is_true('bookingpro.enable_customer_followup', 'True'):
            raise UserError(_('Customer follow-up is disabled in BookingPro settings.'))
        now = fields.Datetime.now()
        for rec in self:
            note = message or rec.customer_followup_message or rec.followup_note or ''
            values = rec._prepare_customer_followup_schedule_values(base_dt=now)
            values.update({
                'customer_followup_requested': True,
                'customer_followup_requested_at': rec.customer_followup_requested_at or now,
                'customer_followup_message': note,
                'followup_note': note or rec.followup_note,
                'customer_followup_email_error': False,
            })
            rec.write(values)
            if rec.followup_state == 'none':
                rec._schedule_followup_activity(summary=_('BookingPro customer requested follow-up'), days=0)
        return True

    def action_send_customer_followup_email(self):
        template = self.env.ref('bookingpro.mail_template_customer_followup', raise_if_not_found=False)
        if not template:
            raise UserError(_('Customer follow-up email template is missing.'))
        now = fields.Datetime.now()
        for rec in self:
            if rec.customer_followup_state == 'done':
                continue
            if not rec.partner_id.email:
                rec.write({
                    'customer_followup_state': 'failed',
                    'customer_followup_email_error': _('Customer email is missing.'),
                })
                self.env['bookingpro.notification.log'].sudo().create({
                    'appointment_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'channel': 'email',
                    'notification_type': 'customer_followup_email',
                    'state': 'failed',
                    'recipient': False,
                    'error_message': _('Customer email is missing.'),
                    'company_id': rec.company_id.id,
                })
                continue
            try:
                rec._send_mail_template_with_bookingpro_smtp(template, rec)
                new_count = (rec.customer_followup_email_count or 0) + 1
                interval = rec.customer_followup_interval_hours or rec._customer_followup_interval_hours()
                max_emails = rec.customer_followup_max_emails or rec._customer_followup_max_emails()
                next_due = now + timedelta(hours=interval) if new_count < max_emails else False
                state = 'scheduled' if next_due else 'stopped'
                rec.write({
                    'customer_followup_requested': True,
                    'customer_followup_state': state,
                    'customer_followup_email_sent': True,
                    'customer_followup_email_count': new_count,
                    'customer_followup_email_sent_datetime': now,
                    'customer_followup_last_email_datetime': now,
                    'customer_followup_due_datetime': next_due,
                    'customer_followup_next_email_datetime': next_due,
                    'customer_followup_email_error': False,
                })
                self.env['bookingpro.notification.log'].sudo().create({
                    'appointment_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'channel': 'email',
                    'notification_type': 'customer_followup_email',
                    'state': 'queued',
                    'recipient': rec.partner_id.email,
                    'sent_date': now,
                    'company_id': rec.company_id.id,
                })
            except Exception as exc:
                interval = rec.customer_followup_interval_hours or rec._customer_followup_interval_hours()
                next_due = now + timedelta(hours=interval)
                rec.write({
                    'customer_followup_state': 'failed',
                    'customer_followup_due_datetime': next_due,
                    'customer_followup_next_email_datetime': next_due,
                    'customer_followup_email_error': str(exc),
                })
                self.env['bookingpro.notification.log'].sudo().create({
                    'appointment_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'channel': 'email',
                    'notification_type': 'customer_followup_email',
                    'state': 'failed',
                    'recipient': rec.partner_id.email,
                    'error_message': str(exc),
                    'company_id': rec.company_id.id,
                })
        return True

    def action_mark_customer_followup_done(self):
        self.write({
            'customer_followup_state': 'done',
            'followup_state': 'done',
            'customer_followup_due_datetime': False,
            'customer_followup_next_email_datetime': False,
        })
        return True

    def _auto_schedule_completion_followup(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param('bookingpro.auto_followup_on_completion', default='True') == 'True'
        send_customer_email = self.env['ir.config_parameter'].sudo().get_param('bookingpro.send_customer_followup_after_completion', default='True') == 'True'
        if not enabled and not send_customer_email:
            return False
        for rec in self:
            if enabled and rec.followup_state == 'none':
                rec._schedule_followup_activity(summary=_('BookingPro post-appointment follow-up'))
            if send_customer_email:
                now = fields.Datetime.now()
                values = rec._prepare_customer_followup_schedule_values(base_dt=now)
                values.update({
                    'customer_followup_requested': True,
                    'customer_followup_message': rec.customer_followup_message or _('Thank you for your appointment. Our team may follow up with you if anything else is needed.'),
                })
                rec.write(values)
        return True

    def action_confirm(self):
        for rec in self:
            rec._check_conflicts()
            rec.write({'state': 'confirmed'})
            rec._send_template('bookingpro.mail_template_appointment_confirmed')
        return True

    def action_mark_payment_pending(self):
        self.write({'state': 'payment_pending', 'payment_state': 'pending'})
        return True

    def action_mark_paid(self):
        self.write({'state': 'paid', 'payment_state': 'paid'})
        return True

    def action_start(self):
        self.filtered(lambda r: r.state in ['confirmed', 'rescheduled', 'paid']).write({'state': 'in_progress'})
        return True

    def action_complete(self):
        records = self.filtered(lambda r: r.state in ['in_progress', 'confirmed', 'rescheduled', 'paid'])
        records.write({'state': 'completed'})
        records._auto_schedule_completion_followup()
        return True

    def action_no_show(self):
        records = self.filtered(lambda r: r.state in ['confirmed', 'rescheduled'])
        records.write({'state': 'no_show'})
        records._auto_schedule_completion_followup()
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ['completed', 'invoiced']:
                raise UserError(_('Completed or invoiced appointments cannot be cancelled.'))
            rec.write({'state': 'cancelled'})
            rec._send_template('bookingpro.mail_template_appointment_cancelled')
        return True

    def action_request_reschedule(self):
        self.write({'state': 'reschedule_requested'})
        return True

    def action_create_invoice(self):
        AccountMove = self.env['account.move'].sudo()
        for rec in self:
            if rec.invoice_id:
                continue
            if not rec.partner_id:
                raise UserError(_('Customer is required before creating an invoice.'))
            invoice = AccountMove.create({
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'invoice_origin': rec.name,
                'invoice_line_ids': [(0, 0, {
                    'name': rec.service_id.name,
                    'quantity': 1,
                    'price_unit': rec.service_id.price,
                    'tax_ids': [(6, 0, rec.service_id.tax_ids.ids)],
                })],
            })
            rec.write({'invoice_id': invoice.id, 'state': 'invoiced'})
        return True

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice linked yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }

    def action_view_calendar_event(self):
        self.ensure_one()
        if not self.calendar_event_id:
            raise UserError(_('No calendar event linked yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Calendar Event'),
            'res_model': 'calendar.event',
            'res_id': self.calendar_event_id.id,
            'view_mode': 'form',
        }

    def _bookingpro_company_param(self, key, company=None, default=''):
        company = company or self.env.company
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('%s.company_%s' % (key, company.id), default=ICP.get_param(key, default=default))

    def _bookingpro_selected_mail_server(self, company=None):
        company = company or self.env.company
        server_id = self._bookingpro_company_param('bookingpro.mail_server_id', company, default='')
        try:
            server_id = int(server_id or 0)
        except Exception:
            server_id = 0
        return self.env['ir.mail_server'].sudo().browse(server_id).exists() if server_id else self.env['ir.mail_server'].sudo()

    def _bookingpro_email_values(self, rec):
        values = {}
        MailMail = self.env['mail.mail']
        mail_server = rec._bookingpro_selected_mail_server(rec.company_id)
        if mail_server and 'mail_server_id' in MailMail._fields:
            values['mail_server_id'] = mail_server.id
        from_email = rec._bookingpro_company_param('bookingpro.smtp_from_email', rec.company_id, default=rec.company_id.email or '')
        from_name = rec._bookingpro_company_param('bookingpro.smtp_from_name', rec.company_id, default=rec.company_id.name or 'BookingPro')
        if from_email and 'email_from' in MailMail._fields:
            values['email_from'] = '%s <%s>' % (from_name or rec.company_id.name or 'BookingPro', from_email)
        return values

    def _send_mail_template_with_bookingpro_smtp(self, template, rec):
        email_values = rec._bookingpro_email_values(rec)
        try:
            return template.sudo().send_mail(rec.id, force_send=False, email_values=email_values or None)
        except TypeError:
            # Older/Odoo-custom send_mail signatures may not accept email_values.
            # In that case, Odoo will use the selected/default outgoing mail server.
            return template.sudo().send_mail(rec.id, force_send=False)

    def _send_template(self, xml_id):
        template = self.env.ref(xml_id, raise_if_not_found=False)
        if not template:
            return False
        for rec in self:
            rec._send_mail_template_with_bookingpro_smtp(template, rec)
            self.env['bookingpro.notification.log'].sudo().create({
                'appointment_id': rec.id,
                'partner_id': rec.partner_id.id,
                'channel': 'email',
                'notification_type': xml_id.split('.')[-1],
                'state': 'queued',
                'recipient': rec.partner_id.email,
                'company_id': rec.company_id.id,
            })
        return True

    @api.model
    def cron_send_reminders(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('bookingpro.enable_email_reminders', default='True') != 'True':
            return True
        now = fields.Datetime.now()
        reminder_states = ['confirmed', 'paid', 'rescheduled']
        if ICP.get_param('bookingpro.send_5h_reminder', default='True') == 'True':
            window_5 = now + timedelta(hours=5)
            after_1h = now + timedelta(hours=1, minutes=15)
            appointments_5h = self.sudo().search([
                ('state', 'in', reminder_states),
                ('start_datetime', '>', after_1h),
                ('start_datetime', '<=', window_5),
                ('reminder_5h_sent', '=', False),
            ], limit=100)
            for appointment in appointments_5h:
                appointment._send_template('bookingpro.mail_template_appointment_reminder')
                appointment.write({'reminder_5h_sent': True})
        if ICP.get_param('bookingpro.send_1h_reminder', default='True') == 'True':
            window_1 = now + timedelta(hours=1)
            appointments_1h = self.sudo().search([
                ('state', 'in', reminder_states),
                ('start_datetime', '>', now),
                ('start_datetime', '<=', window_1),
                ('reminder_1h_sent', '=', False),
            ], limit=100)
            for appointment in appointments_1h:
                appointment._send_template('bookingpro.mail_template_appointment_reminder')
                appointment.write({'reminder_1h_sent': True})
        return True

    @api.model
    def cron_send_customer_followups(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('bookingpro.enable_customer_followup', default='True') != 'True':
            return True
        if ICP.get_param('bookingpro.send_customer_followup_email_on_booking', default='True') != 'True':
            return True
        now = fields.Datetime.now()
        max_emails = max(self._bookingpro_param_int('bookingpro.customer_followup_max_emails', 3), 1)
        appointments = self.sudo().search([
            ('customer_followup_requested', '=', True),
            ('customer_followup_state', 'in', ['requested', 'scheduled', 'failed', 'email_queued']),
            ('customer_followup_email_count', '<', max_emails),
            '|', ('customer_followup_next_email_datetime', '=', False), ('customer_followup_next_email_datetime', '<=', now),
        ], limit=100)
        appointments.action_send_customer_followup_email()
        return True

    def action_send_to_readai(self):
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('bookingpro.readai_enabled', default='False') == 'True'
        api_url = ICP.get_param('bookingpro.readai_api_url', default='')
        api_key = ICP.get_param('bookingpro.readai_api_key', default='')
        if not enabled or not api_url:
            raise UserError(_('Read.ai integration is not configured. Enable it in BookingPro Settings and add an API/Webhook URL.'))
        try:
            import requests
        except Exception as exc:
            raise UserError(_('Python requests library is not available: %s') % exc)
        for rec in self:
            payload = {
                'reference': rec.name,
                'customer': rec.partner_id.name,
                'customer_email': rec.partner_id.email,
                'service': rec.service_id.name,
                'staff': rec.staff_user_id.name,
                'start_datetime': fields.Datetime.to_string(rec.start_datetime),
                'end_datetime': fields.Datetime.to_string(rec.end_datetime),
                'meeting_url': rec.read_ai_meeting_url or '',
                'notes': rec.customer_note or '',
                'company': rec.company_id.name,
            }
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['Authorization'] = 'Bearer %s' % api_key
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=20)
                rec.write({
                    'read_ai_status': 'sent' if response.status_code < 400 else 'failed',
                    'read_ai_response': response.text[:2000],
                })
                self.env['bookingpro.notification.log'].sudo().create({
                    'appointment_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'channel': 'read_ai',
                    'notification_type': 'read_ai_sync',
                    'state': 'sent' if response.status_code < 400 else 'failed',
                    'recipient': api_url,
                    'error_message': False if response.status_code < 400 else response.text[:1000],
                    'company_id': rec.company_id.id,
                })
            except Exception as exc:
                rec.write({'read_ai_status': 'failed', 'read_ai_response': str(exc)})
                self.env['bookingpro.notification.log'].sudo().create({
                    'appointment_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'channel': 'read_ai',
                    'notification_type': 'read_ai_sync',
                    'state': 'failed',
                    'recipient': api_url,
                    'error_message': str(exc),
                    'company_id': rec.company_id.id,
                })
        return True
