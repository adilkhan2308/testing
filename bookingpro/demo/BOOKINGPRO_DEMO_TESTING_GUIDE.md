# BookingPro Demo Testing Data

This module includes demo data to make portal testing easier without changing the module logic.

## Admin / Booking Manager Portal Test

Use your existing Odoo admin account, then open:

- `/bookingpro/workspace`

You should see demo services, demo resources, staff availability, CRM leads, and demo appointments.

## Public Booking Test

Open:

- `/bookingpro`

Use one of the demo services:

- Demo Dental Checkup
- Demo General Consultation

The demo staff availability is Monday to Friday, 09:00 to 17:00 with a 13:00 to 14:00 break.

## Customer Portal Test

1. Open `/bookingpro/signup`.
2. Create a customer account using this exact email:

   `demo.customer@bookingpro.test`

3. Use any password with at least 6 characters.
4. Login with the new customer account.
5. Open `/my/bookingpro`.

Because the demo data already creates a customer contact with this email, the signup flow links the portal user to the existing demo customer. The customer portal should show the demo customer appointments.

## Demo Customer Records

- Demo Customer Adil: `demo.customer@bookingpro.test`
- Demo Customer Abigail: `demo.abigail@bookingpro.test`

## Demo Data Included

- 2 demo customers
- 2 service categories
- 2 services
- 2 resources
- Monday-Friday staff availability for the admin user
- 4 demo appointments with pending, confirmed, completed, and reschedule requested states
- BookingPro config parameters for CRM leads, follow-up, portal cancel/reschedule, and slot intervals
