# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bookingpro_slot_step_minutes = fields.Integer(
        string='Slot Step Minutes',
        default=30,
        config_parameter='bookingpro.slot_step_minutes',
        help='Controls how frequently time slots are generated on the public booking page.',
    )
    bookingpro_auto_confirm = fields.Boolean(
        string='Auto Confirm Public Bookings',
        default=False,
        config_parameter='bookingpro.auto_confirm',
        help='If enabled, public bookings are automatically confirmed when no payment is required.',
    )
    bookingpro_require_payment = fields.Boolean(
        string='Require Payment Before Confirmation',
        default=False,
        config_parameter='bookingpro.require_payment',
    )
    bookingpro_allow_portal_cancel = fields.Boolean(
        string='Allow Portal Cancellation Requests',
        default=True,
        config_parameter='bookingpro.allow_portal_cancel',
    )
    bookingpro_allow_portal_reschedule = fields.Boolean(
        string='Allow Portal Reschedule Requests',
        default=True,
        config_parameter='bookingpro.allow_portal_reschedule',
    )

    bookingpro_company_slug = fields.Char(
        string='Client Booking Slug',
        related='company_id.bookingpro_slug',
        readonly=False,
    )
    bookingpro_company_public_booking_url = fields.Char(
        string='Client Booking Link',
        related='company_id.bookingpro_public_booking_url',
        readonly=True,
    )

    bookingpro_create_crm_lead = fields.Boolean(
        string='Create CRM Lead from Booking',
        default=True,
        config_parameter='bookingpro.create_crm_lead',
    )
    bookingpro_auto_followup_on_completion = fields.Boolean(
        string='Auto Follow-up After Completion/No-show',
        default=True,
        config_parameter='bookingpro.auto_followup_on_completion',
    )
    bookingpro_followup_delay_days = fields.Integer(
        string='Follow-up Delay Days',
        default=1,
        config_parameter='bookingpro.followup_delay_days',
    )

    bookingpro_enable_customer_followup = fields.Boolean(
        string='Enable Customer Follow-up',
        default=True,
        config_parameter='bookingpro.enable_customer_followup',
    )
    bookingpro_auto_customer_followup_on_booking = fields.Boolean(
        string='Auto Customer Follow-up on Booking',
        default=True,
        config_parameter='bookingpro.auto_customer_followup_on_booking',
    )
    bookingpro_send_customer_followup_email_on_booking = fields.Boolean(
        string='Send Customer Follow-up Email on Booking',
        default=True,
        config_parameter='bookingpro.send_customer_followup_email_on_booking',
    )
    bookingpro_send_customer_followup_after_completion = fields.Boolean(
        string='Send Customer Follow-up Email After Completion',
        default=True,
        config_parameter='bookingpro.send_customer_followup_after_completion',
    )
    bookingpro_create_internal_activity_for_customer_followup = fields.Boolean(
        string='Create Internal Activity for Customer Follow-up',
        default=True,
        config_parameter='bookingpro.create_internal_activity_for_customer_followup',
    )
    bookingpro_customer_followup_email_delay_hours = fields.Integer(
        string='Customer Follow-up Email Delay Hours',
        default=0,
        config_parameter='bookingpro.customer_followup_email_delay_hours',
        help='Legacy value kept for compatibility. Recurring follow-up now uses the interval below.',
    )
    bookingpro_customer_followup_interval_hours = fields.Integer(
        string='Customer Follow-up Interval Hours',
        default=1,
        config_parameter='bookingpro.customer_followup_interval_hours',
        help='Automatic customer follow-up email interval. Use 1 or 5 hours.',
    )
    bookingpro_customer_followup_max_emails = fields.Integer(
        string='Customer Follow-up Max Emails',
        default=3,
        config_parameter='bookingpro.customer_followup_max_emails',
        help='Stops automatic follow-up emails after this number of emails, unless manually restarted.',
    )

    bookingpro_enable_email_reminders = fields.Boolean(
        string='Enable Email Reminders',
        default=True,
        config_parameter='bookingpro.enable_email_reminders',
    )
    bookingpro_send_5h_reminder = fields.Boolean(
        string='Send 5 Hour Reminder',
        default=True,
        config_parameter='bookingpro.send_5h_reminder',
    )
    bookingpro_send_1h_reminder = fields.Boolean(
        string='Send 1 Hour Reminder',
        default=True,
        config_parameter='bookingpro.send_1h_reminder',
    )

    bookingpro_readai_enabled = fields.Boolean(
        string='Enable Read.ai Integration Hook',
        default=False,
        config_parameter='bookingpro.readai_enabled',
    )
    bookingpro_readai_api_url = fields.Char(
        string='Read.ai API/Webhook URL',
        config_parameter='bookingpro.readai_api_url',
    )
    bookingpro_readai_api_key = fields.Char(
        string='Read.ai API Key',
        config_parameter='bookingpro.readai_api_key',
    )
