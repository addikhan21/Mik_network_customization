/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ChartRenderer } from "./chart_renderer/chart_renderer";
import { Refresher } from "./chart_renderer/refresher.esm";
import { NotificationModal } from "./chart_renderer/notification_modal";
import { actionService } from '@web/webclient/actions/action_service';
const { Component, onWillStart, useRef, onMounted, useState } = owl;
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { browser } from "@web/core/browser/browser";
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";





export class UserStats extends Component {

    setup() {
        // this.loaderRef = useRef("loader");
        // this.containerRef = useRef("containerRef");
        this.dialogService = useService('dialog');
        this.uiService = useService('ui');
        this.state = useState({
            activeTab: 'dashboard',
            onlineUsers: 0,
            offlineUsers: 0,
            activeUsers: 0,
            inactiveUsers: 0,
            disabledUsers: 0,
            totalUsers: 0,
            current_balance: 0.00,
            company_name: "...",
            serverUtilization:{
                diskUsage: [],
                message: "Loading...",
            } ,

            packageSubscriptions:{
                subData: [],
                message: "Loading...",
                },
            topFranchises:{
                franchiseData: [],
                message: "Loading...",
            },
            calendarEvents: {
                events: [],
                count: 0,
                loading: false,
                error: null,
                date: null
            },
            financialMetrics : {
                monthlyRecurringRevenue: 0,
                totalCurrentRevenue: 0,
                unpaidInvoiceData: { count: 0, amount: 0 },
                paidCurrentRevenue: 0,
                overdueInvoiceData: { count: 0, amount: 0 },
                activeSubscriptionCount: 0,
                outstandingCustomerCount: 0,
                averageRevenuePerUser: 0,
                churnedSubscriptionCount: 0,
                isLoadingFinancials: false,
                financialErrorMsg: null
            },
            businessIntelligence: {
                loading: false,
                error: null,
                lastUpdated: null
            },
            purchaseOrders: {
                count: 0,
                total: 0,
                pending: 0,
                approved: 0
            },
            internalTransfers: {
                count: 0,
                items: 0,
                inProgress: 0,
                done: 0
            },
            opportunities: {
                count: 0,
                pipelineValue: 0,
                won: 0,
                lost: 0
            },
            stockAlerts: {
                count: 0,
                outOfStock: 0,
                lowStock: 0
            },
            tickets: {
                openCount: 0,
                resolvedCount: 0,
                urgentCount: 0,
                pendingCount: 0
            },

        })

        this.orm = useService('orm');
        this.actionService = useService("action");
        this.menuService = useService("menu");
        this.dialogService = useService("dialog");


        onMounted(async() => {
        this.uiService.block();
        try{

            await this.loadDashboardData();

        }
        finally{
            this.uiService.unblock();
        }
        await this.showRefreshDialog();
        })


    }

    async loadDashboardData() {
       const [stats,balanceData] = await Promise.all([
            rpc("/api/user-stats"),
            rpc("/api/current-balance"),
            this.fetchDiskUsage(),
            this.fetchCompanyName(),
            // this.getMonthlyRevenue(),
            this.getPackageSubscriptions(),
            this.getTopFranchises(),
            // this.getYearlyRevenue(),
            // this.getRegionDistribution()
        ])

        this.state.onlineUsers = stats.online
        this.state.offlineUsers = stats.offline
        this.state.activeUsers = stats.active
        this.state.inactiveUsers = stats.inactive
        this.state.disabledUsers = stats.disabled
        this.state.totalUsers = stats.total
        this.state.current_balance = balanceData.current_balance
    }

    async fetchFinancialData() {
        this.state.financialMetrics.isLoadingFinancials = true;
        try {
            const response = await rpc('/api/financial-metrics');

            if (response.status === 'success') {
                const data = response.data;
                this.state.financialMetrics = {
                    monthlyRecurringRevenue: data.mrr,
                    totalCurrentRevenue: data.total_revenue,
                    unpaidInvoiceData: data.unpaid_invoices,
                    paidCurrentRevenue: data.paid_invoices,
                    overdueInvoiceData: data.overdue_invoices,
                    activeSubscriptionCount: data.active_subscriptions,
                    outstandingCustomerCount: data.outstanding_customers,
                    averageRevenuePerUser: data.arpu,
                    churnedSubscriptionCount: data.churned_subscriptions,
                    isLoadingFinancials: false,
                    financialErrorMsg: null
                };
            } else {
                this.state.financialMetrics.financialErrorMsg = response.message || 'Failed to load financial data';
                this.state.financialMetrics.isLoadingFinancials = false;
            }
        } catch (error) {
            console.error('Financial data fetch failed:', error);
            this.state.financialMetrics.financialErrorMsg = 'Unable to load financial metrics';
            this.state.financialMetrics.isLoadingFinancials = false;
        }
    }



    async handleUsers() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "All Users",
            res_model: "users",
            views: [
                [false, "list"],
                [false, "form"],

              ],
        })
    }
    async handleHome() {
         try {
        const result = await rpc("/api/admin-home");
        await this.actionService.doAction(result);
    } catch (error) {
        // The backend will handle the error notification
        console.log('Action failed:', error);
    }}



    async showRefreshDialog() {
        const dialogMessage = await rpc("/api/refresh-message");

        if (dialogMessage.status === "success") {
            setTimeout(() => {
                this.dialogService.add(NotificationModal, {
                    title: dialogMessage.heading,
                    body: markup(dialogMessage.message),
                    close: () => {
                        this.dialogService.remove();
                    }
                });
            }, 1000);
        }
    }
    log_out_user() {
        const route = "/web/session/logout";
        this.dialogService.add(ConfirmationDialog, {
            title: "Logout Confirmation",
            body: "You will be logged out of the system. Any unsaved changes will be lost.",
            confirmLabel: "Yes, Logout",
            cancelLabel: "Stay Logged In",
            confirm: () => {
                browser.location.href = route;
            },
            cancel: () => {
                console.log("Logout cancelled");
            }
        });

    }

    async fetchCalendarEvents() {
    this.state.calendarEvents.loading = true;
    try {
        const result = await rpc("/api/calendar-events");

        if (result.status === 'success') {
            this.state.calendarEvents.events = result.events;
            this.state.calendarEvents.count = result.count;
            this.state.calendarEvents.date = result.date;
            this.state.calendarEvents.error = null;
        } else {
            this.state.calendarEvents.error = result.message;
        }
    } catch (error) {
        this.state.calendarEvents.error = 'Failed to load calendar events';
        console.error('Calendar events error:', error);
    } finally {
        this.state.calendarEvents.loading = false;
    }
}


async fetchCompanyName() {
    try {
        // Fetch the current user's company
        const companies = await this.orm.searchRead(
            'res.company',
            [['id', '=', this.env.services.company.currentCompany.id]], // Get current company
            ['name'] // Fields to retrieve
        );

        if (companies && companies.length > 0) {
            this.state.company_name = companies[0].name;
        } else {
            // Fallback: get the first company if current company not found
            const fallbackCompanies = await this.orm.searchRead(
                'res.company',
                [], // No domain - get all companies
                ['name'],
                { limit: 1 } // Get only the first one
            );

            if (fallbackCompanies && fallbackCompanies.length > 0) {
                this.state.company_name = fallbackCompanies[0].name;
            } else {
                this.state.company_name = "Company Name Not Found";
            }
        }
    } catch (error) {
        console.error("Failed to fetch company name:", error);
        this.state.company_name = "Error Loading Company";
    }
}

    setActiveTab(tab) {
        this.state.activeTab = tab;
            if (tab === 'calendar') {
                this.fetchCalendarEvents();
            }
            else if (tab === 'financal') {
                this.fetchFinancialData();
            }
            else if (tab === 'biboard') {
                this.loadBusinessIntelligenceData();
            }
    }
    // Fetch disk usage from the Odoo controller API
    async fetchDiskUsage() {
        try {
            const response = await rpc('/api/disk-usage');

            if (!response) {
                console.log("No disk usage data received");
                return;
            }
            this.state.serverUtilization.diskUsage = {
                labels: ["Used", "Free"],
                datasets: [{
                    label: 'Usage of disk',
                    data: [
                        Number(response.used_space).toFixed(2),
                        Number(response.free_space).toFixed(2)
                    ],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(75, 192, 192, 0.5)',

                    ],
                    hoverOffset: 4
                }]
            };
            this.state.serverUtilization.message = response.message;


            } catch (error) {
                console.log("Data fetch failed:", error.message);
            }
        }


    async getPackageSubscriptions() {
        try {
            const response = await rpc('/api/package-subscriptions');
            if (!response) {
                console.log("No subscription data received");
                return;
            }

            this.state.packageSubscriptions.subData = {
                labels: response.labels,
                datasets: [{
                    label:  'Package Distribution',
                    data: response.data,
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.5)',   // Teal
                        'rgba(54, 162, 235, 0.5)',   // Blue
                        'rgba(255, 206, 86, 0.5)',   // Yellow
                        'rgba(153, 102, 255, 0.5)',  // Purple
                        'rgba(255, 99, 132, 0.5)',   // Pink
                        'rgba(255, 159, 64, 0.5)',   // Orange
                        'rgba(46, 204, 113, 0.5)',   // Emerald
                        'rgba(142, 68, 173, 0.5)',   // Amethyst
                        'rgba(52, 152, 219, 0.5)',   // Peter River
                        'rgba(231, 76, 60, 0.5)',    // Pomegranate
                        'rgba(26, 188, 156, 0.5)',   // Turquoise
                        'rgba(155, 89, 182, 0.5)',   // Wisteria
                        'rgba(241, 196, 15, 0.5)',   // Sunflower
                        'rgba(230, 126, 34, 0.5)',   // Carrot
                        'rgba(149, 165, 166, 0.5)'   // Concrete
                    ],
                },],
            };
            this.state.packageSubscriptions.message = response.message;

        }catch (error) {
                console.log("Package subscription data fetch failed:", error.message);
            }
        }

    async getTopFranchises() {
        try {
            const response = await rpc('/api/top-franchises');
            if (!response) {
                console.log("No top franchise data received");
                return;
            }
            this.state.topFranchises.franchiseData = {
                labels: response.labels,
                datasets: [{
                    label: 'Online Users',
                    data: response.data,
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.5)',   // Teal
                        'rgba(54, 162, 235, 0.5)',   // Blue
                        'rgba(255, 206, 86, 0.5)',   // Yellow
                        'rgba(153, 102, 255, 0.5)',  // Purple
                        'rgba(255, 99, 132, 0.5)',   // Pink


                    ],
                    hoverOffset: 4
                }],
            };

            this.state.topFranchises.message = response.message;

        } catch (error) {
            console.log("Top franchises data fetch failed:", error.message);
        }
    }


    // Views Actions

    async viewOnlineUsers() {
        let domain = [['current_status', '=', 'online']]
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Online Users",
            res_model: "users",
            domain,
            views: [
                [false, "list"],
                [false, "form"],

              ],
              context: {'create': false , 'open': true, 'edit': false},
        })
    }
    async viewOfflineUsers() {
        let domain = [['current_status', '=', 'offline'],['is_disable', '!=', 'False'], ['conection_status', '=', 'active']];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Offline Users",
            res_model: "users",
            domain,
            views: [
                [false, "list"],
                [false, "form"],
              ],
              context: {'create': false , 'open': true, 'edit': false},
        })
    }
    async viewDisableUsers() {
        let domain = [['is_disable', '=', 'True']];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Offline Users",
            res_model: "users",
            domain,
            views: [
                [false, "list"],
                [false, "form"],
              ],
              context: {'create': false , 'open': true, 'edit': false},
        })
    }

    async viewActiveUsers() {
        let domain = [['conection_status', '=', 'active']]
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Active Users",
            res_model: "users",
            domain,
            views: [
                [false, "list"],
                [false, "form"],
              ],
              context: {'create': false , 'open': true, 'edit': false},
        })
    }
    async viewInActiveUsers() {
        let domain = [['conection_status', '!=', 'active']]
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Expired Users",
            res_model: "users",
            domain,
            views: [
                [false, "list"],
                [false, "form"],
              ],
              context: {'create': false , 'open': true, 'edit': false},
        })
    }
    async viewTotalUsers() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Total Users",
            res_model: "users",
            views: [
                [false, "list"],
                [false, "form"],
              ],
              context: {'create': false , 'open': true, 'edit': false},
        })
    }

     async loadBusinessIntelligenceData() {
        this.state.businessIntelligence.loading = true;
        this.state.businessIntelligence.error = null;

        try {
            const result = await rpc('/stats/business_intelligence_data', {});

            if (result.success) {
                const data = result.data;

                this.state.purchaseOrders = data.purchaseOrders;
                this.state.internalTransfers = data.internalTransfers;
                this.state.opportunities = data.opportunities;
                this.state.stockAlerts = data.stockAlerts;
                this.state.tickets = data.tickets;
                this.state.businessIntelligence.lastUpdated = data.lastUpdated;
            } else {
                this.state.businessIntelligence.error = result.error;
                this.notification.add('Failed to load business intelligence data', {
                    type: 'danger',
                });
            }
        } catch (error) {
            console.error('Error loading business intelligence data:', error);
            this.state.businessIntelligence.error = error.message;
            this.notification.add('Error loading business intelligence data', {
                type: 'danger',
            });
        } finally {
            this.state.businessIntelligence.loading = false;
        }
    }

    // Navigation methods
    async viewPurchaseOrders() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const formattedDate = firstDay.toISOString().split('T')[0];

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Purchase Orders (This Month)',
            res_model: 'purchase.order',
            views: [[false, 'list'], [false, 'form']],
            domain: [['date_order', '>=', formattedDate]],
            context: {},
        });
    }

    async viewInternalTransfers() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const formattedDate = firstDay.toISOString().split('T')[0];

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Internal Transfers (This Month)',
            res_model: 'stock.picking',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['picking_type_code', '=', 'internal'],
                ['create_date', '>=', formattedDate]
            ],
            context: {},
        });
    }

    async viewOpportunities() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Sales Opportunities',
            res_model: 'crm.lead',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [['type', '=', 'opportunity'], ['active', '=', true]],
            context: {},
        });
    }

    async viewStockAlerts() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Stock Alerts - Low Inventory',
            res_model: 'product.product',
            views: [[false, 'list'], [false, 'form']],
            domain: [['type', '=', 'product']],
            context: {},
        });
    }

    async viewTickets() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Support Tickets',
            res_model: 'helpdesk.ticket',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [['stage_id.closed', '=', false]],
            context: {},
        });
    }



}
UserStats.template = "stats.UserStats";
UserStats.components = { ChartRenderer, Refresher, NotificationModal};

registry.category("actions").add("stats.user_stats", UserStats);

