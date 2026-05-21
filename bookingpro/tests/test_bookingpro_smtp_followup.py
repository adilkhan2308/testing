# -*- coding: utf-8 -*-
import socketserver
import threading
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.base.models.ir_mail_server import IrMail_Server
from odoo.tests.common import TransactionCase, tagged


class _SMTPHandler(socketserver.StreamRequestHandler):

    def handle(self):
        self.server.messages = getattr(self.server, 'messages', [])
        self.wfile.write(b'220 bookingpro-test-smtp ESMTP\r\n')
        data_mode = False
        message_lines = []
        while True:
            line = self.rfile.readline()
            if not line:
                break
            command = line.decode('utf-8', errors='replace').rstrip('\r\n')
            if data_mode:
                if command == '.':
                    self.server.messages.append('\n'.join(message_lines))
                    message_lines = []
                    data_mode = False
                    self.wfile.write(b'250 2.0.0 queued\r\n')
                else:
                    message_lines.append(command)
                continue

            upper = command.upper()
            if upper.startswith(('EHLO', 'HELO')):
                self.wfile.write(b'250-bookingpro-test-smtp\r\n250 SIZE 10485760\r\n')
            elif upper.startswith('MAIL FROM'):
                self.wfile.write(b'250 2.1.0 ok\r\n')
            elif upper.startswith('RCPT TO'):
                self.wfile.write(b'250 2.1.5 ok\r\n')
            elif upper == 'DATA':
                data_mode = True
                self.wfile.write(b'354 end data with <CR><LF>.<CR><LF>\r\n')
            elif upper == 'RSET':
                self.wfile.write(b'250 2.0.0 reset\r\n')
            elif upper == 'NOOP':
                self.wfile.write(b'250 2.0.0 ok\r\n')
            elif upper == 'QUIT':
                self.wfile.write(b'221 2.0.0 bye\r\n')
                break
            else:
                self.wfile.write(b'250 2.0.0 ok\r\n')


class _ThreadedSMTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


@contextmanager
def _smtp_capture_server():
    server = _ThreadedSMTPServer(('127.0.0.1', 0), _SMTPHandler)
    server.messages = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@tagged('post_install', '-at_install')
class TestBookingProSmtpFollowup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.staff_user = cls.env.user
        cls.category = cls.env['bookingpro.category'].create({
            'name': 'SMTP Follow-up Category',
            'company_id': cls.company.id,
            'website_published': True,
        })
        cls.service = cls.env['bookingpro.service'].create({
            'name': 'SMTP Follow-up Service',
            'category_id': cls.category.id,
            'duration': 1.0,
            'price': 75.0,
            'company_id': cls.company.id,
            'website_published': True,
            'staff_user_ids': [(6, 0, [cls.staff_user.id])],
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'SMTP Follow-up Customer',
            'email': 'smtp.followup.customer@example.test',
            'company_id': cls.company.id,
        })

    def setUp(self):
        super().setUp()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('bookingpro.enable_customer_followup', 'True')
        icp.set_param('bookingpro.auto_customer_followup_on_booking', 'False')
        icp.set_param('bookingpro.create_internal_activity_for_customer_followup', 'True')
        icp.set_param('bookingpro.send_customer_followup_email_on_booking', 'True')
        icp.set_param('bookingpro.customer_followup_interval_hours', '1')
        icp.set_param('bookingpro.customer_followup_max_emails', '2')

    def _create_due_followup_appointment(self):
        start = fields.Datetime.now() + timedelta(days=1)
        appointment = self.env['bookingpro.appointment'].create({
            'partner_id': self.partner.id,
            'service_id': self.service.id,
            'staff_user_id': self.staff_user.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
            'state': 'confirmed',
            'company_id': self.company.id,
            'customer_followup_requested': False,
        })
        appointment.action_request_customer_followup('Please send details after booking.')
        appointment.write({
            'customer_followup_next_email_datetime': fields.Datetime.now() - timedelta(minutes=1),
            'customer_followup_due_datetime': fields.Datetime.now() - timedelta(minutes=1),
            'customer_followup_email_count': 0,
        })
        return appointment

    def _mail_recipient_emails(self, mail):
        raw_email_to = (mail.email_to or '').replace(',', ' ').split()
        partner_emails = mail.recipient_ids.mapped('email')
        message_partner_emails = mail.mail_message_id.partner_ids.mapped('email')
        return {email.strip() for email in raw_email_to + partner_emails + message_partner_emails if email}

    def test_followup_cron_queues_mail_with_selected_smtp_server(self):
        mail_server = self.env['ir.mail_server'].sudo().create({
            'name': 'BookingPro Test SMTP',
            'smtp_host': '127.0.0.1',
            'smtp_port': 2525,
            'smtp_encryption': 'none',
            'smtp_authentication': 'login',
            'sequence': 1,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'bookingpro.mail_server_id.company_%s' % self.company.id,
            str(mail_server.id),
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'bookingpro.smtp_from_email.company_%s' % self.company.id,
            'bookingpro@example.test',
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'bookingpro.smtp_from_name.company_%s' % self.company.id,
            'BookingPro QA',
        )

        appointment = self._create_due_followup_appointment()
        self.env['bookingpro.appointment'].cron_send_customer_followups()

        mail = self.env['mail.mail'].sudo().search([
            ('model', '=', 'bookingpro.appointment'),
            ('res_id', '=', appointment.id),
            ('subject', 'ilike', 'Follow-up for your appointment'),
        ], limit=1)
        self.assertTrue(mail)
        self.assertEqual(mail.mail_server_id, mail_server)
        self.assertIn(self.partner.email, self._mail_recipient_emails(mail))
        self.assertIn('BookingPro QA', mail.email_from)
        self.assertIn('bookingpro@example.test', mail.email_from)
        self.assertEqual(appointment.customer_followup_email_count, 1)
        self.assertEqual(appointment.customer_followup_state, 'scheduled')
        self.assertTrue(appointment.customer_followup_next_email_datetime)
        self.assertTrue(appointment.notification_log_ids.filtered(
            lambda log: log.notification_type == 'customer_followup_email' and log.state == 'queued'
        ))

    def test_followup_mail_queue_delivers_through_smtp_socket(self):
        with _smtp_capture_server() as smtpd:
            mail_server = self.env['ir.mail_server'].sudo().create({
                'name': 'BookingPro Capture SMTP',
                'smtp_host': '127.0.0.1',
                'smtp_port': smtpd.server_address[1],
                'smtp_encryption': 'none',
                'smtp_authentication': 'login',
                'sequence': 1,
            })
            icp = self.env['ir.config_parameter'].sudo()
            icp.set_param('bookingpro.mail_server_id.company_%s' % self.company.id, str(mail_server.id))
            icp.set_param('bookingpro.smtp_from_email.company_%s' % self.company.id, 'bookingpro@example.test')
            icp.set_param('bookingpro.smtp_from_name.company_%s' % self.company.id, 'BookingPro QA')

            appointment = self._create_due_followup_appointment()
            self.env['bookingpro.appointment'].cron_send_customer_followups()
            mail = self.env['mail.mail'].sudo().search([
                ('model', '=', 'bookingpro.appointment'),
                ('res_id', '=', appointment.id),
                ('subject', 'ilike', 'Follow-up for your appointment'),
            ], limit=1)
            self.assertTrue(mail)
            mail_id = mail.id
            if 'auto_delete' in mail._fields:
                mail.write({'auto_delete': False})

            with patch.object(IrMail_Server, '_disable_send', return_value=False):
                mail.send(raise_exception=True)

            mail = self.env['mail.mail'].sudo().browse(mail_id)
            self.assertTrue(mail.exists())
            self.assertEqual(mail.state, 'sent')
            self.assertEqual(len(smtpd.messages), 1)
            sent_message = smtpd.messages[0]
            self.assertIn('Follow-up for your appointment', sent_message)
            self.assertIn('smtp.followup.customer@example.test', sent_message)
            self.assertIn('bookingpro@example.test', sent_message)
