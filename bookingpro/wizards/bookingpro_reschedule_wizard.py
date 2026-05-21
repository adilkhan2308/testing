# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BookingProRescheduleWizard(models.TransientModel):
    _name = 'bookingpro.reschedule.wizard'
    _description = 'BookingPro Reschedule Appointment Wizard'

    appointment_id = fields.Many2one('bookingpro.appointment', required=True)
    new_start_datetime = fields.Datetime(required=True)
    new_end_datetime = fields.Datetime(required=True)
    reason = fields.Text()

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'bookingpro.appointment' and active_id:
            appointment = self.env['bookingpro.appointment'].browse(active_id).exists()
            if appointment:
                vals.setdefault('appointment_id', appointment.id)
                vals.setdefault('new_start_datetime', appointment.start_datetime)
                vals.setdefault('new_end_datetime', appointment.end_datetime)
        return vals

    def action_apply_reschedule(self):
        self.ensure_one()
        appointment = self.appointment_id
        if self.new_start_datetime >= self.new_end_datetime:
            raise UserError(_('New start time must be before new end time.'))
        if self.env['bookingpro.appointment'].has_conflict(
            self.new_start_datetime,
            self.new_end_datetime,
            staff_user_id=appointment.staff_user_id.id,
            resource_id=appointment.resource_id.id,
            service=appointment.service_id,
            exclude_appointment_id=appointment.id,
        ):
            raise UserError(_('The selected new time conflicts with another booking.'))
        self.env['bookingpro.reschedule.history'].create({
            'appointment_id': appointment.id,
            'old_start_datetime': appointment.start_datetime,
            'old_end_datetime': appointment.end_datetime,
            'new_start_datetime': self.new_start_datetime,
            'new_end_datetime': self.new_end_datetime,
            'reason': self.reason,
            'requested_by_id': self.env.user.id,
            'approval_state': 'approved',
        })
        appointment.write({
            'start_datetime': self.new_start_datetime,
            'end_datetime': self.new_end_datetime,
            'reschedule_reason': self.reason,
            'state': 'rescheduled',
        })
        appointment._send_template('bookingpro.mail_template_appointment_rescheduled')
        return {'type': 'ir.actions.act_window_close'}
