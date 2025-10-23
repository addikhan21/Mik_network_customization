from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Distributors(models.Model):
    _name = 'distributors'


    name=fields.Char(string='Name', required=True)
    user_count = fields.Integer(string='Users', compute='_compute_user_count')
    total_users = fields.Integer(compute='_compute_total_users')
    online_users = fields.Integer(compute='_compute_total_online_users')
    distributor_type = fields.Selection([('master_dealer', 'Master Dealer'), ('dealer', 'Dealer'), ('sub_dealer', 'Sub Dealer')], string='Distributor Type', required=True)
    
    
    def action_view_admin_secret(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Admin',
            'view_mode': 'list,form',
            'res_model': 'admins',
            'domain': [('distributor_id', '=', self.id)],
        }
              
                
    # @api.depends('user_count')
    # def _compute_total_online_users(self):
    #     for distributor in self:
    #         if distributor.distributor_type == 'master_dealer':
    #             distributors_list = self.env['distributors'].search([('master_dealer_id', '=', distributor.id)]).ids
    #             distributors_list.append(distributor.id)
    #             distributor.online_users = self.env['users'].search_count([('distributor_id', 'in', distributors_list), ('current_status', '=', 'online')])
    #
    #         elif distributor.distributor_type == 'dealer':
    #             distributors_list = self.env['distributors'].search([('dealer_id', '=', distributor.id)]).ids
    #             distributors_list.append(distributor.id)
    #             distributor.online_users = self.env['users'].search_count([('distributor_id', 'in', distributors_list), ('current_status', '=', 'online')])
    #
    #         else:
    #             if distributor.distributor_type == 'sub_dealer':
    #                 distributor.online_users = self.env['users'].search_count([('distributor_id', '=', distributor.id), ('current_status', '=', 'online')])
    
    
    
    
    
    # def _compute_total_users(self):
    #     for distributor in self:
    #
    #         if distributor.distributor_type == 'master_dealer':
    #             distributors_list = self.env['distributors'].search([('master_dealer_id', '=', distributor.id)]).ids
    #             distributors_list.append(distributor.id)
    #             distributor.total_users = self.env['users'].search_count([('distributor_id', 'in', distributors_list)])
    #
    #         elif distributor.distributor_type == 'dealer':
    #             distributors_list = self.env['distributors'].search([('dealer_id', '=', distributor.id)]).ids
    #             distributors_list.append(distributor.id)
    #             distributor.total_users = self.env['users'].search_count([('distributor_id', 'in', distributors_list)])
    #
    #         else:
    #             if distributor.distributor_type == 'sub_dealer':
    #                 distributor.total_users = self.env['users'].search_count([('distributor_id', '=', distributor.id)])
        
    def _compute_user_count(self):
        for distributor in self:
            distributor.user_count = self.env['users'].search_count([('distributor_id', '=', distributor.id)])
    
    def action_view_users(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Users',
            'view_mode': 'list,form',
            'res_model': 'users',
            'domain': [('distributor_id', '=', self.id)],
            # 'context': {'default_distributor_id': self.id},
        }