# -*- coding: utf-8 -*-
# from odoo import http


# class Users(http.Controller):
#     @http.route('/users/users', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/users/users/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('users.listing', {
#             'root': '/users/users',
#             'objects': http.request.env['users.users'].search([]),
#         })

#     @http.route('/users/users/objects/<model("users.users"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('users.object', {
#             'object': obj
#         })

