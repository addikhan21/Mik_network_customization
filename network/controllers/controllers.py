# -*- coding: utf-8 -*-
# from odoo import http


# class Network(http.Controller):
#     @http.route('/network/network', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/network/network/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('network.listing', {
#             'root': '/network/network',
#             'objects': http.request.env['network.network'].search([]),
#         })

#     @http.route('/network/network/objects/<model("network.network"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('network.object', {
#             'object': obj
#         })

