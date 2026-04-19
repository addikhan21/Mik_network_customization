import json
import logging
import requests
from urllib.parse import quote
from odoo import models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class GenieACSPendingTasksWizard(models.TransientModel):
    _name = "genieacs.pending.tasks.wizard"
    _description = "GenieACS Pending Tasks Viewer"

    tasks_html = fields.Html(string="Pending Tasks", readonly=True, sanitize=False)

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'tasks_html' in fields_list:
            res['tasks_html'] = self._fetch_pending_tasks()
        return res

    def _get_genieacs_credentials(self):
        ICP = self.env["ir.config_parameter"].sudo()
        url = ICP.get_param("genieacs.url")
        user = ICP.get_param("genieacs.username")
        pwd = ICP.get_param("genieacs.password")
        if not url:
            raise ValidationError(_("GenieACS URL is not configured."))
        return url.rstrip("/"), user, pwd

    def _fetch_pending_tasks(self):
        url, user, pwd = self._get_genieacs_credentials()
        auth = (user, pwd) if user else None
        
        # Get device_id from context if available
        device_id = self.env.context.get('default_device_id')
        
        if device_id:
            query = json.dumps({"device": device_id})
        else:
            query = json.dumps({})
        
        api_url = f"{url}/tasks?query={quote(query, safe='')}"
        
        try:
            _logger.info("GenieACS Fetch Pending Tasks → GET %s", api_url)
            response = requests.get(api_url, auth=auth, timeout=15)
            response.raise_for_status()
            tasks = response.json() or []
            
            return self._build_tasks_html(tasks, device_id)
            
        except requests.exceptions.ConnectionError:
            return self._error_html("Cannot connect to GenieACS. Check if the service is running.")
        except requests.exceptions.Timeout:
            return self._error_html("GenieACS request timed out.")
        except Exception as e:
            _logger.exception("Error fetching pending tasks")
            return self._error_html(f"Error: {str(e)}")

    def _build_tasks_html(self, tasks, device_id=None):
        if not tasks:
            return f"""
            <div style="font-family: inherit; padding: 20px;">
                <div class="alert alert-success" role="alert">
                    <i class="fa fa-check-circle me-2"></i>
                    <strong>No pending tasks</strong>
                    {f' for device {device_id}' if device_id else ''}.
                </div>
            </div>
            """
        
        rows = []
        for idx, task in enumerate(tasks, 1):
            task_name = task.get('name', 'Unknown')
            device = task.get('device', 'N/A')
            timestamp = task.get('timestamp', 'N/A')
            task_id = task.get('_id', 'N/A')
            
            # Task type badge color
            badge_color = {
                'reboot': 'warning',
                'factoryReset': 'danger',
                'setParameterValues': 'info',
                'getParameterValues': 'primary',
                'refreshObject': 'secondary'
            }.get(task_name, 'secondary')
            
            rows.append(f"""
                <tr>
                    <td style="padding: 10px; text-align: center; font-size: 13px;">{idx}</td>
                    <td style="padding: 10px; font-family: monospace; font-size: 12px;">{task_id}</td>
                    <td style="padding: 10px;">
                        <span class="badge bg-{badge_color}">{task_name}</span>
                    </td>
                    <td style="padding: 10px; font-family: monospace; font-size: 12px;">{device}</td>
                    <td style="padding: 10px; font-size: 12px;">{timestamp}</td>
                </tr>
            """)
        
        table_rows = "\n".join(rows)
        
        return f"""
        <div style="font-family: inherit;">
            <div class="alert alert-info d-flex justify-content-between align-items-center" role="alert">
                <div>
                    <i class="fa fa-tasks me-2"></i>
                    <strong>{len(tasks)} pending task(s)</strong> {f'for device {device_id}' if device_id else 'in queue'}
                </div>
            </div>
            
            <table class="table table-striped table-hover" style="margin-bottom: 0; border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color: #17a2b8; color: #fff;">
                        <th style="padding: 10px; font-size: 13px; text-align: center; width: 5%;">#</th>
                        <th style="padding: 10px; font-size: 13px;">Task ID</th>
                        <th style="padding: 10px; font-size: 13px;">Task Type</th>
                        <th style="padding: 10px; font-size: 13px;">Device ID</th>
                        <th style="padding: 10px; font-size: 13px;">Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """

    def _error_html(self, message):
        return f"""
        <div style="font-family: inherit; padding: 20px;">
            <div class="alert alert-danger" role="alert">
                <i class="fa fa-exclamation-triangle me-2"></i>
                <strong>Error:</strong> {message}
            </div>
        </div>
        """

    def action_refresh(self):
        self.tasks_html = self._fetch_pending_tasks()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
