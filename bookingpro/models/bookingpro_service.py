# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BookingProService(models.Model):
    _name = 'bookingpro.service'
    _description = 'BookingPro Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(copy=False)
    category_id = fields.Many2one('bookingpro.category', required=True, tracking=True, check_company=True)
    description = fields.Html()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    duration = fields.Float(string='Duration (Hours)', default=1.0, required=True, tracking=True)
    price = fields.Monetary(default=0.0, tracking=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes')

    buffer_before = fields.Float(string='Buffer Before (Hours)', default=0.0)
    buffer_after = fields.Float(string='Buffer After (Hours)', default=0.0)
    capacity = fields.Integer(default=1, required=True)

    staff_user_ids = fields.Many2many(
        'res.users',
        'bookingpro_service_res_users_rel',
        'service_id',
        'user_id',
        string='Assigned Staff',
        domain="[('share','=',False)]",
    )
    resource_ids = fields.Many2many(
        'bookingpro.resource',
        'bookingpro_service_resource_rel',
        'service_id',
        'resource_id',
        string='Allowed Resources',
    )

    appointment_ids = fields.One2many('bookingpro.appointment', 'service_id')
    appointment_count = fields.Integer(compute='_compute_appointment_count')

    _positive_duration = models.Constraint(
        'CHECK(duration > 0)',
        'Service duration must be greater than zero.',
    )
    _positive_capacity = models.Constraint(
        'CHECK(capacity > 0)',
        'Service capacity must be greater than zero.',
    )

    @api.depends('appointment_ids')
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    @api.constrains('buffer_before', 'buffer_after')
    def _check_buffers(self):
        for rec in self:
            if rec.buffer_before < 0 or rec.buffer_after < 0:
                raise ValidationError(_('Buffer time cannot be negative.'))

    def _float_to_time(self, value):
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if hours >= 24:
            return time(hour=23, minute=59, second=59)
        if minutes >= 60:
            hours += 1
            minutes = 0
        return time(hour=hours, minute=minutes)

    def _slot_range(self, selected_date, schedule_line):
        start_dt = datetime.combine(selected_date, self._float_to_time(schedule_line.hour_from))
        end_dt = datetime.combine(selected_date, self._float_to_time(schedule_line.hour_to))
        break_from = break_to = None
        if schedule_line.break_hour_from and schedule_line.break_hour_to:
            break_from = datetime.combine(selected_date, self._float_to_time(schedule_line.break_hour_from))
            break_to = datetime.combine(selected_date, self._float_to_time(schedule_line.break_hour_to))
        return start_dt, end_dt, break_from, break_to

    def get_available_slots(self, selected_date, staff_user=None, resource=None):
        """Return available slot dictionaries for website/API usage.

        selected_date: date object
        staff_user: optional res.users record
        resource: optional bookingpro.resource record
        """
        self.ensure_one()
        Appointment = self.env['bookingpro.appointment'].sudo()
        Schedule = self.env['bookingpro.staff.schedule'].sudo()
        weekday = str(selected_date.weekday())
        if staff_user:
            staff_candidates = staff_user
            if self.staff_user_ids and staff_user not in self.staff_user_ids:
                return []
        else:
            staff_candidates = self.staff_user_ids
        if not staff_candidates:
            staff_candidates = self.env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)], limit=20)

        if resource and self.resource_ids and resource not in self.resource_ids:
            return []

        slots = []
        step_minutes = int(self.env['ir.config_parameter'].sudo().get_param('bookingpro.slot_step_minutes', default=30) or 30)
        step = timedelta(minutes=max(step_minutes, 5))
        duration = timedelta(hours=self.duration)
        buffer_before = timedelta(hours=self.buffer_before)
        buffer_after = timedelta(hours=self.buffer_after)

        for staff in staff_candidates:
            schedule_lines = Schedule.search([
                ('staff_user_id', '=', staff.id),
                ('weekday', '=', weekday),
                ('active', '=', True),
                ('company_id', '=', self.company_id.id),
            ])
            for line in schedule_lines:
                start_window, end_window, break_from, break_to = self._slot_range(selected_date, line)
                cursor = start_window
                while cursor + duration <= end_window:
                    slot_start = cursor
                    slot_end = cursor + duration
                    if break_from and break_to and slot_start < break_to and slot_end > break_from:
                        cursor += step
                        continue
                    conflict_start = slot_start - buffer_before
                    conflict_end = slot_end + buffer_after
                    if not Appointment.has_conflict(
                        start_dt=conflict_start,
                        end_dt=conflict_end,
                        staff_user_id=staff.id,
                        resource_id=resource.id if resource else False,
                        service=self,
                    ):
                        slots.append({
                            'staff_id': staff.id,
                            'staff_name': staff.name,
                            'resource_id': resource.id if resource else False,
                            'resource_name': resource.name if resource else '',
                            'start': fields.Datetime.to_string(slot_start),
                            'end': fields.Datetime.to_string(slot_end),
                            'label': '%s - %s' % (slot_start.strftime('%H:%M'), slot_end.strftime('%H:%M')),
                        })
                    cursor += step
        return slots
