/** @odoo-module */

import { loadJS } from "@web/core/assets";
const { Component, onWillStart, useRef, onMounted, useEffect, onWillUnmount } = owl;
import { useService } from "@web/core/utils/hooks";

export class ChartRenderer extends Component {

    setup() {
        this.chartRef = useRef("chart")
        this.actionService = useService("action")
        

        onWillStart(async () => {
            // await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
            await loadJS("/web/static/lib/Chart/Chart.js")
        })

        useEffect(() => {
            this.renderChart()
            return () => this.chart?.destroy()
        }, () => [this.props.data])

        onMounted(() => {
            this.renderChart()
        })

        onWillUnmount(()=>{
            if (this.chart){
                this.chart.destroy()
            }

        })

    }


    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
    
        this.chart = new Chart(this.chartRef.el, {
            type: this.props.type, 
            data: this.props.data,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    
                    // title: {
                    //     display: true,
                    //     text: 'Server Utilization',
                    //     position: 'top',
                    // }
                }
            }
        });
    }
    
}

ChartRenderer.template = "stats.ChartRenderer";