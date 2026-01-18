/** @odoo-module */
import { Component } from "@odoo/owl";

export class NotificationModal extends Component {
    setup() {
        this.close = () => this.props.close();
    }
}

NotificationModal.template = 'stats.NotificationModal';