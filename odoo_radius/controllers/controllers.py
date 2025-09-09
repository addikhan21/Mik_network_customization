# -*- coding: utf-8 -*-
# from odoo import http


# class OdooRadius(http.Controller):
#     @http.route('/odoo_radius/odoo_radius', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo_radius/odoo_radius/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo_radius.listing', {
#             'root': '/odoo_radius/odoo_radius',
#             'objects': http.request.env['odoo_radius.odoo_radius'].search([]),
#         })

#     @http.route('/odoo_radius/odoo_radius/objects/<model("odoo_radius.odoo_radius"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo_radius.object', {
#             'object': obj
#         })

