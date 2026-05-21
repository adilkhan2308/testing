# -*- coding: utf-8 -*-
"""BookingPro branded authentication and role routing.

This controller keeps the standard Odoo authentication engine, but replaces the
visual login/register entry point with a BookingPro-specific interface and sends
users to the correct portal area after login:
- BookingPro Administrator / Booking Manager -> workspace dashboard
- BookingPro Staff -> workspace appointments
- Customer / Portal user -> customer portal appointments
"""

import logging

from odoo import http, _
from odoo.exceptions import AccessDenied
from odoo.http import request

try:  # Odoo 17+ / 18+ / 19 style
    from odoo.addons.web.controllers.home import Home
except Exception:  # pragma: no cover - older compatibility fallback
    from odoo.addons.web.controllers.main import Home

try:
    from odoo.addons.web.controllers.utils import ensure_db
except Exception:  # pragma: no cover - older compatibility fallback
    from odoo.addons.web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)


class BookingProAuth(Home):
    """Custom branded login/signup while preserving Odoo's session handling."""

    def _is_public_user(self):
        try:
            return request.env.user._is_public()
        except Exception:
            return not bool(request.session.uid)

    def _safe_has_group(self, user, xmlid):
        try:
            return bool(user and user.exists() and user.has_group(xmlid))
        except Exception:
            return False

    def _is_internal_backend_user(self, user=None):
        """True for users who should keep Odoo backend/app access.

        Important rule for BookingPro:
        - Customer/portal users must never see the Odoo backend.
        - Admin/manager/internal users must never be blocked from the backend.

        Some Odoo 19 builds or custom databases do not expose group relations in
        exactly the same way, so we combine explicit BookingPro manager groups
        with the standard internal-user marker and the share flag.
        """
        user = user or request.env.user
        if not user or not user.exists():
            return False
        try:
            # Portal/customer users are external users. Even if some group check is
            # noisy, share=True must always be treated as customer-only access.
            if getattr(user, 'share', False):
                return False
        except Exception:
            pass
        return (
            self._safe_has_group(user, 'base.group_system')
            or self._safe_has_group(user, 'base.group_user')
            or self._safe_has_group(user, 'bookingpro.group_bookingpro_manager')
            or self._safe_has_group(user, 'bookingpro.group_bookingpro_booking_manager')
        )

    def _is_bookingpro_manager_user(self, user=None):
        user = user or request.env.user
        return (
            self._safe_has_group(user, 'base.group_system')
            or self._safe_has_group(user, 'bookingpro.group_bookingpro_manager')
            or self._safe_has_group(user, 'bookingpro.group_bookingpro_booking_manager')
        )

    def _is_bookingpro_staff_user(self, user=None):
        user = user or request.env.user
        return (
            self._safe_has_group(user, 'bookingpro.group_bookingpro_staff')
            and not self._is_bookingpro_manager_user(user)
        )

    def _bookingpro_user_target(self, user=None):
        user = user or request.env.user
        if self._is_bookingpro_manager_user(user):
            # BookingPro admins/managers can use the premium workspace and still
            # keep full Odoo backend access through /web or the app switcher.
            return '/bookingpro/workspace'
        if self._is_bookingpro_staff_user(user):
            return '/bookingpro/workspace/appointments'
        return '/my/bookingpro'

    def _bookingpro_backend_target_for_user(self, user=None):
        """Return a redirect only for users who must not enter /web.

        Admin / internal users return False, which allows Odoo backend normally.
        Customer portal users are sent back to the customer portal. Staff-only
        users are sent to the staff workspace.
        """
        user = user or request.env.user
        if self._is_bookingpro_manager_user(user):
            return False
        if self._is_bookingpro_staff_user(user):
            return '/bookingpro/workspace/appointments'
        if self._is_internal_backend_user(user):
            return False
        return '/my/bookingpro'

    def _bookingpro_backend_url(self):
        # Odoo 18/19 commonly uses /odoo for the backend web client.
        # Keep this centralized so portal buttons never point to a missing /web website page.
        return '/odoo'

    @http.route(['/web', '/web/', '/odoo', '/odoo/', '/odoo/<path:path>'], type='http', auth='user', website=False, sitemap=False)
    def web_client(self, s_action=None, path=None, **kw):
        """Guard Odoo backend access for BookingPro roles.

        This catches direct backend access, old login redirects, and app-switcher
        attempts. Admins/managers keep backend access; staff/customers are routed
        to the correct custom portal pages. The catch-all /odoo/<path:path> is
        important in Odoo 19 because the backend web client can use /odoo URLs.
        """
        target = self._bookingpro_backend_target_for_user(request.env.user)
        if target:
            return request.redirect(target)
        return super().web_client(s_action=s_action, **kw)

    @http.route('/bookingpro/backend', type='http', auth='user', website=False, sitemap=False)
    def bookingpro_backend_entry(self, **kw):
        """Stable backend entry point for BookingPro portal buttons.

        Customer/portal users are protected from backend access, while admins and
        internal users are sent into Odoo's native backend web client. We render
        the web client directly instead of redirecting to /web or /odoo, because
        some Odoo 19 website configurations can otherwise show a website 404 page.
        """
        target = self._bookingpro_backend_target_for_user(request.env.user)
        if target:
            return request.redirect(target)
        return super().web_client(**kw)

    def _resolve_login_identifier(self, login):
        """Allow login by email or username/login.

        Odoo authenticates against res.users.login. The branded login form accepts
        either a full email address or a short username such as "admin". Resolve
        the submitted identifier to the actual res.users.login before calling the
        native authentication engine.
        """
        login = (login or '').strip()
        if not login:
            return login
        try:
            Users = request.env['res.users'].sudo()
            domains = [
                [('login', '=', login)],
                [('email', '=ilike', login)],
                [('partner_id.email', '=ilike', login)],
            ]
            if '@' not in login:
                domains.append([('name', '=ilike', login)])
            for domain in domains:
                users = Users.search(domain, limit=2)
                if len(users) == 1:
                    return users.login
        except Exception:
            _logger.info('BookingPro login identifier resolution failed for %s', login, exc_info=True)
        return login

    def _auth_page_values(self, **extra):
        values = {
            'page_name': 'bookingpro_auth',
            'redirect': extra.get('redirect') or request.params.get('redirect') or '/bookingpro/post-login',
            'login': extra.get('login') or request.params.get('login') or '',
            'error': extra.get('error') or request.params.get('error') or False,
            'success': extra.get('success') or request.params.get('success') or False,
            'bookingpro_company': request.env.company.sudo() if request.db else False,
            'name': extra.get('name') or request.params.get('name') or '',
            'phone': extra.get('phone') or request.params.get('phone') or '',
        }
        values.update(extra)
        return values

    def _authenticate_bookingpro_session(self, login, password):
        credential = {
            'login': login,
            'password': password,
            'type': 'password',
        }
        try:
            auth_info = request.session.authenticate(request.env, credential)
            if isinstance(auth_info, dict):
                return auth_info.get('uid') or request.session.uid
            return auth_info or request.session.uid
        except TypeError:
            return request.session.authenticate(request.db, login, password)

    @http.route('/bookingpro/post-login', type='http', auth='user', website=True, sitemap=False)
    def bookingpro_post_login(self, **kw):
        """Role-based landing page immediately after successful login."""
        return request.redirect(self._bookingpro_user_target())

    @http.route(['/bookingpro/customer', '/bookingpro/customer-portal'], type='http', auth='user', website=True, sitemap=False)
    def bookingpro_customer_portal_entry(self, **kw):
        """Stable customer portal entry used as a fallback for login redirects."""
        return request.redirect('/my/bookingpro')

    @http.route('/bookingpro/login', type='http', auth='public', website=True, sitemap=False)
    def bookingpro_login_page(self, redirect=None, **kw):
        ensure_db()
        if not self._is_public_user():
            return request.redirect(redirect or self._bookingpro_user_target())
        values = self._auth_page_values(redirect=redirect or '/bookingpro/post-login')
        return request.render('bookingpro.bookingpro_login_page', values)

    @http.route('/web/login', type='http', auth='public', website=True, sitemap=False, methods=['GET', 'POST'], csrf=False)
    def web_login(self, redirect=None, **kw):
        """Replace the standard Odoo login screen with BookingPro branding.

        POST login is handled here so customer accounts can never be dropped on
        Odoo's default /web or /odoo page by an old redirect parameter. After a
        successful login, the role target is calculated from the authenticated
        user record directly.
        """
        ensure_db()
        redirect = redirect or kw.get('redirect') or '/bookingpro/post-login'
        if request.httprequest.method == 'POST':
            login = (kw.get('login') or '').strip()
            password = kw.get('password') or ''
            try:
                auth_login = self._resolve_login_identifier(login)
                uid = self._authenticate_bookingpro_session(auth_login, password)
                user = request.env['res.users'].sudo().browse(uid)
                target = self._bookingpro_user_target(user)
                return request.redirect(target)
            except AccessDenied:
                _logger.info('BookingPro login failed for %s', login)
                values = self._auth_page_values(
                    redirect='/bookingpro/post-login',
                    login=login,
                    error=_('Wrong login or password. Please try again.'),
                )
                return request.render('bookingpro.bookingpro_login_page', values)
            except Exception:
                _logger.info('BookingPro login failed for %s', login, exc_info=True)
                values = self._auth_page_values(
                    redirect='/bookingpro/post-login',
                    login=login,
                    error=_('Wrong login or password. Please try again.'),
                )
                return request.render('bookingpro.bookingpro_login_page', values)
        if request.session.uid:
            return request.redirect(self._bookingpro_user_target())
        values = self._auth_page_values(redirect=redirect, login=kw.get('login'))
        return request.render('bookingpro.bookingpro_login_page', values)

    @http.route(['/bookingpro/signup', '/web/signup'], type='http', auth='public', website=True, sitemap=False, methods=['GET', 'POST'], csrf=True)
    def bookingpro_signup(self, **post):
        """Create a customer/portal-style BookingPro account.

        This route intentionally creates customer accounts only. Admin and staff
        access must be granted by an existing administrator through Odoo groups,
        which keeps backend/workspace access protected.
        """
        ensure_db()
        if not self._is_public_user():
            return request.redirect(self._bookingpro_user_target())

        values = self._auth_page_values(signup_mode=True)
        if request.httprequest.method != 'POST':
            return request.render('bookingpro.bookingpro_signup_page', values)

        name = (post.get('name') or '').strip()
        email = (post.get('email') or post.get('login') or '').strip().lower()
        phone = (post.get('phone') or '').strip()
        password = post.get('password') or ''
        confirm_password = post.get('confirm_password') or ''
        role = (post.get('role') or 'customer').strip()

        values.update({'name': name, 'login': email, 'phone': phone})
        if role != 'customer':
            values['error'] = _('Only customer self-registration is allowed. Admin and staff accounts must be configured by an administrator.')
            return request.render('bookingpro.bookingpro_signup_page', values)
        if not name or not email or not password:
            values['error'] = _('Please fill name, email, and password.')
            return request.render('bookingpro.bookingpro_signup_page', values)
        if password != confirm_password:
            values['error'] = _('Password and confirmation password do not match.')
            return request.render('bookingpro.bookingpro_signup_page', values)
        if len(password) < 6:
            values['error'] = _('Please use a password with at least 6 characters.')
            return request.render('bookingpro.bookingpro_signup_page', values)

        Users = request.env['res.users'].sudo()
        Partner = request.env['res.partner'].sudo()
        if Users.search([('login', '=', email)], limit=1):
            values['error'] = _('An account already exists for this email. Please log in instead.')
            return request.render('bookingpro.bookingpro_signup_page', values)

        company = request.env.company.sudo()
        try:
            partner = Partner.search([('email', '=', email)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'company_type': 'person',
                    'company_id': company.id,
                    'bookingpro_customer_note': _('Self-registered from BookingPro portal.'),
                })
            else:
                partner.write({
                    'name': partner.name or name,
                    'phone': partner.phone or phone,
                    'bookingpro_customer_note': (partner.bookingpro_customer_note or '') + ('\n' if partner.bookingpro_customer_note else '') + _('Self-registration attempted from BookingPro portal.'),
                })

            user_vals = {
                'name': name,
                'login': email,
                'email': email,
                'password': password,
                'partner_id': partner.id,
                'company_id': company.id,
                'company_ids': [(6, 0, [company.id])],
                # share=True keeps the user external/portal-style and prevents
                # internal backend access even when group assignment APIs differ
                # between Odoo versions.
                'share': True,
            }
            user = Users.with_context(no_reset_password=True, signup_valid=True).create(user_vals)
            self._assign_customer_groups_safely(user)
        except Exception as exc:
            _logger.exception('BookingPro customer signup failed')
            values['error'] = _('Could not create the account. Please contact the team. Technical detail: %s') % (str(exc)[:160],)
            return request.render('bookingpro.bookingpro_signup_page', values)

        return request.redirect('/bookingpro/login?success=account_created&login=%s' % email)

    def _assign_customer_groups_safely(self, user):
        """Assign portal/customer group when the current Odoo build exposes a
        writable group relation. Some Odoo 19 builds hide groups_id during XML
        loading, so this method is defensive and non-blocking.
        """
        groups = []
        for xmlid in ('bookingpro.group_bookingpro_customer', 'base.group_portal'):
            try:
                group = request.env.ref(xmlid, raise_if_not_found=False)
                if group:
                    groups.append(group.id)
            except Exception:
                continue
        if not groups:
            return
        for field_name in ('groups_id', 'group_ids'):
            try:
                if field_name in user._fields:
                    user.sudo().write({field_name: [(4, group_id) for group_id in groups]})
                    return
            except Exception:
                _logger.info('Could not assign BookingPro customer groups using %s; continuing with share=True user.', field_name)
        return
