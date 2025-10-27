import logging
from odoo.exceptions import ValidationError
from odoo import models, api, _
import csv
from io import StringIO

_logger = logging.getLogger(__name__)


class Import(models.TransientModel):
    _inherit = "base_import.import"

    # def parse_preview(self, options, count=10):

    #     if "users" == self.res_model:
    #         file_content = self.file.decode('ascii')
    #         csvfile = StringIO(file_content)
    #         reader = csv.DictReader(csvfile)

    #         for row in reader:
    #             package_name = row.get('Package')
    #             distributor_name = row.get('Distributor')

    #             package = self.env['package.line'].search([
    #                 ('package_name', '=', package_name),
    #                 ('dealer_name', '=', distributor_name),
    #                 ('state', '=', 'active')
    #             ])

    #             if not package:
    #                 message =  f"Package '{package_name}' not found for distributor '{distributor_name}'"
    #                 raise ValidationError(message)
    #     return super(Import, self).parse_preview(options, count)



    def execute_import(self, fields, columns, options, dryrun=False):
        
        _logger.info(f"Columns: {columns}")

        # Possible Validations
        
        if "users" == self.res_model:
            
            required_columns = ['distributor', 'expiry date', 'name', 'username', 'package', 'password']
            columns_lower = [col.lower() for col in columns]
            missing_columns = [col for col in required_columns if col.lower() not in columns_lower]
            
            if missing_columns:
                raise ValidationError(
                    f"Required columns are missing: {', '.join(missing_columns)}. \n"
                    f"Please make sure your CSV file includes all required columns."
                )
            
        if "users" == self.res_model and 'package' in columns:
            
            file_content = self.file.decode('ascii')
            csvfile = StringIO(file_content)
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                
                package_name = row.get('Package')
                distributor_name = row.get('Distributor')
                
                package = self.env['package.line'].search([
                    # ('package_name', '=', package_name),
                    ('dealer_name', '=', distributor_name),
                    ('state', '=', 'active')
                ])
                
                if not package:
                    raise ValidationError(f"Package '{package_name}' not found in distributor '{distributor_name}' package list")
        
        
        # Actual Import Logic
        res_import = super(Import, self).execute_import(
            fields, columns, options, dryrun
        )
        
        # print("Importing", res_import)
        
        # Workaround Fix False Package Assignments
        
        if "users" == self.res_model and not dryrun and res_import:
            imported_ids = res_import.get('ids', [])
            
            if imported_ids:
                self._cr.execute("""
                    UPDATE users u
                    SET package_id = p.id
                    FROM package_line p
                    WHERE p.package_name = u.package_name
                    AND p.dealer_name = u.distributor_name
                    AND p.state = 'active'
                    AND u.id IN %s
                """, (tuple(imported_ids),))
                
                _logger.info(f"Package mapping completed for users: {imported_ids}")
                
                # Override the messages
                res_import['messages'] = [{
                    'type': 'info',
                    'message': f'Successfully imported and mapped packages for {len(imported_ids)} records'
                }]
    
        return res_import
