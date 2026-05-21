# -*- coding: utf-8 -*-
{
    'name': 'BookingPro - Appointment Booking & CRM',
    'summary': 'Online appointment booking, CRM-style scheduling, portal, calendar, availability, and reports.',
    'description': '''
BookingPro provides a complete Odoo-based appointment booking system with:
- Public online booking page
- Service and category management
- Staff and resource availability
- Appointment lifecycle and rescheduling
- CRM/customer appointment timeline
- Customer portal
- Calendar integration
- Email notifications
- CRM lead capture
- Follow-up activities
- Multi-tenant/client booking links
- 1 hour and 5 hour appointment reminders
- Read.ai integration hook
- Reporting views
''',
    'version': '19.0.3.0.4',
    'category': 'Services/Appointment Scheduling',
    'author': 'OOTechnologies',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'website',
        'portal',
        'mail',
        'calendar',
        'contacts',
        'crm',
        'sale',
        'account',
        'hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/mail_templates.xml',
        'data/ir_cron.xml',
        'data/bookingpro_demo_data.xml',
        'views/bookingpro_service_views.xml',
        'views/bookingpro_category_views.xml',
        'views/bookingpro_resource_views.xml',
        'views/bookingpro_schedule_views.xml',
        'views/bookingpro_company_views.xml',
        'views/bookingpro_crm_views.xml',
        'views/bookingpro_reschedule_wizard_views.xml',
        'views/bookingpro_appointment_views.xml',
        'views/bookingpro_partner_views.xml',
        'views/bookingpro_config_views.xml',
        'views/bookingpro_dashboard_views.xml',
        'views/bookingpro_auth_templates.xml',
        'views/bookingpro_portal_templates.xml',
        'views/bookingpro_workspace_portal_templates.xml',
        'views/bookingpro_website_templates.xml',
        'report/bookingpro_report_views.xml',
        'views/bookingpro_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bookingpro/static/src/css/bookingpro.css',
            'bookingpro/static/src/css/bookingpro_premium_portal.css',
            'bookingpro/static/src/js/bookingpro_workspace.js',
            'bookingpro/static/src/js/bookingpro_react_portal.js',
        ],
        # Backend assets intentionally kept clean.
        # Premium portal/public styles are frontend-only to avoid backend SCSS compilation issues.
        'web.assets_backend': [],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
