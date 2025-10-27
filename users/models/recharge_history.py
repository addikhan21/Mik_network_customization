from odoo import models, fields, api
import datetime as datetime

class RechargeHistory(models.Model):
    _name = 'recharge.history'
    _description = 'Recharge History'
    _order = 'recharge_date desc'
    _rec_name = 'user_id'
   
    user_id = fields.Many2one('users', string='User', index=True, required=True,)
    distributor_id = fields.Many2one(related='user_id.distributor_id', index=True, string='Distributor')
    distributor_type = fields.Selection(related='distributor_id.distributor_type', string='Distributor')
    package_id = fields.Many2one('package.line', string='Package' , index=True)
    amount = fields.Float(string='Recharge Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                 default=lambda self: self.env.company.currency_id)
    remaining_balance = fields.Float(string='Remaining Balance')
    recharged_by = fields.Many2one('res.users',  string='Recharged By', default=lambda self: self.env.user)
    recharge_date = fields.Datetime(string='Recharge Date', default=fields.Datetime.now() , required=True)
