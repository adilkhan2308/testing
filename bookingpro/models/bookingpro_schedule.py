# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BookingProStaffSchedule(models.Model):
    _name = 'bookingpro.staff.schedule'
    _description = 'BookingPro Staff Availability Schedule'
    _order = 'staff_user_id, weekday, hour_from'
    _check_company_auto = True

    name = fields.Char(compute='_compute_name', store=True)
    staff_user_id = fields.Many2one('res.users', required=True, domain="[('share','=',False)]")
    employee_id = fields.Many2one('hr.employee', string='Employee')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], required=True, default='0')
    hour_from = fields.Float(required=True, default=9.0)
    hour_to = fields.Float(required=True, default=17.0)
    break_hour_from = fields.Float(string='Break From')
    break_hour_to = fields.Float(string='Break To')
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.depends('staff_user_id', 'weekday', 'hour_from', 'hour_to')
    def _compute_name(self):
        weekday_labels = dict(self._fields['weekday'].selection)
        for rec in self:
            rec.name = '%s - %s %.2f-%.2f' % (
                rec.staff_user_id.name or 'Staff',
                weekday_labels.get(rec.weekday, ''),
                rec.hour_from,
                rec.hour_to,
            )

    @api.constrains('hour_from', 'hour_to', 'break_hour_from', 'break_hour_to')
    def _check_hours(self):
        for rec in self:
            if rec.hour_from < 0 or rec.hour_to > 24 or rec.hour_from >= rec.hour_to:
                raise ValidationError(_('Working hours must be between 0 and 24, and start must be before end.'))
            if rec.break_hour_from or rec.break_hour_to:
                if not (rec.hour_from <= rec.break_hour_from < rec.break_hour_to <= rec.hour_to):
                    raise ValidationError(_('Break time must be inside the working time range.'))
