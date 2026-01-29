import os
import sqlite3
from flask import Flask, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TARGET_DIR = os.getenv("TARGET_DIR", "./data")
DB_PATH = os.path.join(TARGET_DIR, "factory.db")

def get_data():
    if not os.path.exists(DB_PATH):
        return 0, 0, 0, 0, []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM assembly_logs")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assembly_logs WHERE status = 'FAIL'")
        fail = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, torque_val FROM assembly_logs ORDER BY id DESC LIMIT 10")
        recent_data = cursor.fetchall()
        recent_data.reverse()
        
        conn.close()
        
        pass_units = total - fail
        rate = round((fail / total * 100), 2) if total > 0 else 0
        return total, pass_units, fail, rate, recent_data
    except Exception as e:
        print(f"Database Error: {e}")
        return 0, 0, 0, 0, []

@app.route('/')
def dashboard():
    total, pass_units, fail, rate, recent_data = get_data()
    chart_data = [["ID", "Torque"]] + [[str(d[0]), d[1]] for d in recent_data]

    html = '''
    <html>
        <head>
            <title>Production Monitor</title>
            <meta http-equiv="refresh" content="5">
            <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
            <script type="text/javascript">
                google.charts.load('current', {'packages':['corechart']});
                google.charts.setOnLoadCallback(drawChart);
                function drawChart() {
                    var data = google.visualization.arrayToDataTable(''' + str(chart_data) + ''');
                    var options = {
                        title: 'Torque Trend (Last 10 units)',
                        curveType: 'function',
                        legend: { position: 'bottom' },
                        vAxis: { minValue: 40, maxValue: 50 },
                        hAxis: { title: 'Log ID' },
                        colors: ['#2e7d32']
                    };
                    var chart = new google.visualization.LineChart(document.getElementById('curve_chart'));
                    chart.draw(data, options);
                }
            </script>
            <style>
                body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 40px; text-align: center; }
                .container { max-width: 900px; margin: auto; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
                .stat-container { display: flex; justify-content: space-between; margin-bottom: 30px; }
                .stat-box { flex: 1; margin: 0 10px; padding: 20px; border-radius: 15px; background: #fafafa; border: 1px solid #eee; }
                .label { font-size: 14px; color: #666; text-transform: uppercase; }
                .value { font-size: 28px; font-weight: bold; margin-top: 10px; }
                .fail { color: #d32f2f; }
                .pass { color: #388e3c; }
                #curve_chart { width: 100%; height: 350px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: #1a237e; margin-bottom: 30px;">Engine Assembly Line Monitor</h1>
                <div class="stat-container">
                    <div class="stat-box"><div class="label">Total Produced</div><div class="value">''' + str(total) + '''</div></div>
                    <div class="stat-box"><div class="label pass">Pass</div><div class="value pass">''' + str(pass_units) + '''</div></div>
                    <div class="stat-box"><div class="label fail">Fail</div><div class="value fail">''' + str(fail) + '''</div></div>
                </div>
                <div id="curve_chart"></div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <span style="font-size: 20px;">Defect Rate: <b class="fail">''' + str(rate) + '''%</b></span>
                </div>
                <p style="color: #999; font-size: 12px; margin-top: 20px;">System Status: Active | Refreshing every 5s</p>
            </div>
        </body>
    </html>
    '''
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)