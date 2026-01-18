from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class BusinessIntelligenceController(http.Controller):

    @http.route('/stats/business_intelligence_data', type='json', auth='user')
    def get_business_intelligence_data(self):
        """Get comprehensive business intelligence metrics"""
        try:
            # Get current month date range
            today = datetime.now()
            first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Purchase Orders
            purchase_orders = self._get_purchase_orders(first_day)

            # Internal Transfers
            internal_transfers = self._get_internal_transfers(first_day)

            # Sales Opportunities
            opportunities = self._get_opportunities()

            # Stock Alerts
            stock_alerts = self._get_stock_alerts()

            # Support Tickets (if helpdesk module installed)
            tickets = self._get_support_tickets()

            return {
                'success': True,
                'data': {
                    'purchaseOrders': purchase_orders,
                    'internalTransfers': internal_transfers,
                    'opportunities': opportunities,
                    'stockAlerts': stock_alerts,
                    'tickets': tickets,
                    'lastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        except Exception as e:
            _logger.error(f"Error fetching business intelligence data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_purchase_orders(self, first_day):
        """Get purchase order statistics"""
        try:
            PurchaseOrder = request.env['purchase.order']

            # Current month POs
            domain = [('date_order', '>=', first_day.strftime('%Y-%m-%d'))]
            pos = PurchaseOrder.sudo().search(domain)

            total_amount = sum(pos.mapped('amount_total'))
            pending = PurchaseOrder.search_count(domain + [('state', 'in', ['draft', 'sent'])])
            approved = PurchaseOrder.search_count(domain + [('state', '=', 'purchase')])

            return {
                'count': len(pos),
                'total': total_amount,
                'pending': pending,
                'approved': approved
            }
        except Exception as e:
            _logger.error(f"Error in _get_purchase_orders: {str(e)}")
            return {'count': 0, 'total': 0, 'pending': 0, 'approved': 0}

    def _get_internal_transfers(self, first_day):
        """Get internal transfer statistics"""
        try:
            StockPicking = request.env['stock.picking']

            domain = [
                ('picking_type_code', '=', 'internal'),
                ('create_date', '>=', first_day.strftime('%Y-%m-%d'))
            ]

            transfers = StockPicking.sudo().search(domain)
            items_moved = sum(len(t.move_ids_without_package) for t in transfers)

            in_progress = StockPicking.sudo().search_count(domain + [('state', 'in', ['confirmed', 'assigned'])])
            done = StockPicking.sudo().search_count(domain + [('state', '=', 'done')])
            return {
                'count': len(transfers),
                'items': items_moved,
                'inProgress': in_progress,
                'done': done
            }
        except Exception as e:
            _logger.error(f"Error in _get_internal_transfers: {str(e)}")
            return {'count': 0, 'items': 0, 'inProgress': 0, 'done': 0}

    def _get_opportunities(self):
        """Get sales opportunities statistics"""
        try:
            Lead = request.env['crm.lead']

            domain = [('type', '=', 'opportunity'), ('active', '=', True)]
            opportunities = Lead.sudo().search(domain)

            pipeline_value = sum(opp.expected_revenue for opp in opportunities if not opp.stage_id.is_won)
            won = Lead.sudo().search_count([('type', '=', 'opportunity'), ('stage_id.is_won', '=', True)])
            lost = Lead.sudo().search_count([('type', '=', 'opportunity'), ('probability', '=', 0)])
            return {
                'count': len(opportunities),
                'pipelineValue': pipeline_value,
                'won': won,
                'lost': lost
            }
        except Exception as e:
            _logger.error(f"Error in _get_opportunities: {str(e)}")
            return {'count': 0, 'pipelineValue': 0, 'won': 0, 'lost': 0}

    def _get_stock_alerts(self):
        """Get stock alert statistics"""
        try:
            Product = request.env['product.product']
            Quant = request.env['stock.quant']

            products = Product.sudo().search([('type', '=', 'product')])

            out_of_stock = 0
            low_stock = 0

            for product in products:
                qty = sum(Quant.sudo().search([('product_id', '=', product.id)]).mapped('quantity'))

                if qty <= 0:
                    out_of_stock += 1
                elif qty < 10:
                    low_stock += 1

            return {
                'count': out_of_stock + low_stock,
                'outOfStock': out_of_stock,
                'lowStock': low_stock
            }
        except Exception as e:
            _logger.error(f"Error in _get_stock_alerts: {str(e)}")
            return {'count': 0, 'outOfStock': 0, 'lowStock': 0}

    def _get_support_tickets(self):
        """Get support ticket statistics"""
        try:
            # Check if helpdesk module is installed
            # if 'helpdesk.ticket' not in request.env:
            #     return {'openCount': 0, 'resolvedCount': 0, 'urgentCount': 0, 'pendingCount': 0}

            Ticket = request.env['helpdesk.ticket']

            open_count = Ticket.sudo().search_count([("stage_id.closed", "!=", True)])

            first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            resolved_count = Ticket.sudo().search_count([
                ("stage_id.closed", "=", True),
                ('closed_date', '>=', first_day)  # Compare datetime with datetime
            ])
            
            urgent_count = Ticket.sudo().search_count([
                ('priority', '=', '3'),
                ("stage_id.closed", "!=", True)
            ])

            pending_count = Ticket.sudo().search_count([
                ("stage_id.closed", "!=", True),
                ('priority', 'in', ['1', '2'])
            ])

            return {
                'openCount': open_count,
                'resolvedCount': resolved_count,
                'urgentCount': urgent_count,
                'pendingCount': pending_count
            }
        except Exception as e:
            _logger.error(f"Error in _get_support_tickets: {str(e)}")
            return {'openCount': 0, 'resolvedCount': 0, 'urgentCount': 0, 'pendingCount': 0}