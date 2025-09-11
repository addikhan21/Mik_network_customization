# -*- coding: utf-8 -*-
# from odoo import http


# class ServicePlans(http.Controller):
#     @http.route('/service_plans/service_plans', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/service_plans/service_plans/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('service_plans.listing', {
#             'root': '/service_plans/service_plans',
#             'objects': http.request.env['service_plans.service_plans'].search([]),
#         })

#     @http.route('/service_plans/service_plans/objects/<model("service_plans.service_plans"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('service_plans.object', {
#             'object': obj
#         })

