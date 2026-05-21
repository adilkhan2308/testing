# BookingPro - Appointment Booking & CRM Module for Odoo

BookingPro is a complete Odoo module package for appointment booking, CRM-style appointment management, staff/resource availability, public website booking, customer portal, calendar scheduling, email notifications, and reporting.

## Main Features

- Public appointment booking page
- Service categories and service management
- Duration, price, capacity, buffer before/after
- Staff assignment per service
- Bookable resources such as rooms/equipment
- Weekly staff availability schedule
- Slot generation with conflict prevention
- Appointment lifecycle:
  - Draft
  - Pending Confirmation
  - Payment Pending
  - Paid
  - Confirmed
  - Reschedule Requested
  - Rescheduled
  - In Progress
  - Completed
  - No-show
  - Cancelled
  - Invoiced
- Odoo calendar event sync
- Customer profile appointment timeline
- Customer portal appointment list/detail
- Portal cancellation and reschedule request
- Email templates for received/confirmed/rescheduled/cancelled appointments
- Reschedule history log
- Notification log
- Feedback model
- Pivot/graph reporting
- Company-based record rules
- Staff own appointment visibility rule
- Portal own appointment visibility rule

## Dependencies

This module depends on standard Odoo apps:

- Website
- Portal
- Mail
- Calendar
- Contacts
- CRM
- Sales
- Invoicing / Account
- Employees / HR

## Installation

1. Copy the `bookingpro` folder into your Odoo custom addons directory.
2. Restart Odoo.
3. Activate developer mode.
4. Update Apps List.
5. Search for `BookingPro`.
6. Install the module.
7. Assign users to one of these groups:
   - BookingPro Staff
   - BookingPro Booking Manager
   - BookingPro Administrator

## Recommended Setup Flow

1. Open **BookingPro > Configuration > Service Categories**.
2. Create service categories, such as Consultation, Treatment, Repair, Training, or Salon Services.
3. Open **BookingPro > Configuration > Services**.
4. Create services with duration, price, staff, capacity, and buffer time.
5. Open **BookingPro > Configuration > Resources**.
6. Create resources if required, such as rooms, equipment, machines, tables, or courts.
7. Open **BookingPro > Configuration > Staff Availability**.
8. Configure weekly working hours and breaks for each staff user.
9. Open `/bookingpro` on the website and test public booking.
10. Review appointments in **BookingPro > Operations > Appointments** and **Calendar**.

## Developer Notes

- Public website routes are in `controllers/website_booking.py`.
- Portal routes are in `controllers/portal_booking.py`.
- Appointment lifecycle logic is in `models/bookingpro_appointment.py`.
- Slot generation logic is in `models/bookingpro_service.py`.
- Rescheduling wizard is in `wizards/bookingpro_reschedule_wizard.py`.
- Security groups and record rules are in `security/security.xml`.
- Access rights are in `security/ir.model.access.csv`.

## Suggested Next Improvements

- Add payment provider checkout flow before confirmation.
- Add WhatsApp/SMS reminders.
- Add Google/Outlook calendar sync.
- Add multi-branch support.
- Add SaaS subscription plan limits.
- Add drag-and-drop rescheduling enhancement.
- Add automated reminder cron jobs.
- Add industry-specific templates for clinics, salons, consultants, and repair services.

## Compatibility Note

The module is written with modern Odoo 18/19-style structure and should be validated on the exact Odoo version used by your deployment. Some UI syntax may need minor adaptation if your instance uses a customized Odoo build.


## Odoo 19 Compatibility Notes

This package uses the Odoo 19 security model:

- `res.groups.privilege` is created for BookingPro.
- BookingPro groups use `privilege_id` instead of the older `category_id` field on `res.groups`.
- Backend list views use Odoo 19 `list` view syntax instead of older `tree` root tags.

If you previously installed an older copy and the install failed, replace the folder with this version, restart Odoo, update the Apps list, then install/upgrade BookingPro.


## Odoo 19 Testing Command

After copying this folder to your custom addons path, update apps list and install with:

```bash
sudo -u odoo odoo -c /etc/odoo/odoo.conf -d YOUR_DB -i bookingpro --stop-after-init
```

If the module was already installed, use:

```bash
sudo -u odoo odoo -c /etc/odoo/odoo.conf -d YOUR_DB -u bookingpro --stop-after-init
```

This package was statically checked for Python syntax, XML parsing, duplicate XML IDs, missing local XML references, and missing custom fields/methods in custom views. Runtime testing still needs to be done inside the target Odoo 19 database because Odoo itself is not available in this sandbox.


## Odoo 19 Security Compatibility Patch

This build avoids deprecated Odoo 18/older XML patterns on `res.groups`.

- Uses `res.groups.privilege` and `privilege_id` for Odoo 19 group placement.
- Does not use the removed inverse field `res.groups.users`.
- Does not write directly to `res.users.groups_id`; instead, `base.group_system` implies the BookingPro Administrator group for Odoo 19 compatibility.

If upgrading from an older broken package, replace the complete `bookingpro` folder, restart Odoo, update the apps list, then install/update the module.


## Latest Odoo 19 Action Target Patch

This build replaces the deprecated/invalid `ir.actions.act_window.target = inline` value with `current`, because this Odoo 19 environment rejects `inline` during module XML import.


## Latest Odoo 19 Kanban Card Patch

This build replaces the legacy kanban template name `kanban-box` with the Odoo 19-compatible `card` template. This fixes the Owl client error: `Missing 'card' template` when opening BookingPro kanban views.


## Version 19.0.2.0.0 - Completed Missing Business Flow

This update covers the missing workflow items requested after initial testing:

1. **CRM Lead Capture**
   - Every public booking can automatically create a linked CRM lead.
   - Appointment form has CRM Lead smart button and CRM Lead tab.
   - BookingPro menu now includes Operations > CRM Leads.

2. **Follow-up System**
   - Appointment form has follow-up state, responsible user, date, notes, and activity link.
   - Manual button: Schedule Follow-up.
   - Automatic follow-up can be enabled after Completed/No-show appointments.
   - BookingPro menu now includes Operations > Follow-ups.

3. **Multi-tenant / Client Booking Link**
   - Each company/client can have a unique booking slug.
   - Client link format: `/bookingpro/c/<client-slug>`.
   - Services and bookings are filtered by company/client.
   - Configure from BookingPro Settings or company form.

4. **SMTP / Email Reminders**
   - Uses Odoo Outgoing Mail Server / SMTP.
   - Cron sends reminders approximately 5 hours and 1 hour before confirmed appointments.
   - Reminder status is tracked on the appointment.

5. **Read.ai Integration Hook**
   - Store Read.ai meeting/recording URL on the appointment.
   - Send appointment payload to a configured Read.ai API/webhook URL.
   - Status and response are logged in the appointment.

## Recommended Test Flow

1. Configure Odoo Outgoing Mail Server / SMTP.
2. Go to BookingPro > Configuration > Settings.
3. Set Client Booking Slug and copy Client Booking Link.
4. Enable CRM Lead creation, follow-up, and reminders.
5. Create service category, service, resource, staff, and staff availability.
6. Open `/bookingpro/c/<client-slug>` and create a booking.
7. Confirm the appointment in backend.
8. Verify CRM lead, calendar event, reminder flags, and follow-up activity.
9. Add Read.ai meeting URL and click Send to Read.ai after API/webhook setup.


Odoo 19 website slug hotfix
---------------------------
This package avoids direct website-controller domain searches on the computed
`res.company.bookingpro_slug` field. The client booking link resolver now reads
company slugs through `ir.config_parameter`, preventing `OrderedSet has no
attribute strip` errors on `/bookingpro/c/<slug>/...` routes.


## Customer follow-up email workflow

This version includes a complete customer-facing follow-up system:

- Public booking form includes a customer follow-up checkbox and message field.
- New bookings can automatically request follow-up and queue a follow-up email through Odoo SMTP / Outgoing Mail Server.
- Customer portal appointment detail allows customers to request or update follow-up messages.
- Admin/staff portal workspace allows internal users to schedule follow-up, send customer follow-up email, and mark follow-up done.
- Backend appointment form includes customer follow-up status, due datetime, email queue timestamp, and error tracking.
- Cron `BookingPro: Send Customer Follow-up Emails` sends delayed follow-up emails when configured.

SMTP is not custom-coded inside the module. The module uses Odoo's native outgoing mail server configuration. Configure SMTP from Settings > Technical > Email > Outgoing Mail Servers.


## Recurring customer follow-up emails

BookingPro can send customer follow-up emails automatically after booking. Configure the interval from BookingPro Settings or the Portal Workspace Settings. Supported operational options are every 1 hour or every 5 hours. The cron `BookingPro: Send Customer Follow-up Emails` checks due appointments every 15 minutes, queues the follow-up email through the standard Odoo SMTP/outgoing mail server, increments the sent counter, and schedules the next email until the maximum email count is reached or the follow-up is marked done.


## Portal SMTP / Email Setup
BookingPro includes a portal-managed SMTP setup page so client/admin users do not need to open Odoo backend Settings.

Portal URL:

    /bookingpro/workspace/smtp

From this page a BookingPro manager can create/update an Odoo outgoing mail server, select it for BookingPro, configure From Email/Name, and send a test email. BookingPro confirmation, reminder, cancellation, reschedule, and customer follow-up emails use the selected SMTP server where supported by the Odoo mail engine.


## Premium Portal Workspace
This build includes a custom high-class portal workspace at `/bookingpro/workspace`. Admins and booking managers can manage appointments, services, categories, resources, staff availability, CRM leads, settings, SMTP, follow-ups, reminders and Read.ai hooks from the portal without opening the standard Odoo backend.

Portal management URLs:
- `/bookingpro/workspace` dashboard
- `/bookingpro/workspace/appointments`
- `/bookingpro/workspace/services`
- `/bookingpro/workspace/resources`
- `/bookingpro/workspace/availability`
- `/bookingpro/workspace/leads`
- `/bookingpro/workspace/settings`
- `/bookingpro/workspace/smtp`


## Customer Portal Backend Guard

Customer portal pages hide Odoo frontend-to-backend/editor chrome and keep customer users inside `/my/bookingpro`. Admin and Booking Manager users retain the full BookingPro workspace at `/bookingpro/workspace`.
