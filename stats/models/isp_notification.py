# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class IspNotification(models.Model):
    _name = 'isp.notification'
    _description = 'Notification'

    name = fields.Char('Name', required=True)
    heading_eng = fields.Char('Heading English', required=True)
    message_english = fields.Html('Message English', required=True)
    heading_urdu = fields.Char('Heading urdu', required=True)
    message_urdu = fields.Html('Message urdu', required=True)
    publish = fields.Boolean('Publish')
    body = fields.Html('Body', compute='_compute_body', readonly=False, store=True)
    
    @api.depends('publish')
    def _compute_body(self):
        for record in self:
            if record.publish:
                record.body = f"""
                   
                        <div class="col-12">
                            <h3 class="d-flex justify-content-left ">{record.heading_eng}</h3>
                            <div class="text-justify">
                                {record.message_english}
                            </div>
                        </div>
                        
                        <hr/>
                        
                        <div class="col-12" >
                            <h3 class="d-flex justify-content-end">{record.heading_urdu}</h3>
                            <div class="d-flex float-end text-right">
                                {record.message_urdu}
                            </div>
                        </div>
                   
                            """

    
    
   
