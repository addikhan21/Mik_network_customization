from odoo import http, fields
from odoo.http import request
import os
from calendar import monthrange
from datetime import datetime
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class DiskUsageController(http.Controller):

    @http.route(
        "/api/disk-usage",
        type="json",
        auth="user",
    )
    def get_disk_usage(
        self,
    ):
        statvfs = os.statvfs("/")
        total_space = (
            statvfs.f_frsize * statvfs.f_blocks / (1024 * 1024 * 1024)
        )  # Total in GB
        free_space = (
            statvfs.f_frsize * statvfs.f_bfree / (1024 * 1024 * 1024)
        )  # Free in GB
        used_space = total_space - free_space
        percent_used = (used_space / total_space) * 100

        return {
            "total_space": total_space,
            "used_space": used_space,
            "free_space": free_space,
            "percent_used": percent_used,
            "message": f"Server storage: {total_space:.1f}GB total capacity with {free_space:.1f}GB available. Currently using {percent_used:.1f}% of disk space.",
        }

    @http.route("/api/current-balance", type="json", auth="user")
    def get_current_balance(self):
        return {"current_balance": "N/A"}

    @http.route("/api/refresh-message", type="json", auth="user")
    def get_refresh_message(self):
        return {
            "heading": "System Notice",
            "message": "Service is operating normally",
            "status": "fallback",
        }


    @http.route("/api/admin-home", type="json", auth="user")
    def get_admin_home(self):
        return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Only for Distributors",
                    "message": "There is nothing for you to see here",
                    "type": "warning",
                },
            }

    @http.route("/api/user-stats", type="json", auth="user")
    def get_user_stats(self):
        # Simplified query using company-based filtering
        query = """
            WITH user_metrics AS (
                SELECT
                    ru.id,
                    ru.username,
                    ru.is_disable,
                    ru.expiry_date,
                    COUNT(ra.username) as active_sessions
                FROM users ru
                LEFT JOIN radacct ra ON ru.username = ra.username
                    AND ra.acctstoptime IS NULL
                WHERE ru.company_id IN %s
                GROUP BY ru.id, ru.username, ru.is_disable, ru.expiry_date
            ),
            status_counts AS (
                SELECT
                    COUNT(*) as total_users,
                    SUM(CASE WHEN active_sessions >= 1 THEN 1 ELSE 0 END) as online_count,
                    SUM(CASE WHEN expiry_date > NOW() THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN expiry_date <= NOW() OR expiry_date IS NULL THEN 1 ELSE 0 END) as inactive_count,
                    SUM(CASE WHEN is_disable = TRUE THEN 1 ELSE 0 END) as disabled_count
                FROM user_metrics
            )
            SELECT
                COALESCE(online_count, 0) as online_count,
                COALESCE(GREATEST(active_count - online_count, 0), 0) as offline_count,
                COALESCE(active_count, 0) as active_count,
                COALESCE(inactive_count, 0) as inactive_count,
                COALESCE(total_users, 0) as total_count,
                COALESCE(disabled_count, 0) as disabled_count
            FROM status_counts
        """

        # Get distributor IDs based on user's allowed companies
        allowed_companies = [request.env.company.id]

        # Execute query
        result = {}
        if allowed_companies:
            request.env.cr.execute(query, (tuple(allowed_companies),))
            result = request.env.cr.dictfetchone()

        return {
            "online": result.get("online_count", 0) if result else 0,
            "offline": result.get("offline_count", 0) if result else 0,
            "active": result.get("active_count", 0) if result else 0,
            "inactive": result.get("inactive_count", 0) if result else 0,
            "disabled": result.get("disabled_count", 0) if result else 0,
            "total": result.get("total_count", 0) if result else 0,
        }
        # return {
        #     "online": 147,
        #     "offline": 234,
        #     "active": 381,
        #     "inactive": 89,
        #     "disabled": 23,
        #     "total": 493,
        # }
    @http.route("/api/package-subscriptions", type="json", auth="user")
    def get_package_subscriptions(self):
        dummy_result = [
            {"package_name": "Premium Plus", "subscription_count": 156},
            {"package_name": "Business Pro", "subscription_count": 124},
            {"package_name": "Standard", "subscription_count": 98},
            {"package_name": "Basic Plan", "subscription_count": 87},
            {"package_name": "Enterprise", "subscription_count": 45},
            {"package_name": "Starter", "subscription_count": 32},
        ]

        return {
            "labels": [r["package_name"] for r in dummy_result],
            "data": [r["subscription_count"] for r in dummy_result],
            "message": f"Total active subscriptions: {sum(r['subscription_count'] for r in dummy_result)}",
        }

    @http.route("/api/top-franchises", type="json", auth="user")
    def get_top_franchises(self):
        dummy_franchises = [
            {"distributor_id": [1, "Metro Tech Solutions"], "distributor_id_count": 89},
            {"distributor_id": [2, "Digital Networks Pro"], "distributor_id_count": 76},
            {"distributor_id": [3, "ConnectPoint Systems"], "distributor_id_count": 64},
            {"distributor_id": [4, "TechHub Distributors"], "distributor_id_count": 52},
            {"distributor_id": [5, "NetworkMax Solutions"], "distributor_id_count": 41},
        ]

        return {
            "labels": [(franchise["distributor_id"][1]if franchise["distributor_id"]else "N/A")for franchise in dummy_franchises],
            "data": [franchise["distributor_id_count"] for franchise in dummy_franchises],
            "message": f"Top 5 Distributors by Online users"}

    @http.route('/api/calendar-events', type='json', auth='user', methods=['POST'], csrf=False)
    def get_calendar_events(self):
        """Get 20 most recent calendar events"""
        try:

            user = request.env.user
            today = fields.Date.today()

            # Calculate start and end of current week
            start_of_week = today - timedelta(days=today.weekday())  # Monday
            end_of_week = start_of_week + timedelta(days=6)  # Sunday

            # Convert to datetime for full day coverage
            start_datetime = datetime.combine(start_of_week, datetime.min.time())
            end_datetime = datetime.combine(end_of_week, datetime.max.time())

            # Get current week events
            events = request.env['calendar.event'].search([
                ('user_id', '=', user.id),
                ('start', '>=', start_datetime),
                ('start', '<=', end_datetime)
            ], order='start asc')

            event_data = []
            for event in events:
                event_data.append({
                    'id': event.id,
                    'name': event.name,
                    'description': event.description or '',
                    'start': event.start.strftime('%Y-%m-%d %H:%M') if event.start else '',
                    'stop': event.stop.strftime('%Y-%m-%d %H:%M') if event.stop else '',
                    'duration': event.duration,
                    'location': event.location or '',
                    'partner_ids': [partner.name for partner in event.partner_ids],
                    'state': event.alarm_ids.mapped('name') if event.alarm_ids else [],
                    'allday': event.allday,
                })

            return {
                'status': 'success',
                'events': event_data,
                'count': len(event_data),
                'date': today.strftime('%Y-%m-%d')
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'events': [],
                'count': 0
            }



    @http.route('/api/financial-metrics', type='json', auth='user', methods=['POST'])
    def get_financial_metrics(self, **kwargs):
        """Get comprehensive financial metrics for dashboard"""
        try:
            # Get current month date range
            today = fields.Date.today()
            start_of_month = today.replace(day=1)

            # Monthly Recurring Revenue from active subscriptions
            active_subscriptions = request.env['sale.subscription'].sudo().search([
                ('stage_id.type', '=', 'in_progress'),
                ('company_id', '=', request.env.company.id)
            ])

            # mrr = sum(sub.recurring_total for sub in active_subscriptions if hasattr(sub, 'recurring_total'))
            mrr = sum(active_subscriptions.mapped('recurring_total'))
            active_sub_count = len(active_subscriptions)

            # Paid Invoices (Current Month)
            paid_invoices = request.env['account.move'].sudo().search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '=', 'paid'),
                ('invoice_date', '>=', start_of_month),
                ('invoice_date', '<=', today),
                ('company_id', '=', request.env.company.id)
            ])
            # total_revenue = sum(inv.amount_total for inv in paid_invoices)
            total_revenue = sum(paid_invoices.mapped('amount_total'))


            # Unpaid Invoices
            unpaid_invoices = request.env['account.move'].sudo().search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('company_id', '=', request.env.company.id)
            ])
            unpaid_count = len(unpaid_invoices)
            # unpaid_amount = sum(inv.amount_residual for inv in unpaid_invoices)
            unpaid_amount = sum(unpaid_invoices.mapped('amount_residual'))


            # Overdue Invoices
            overdue_invoices = request.env['account.move'].sudo().search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_date_due', '<', today),
                ('company_id', '=', request.env.company.id)
            ])
            overdue_count = len(overdue_invoices)
            # overdue_amount = sum(inv.amount_residual for inv in overdue_invoices)
            overdue_amount = sum(overdue_invoices.mapped('amount_residual'))

            # Customers with Outstanding Balance
            partners_with_balance = request.env['res.partner'].sudo().search([
                ('credit', '>', 0),
                ('company_id', '=', request.env.company.id)
            ])
            outstanding_customers = len(partners_with_balance)

            # Average Revenue Per User (ARPU)
            total_customers = request.env['sale.subscription'].sudo().search_count([
                ('stage_id.type', '=', 'in_progress'),
                ('company_id', '=', request.env.company.id)
            ])
            arpu = mrr / total_customers if total_customers > 0 else 0

            # Churned Subscriptions (this month)
            churned_subscriptions = request.env['sale.subscription'].sudo().search_count([
                ('stage_id.type', '=', 'post'),
                ('write_date', '>=', start_of_month),
                ('write_date', '<=', today),
                ('company_id', '=', request.env.company.id)
            ])

            return {
                'status': 'success',
                'data': {
                    'mrr': round(mrr, 2),
                    'total_revenue': round(total_revenue, 2),
                    'unpaid_invoices': {
                        'count': unpaid_count,
                        'amount': round(unpaid_amount, 2)
                    },
                    'paid_invoices': round(total_revenue, 2),
                    'overdue_invoices': {
                        'count': overdue_count,
                        'amount': round(overdue_amount, 2)
                    },
                    'active_subscriptions': active_sub_count,
                    'outstanding_customers': outstanding_customers,
                    'arpu': round(arpu, 2),
                    'churned_subscriptions': churned_subscriptions
                }
            }

        except Exception as e:
            _logger.error(f"Error fetching financial metrics: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
