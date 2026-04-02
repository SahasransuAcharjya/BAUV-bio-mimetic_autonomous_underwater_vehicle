import dash
from dash import dcc, html, Input, Output, callback, State
import plotly.graph_objs as go
import serial
import queue
import threading
import time
import numpy as np
import pandas as pd
import json
import os
import csv

# Load configuration
try:
    with open('config/config.json', 'r') as f:
        CONFIG = json.load(f)
except:
    CONFIG = {
        "serial": {"port": "COM7", "baudrate": 9600, "timeout": 1.0},
        "dashboard": {"host": "127.0.0.1", "port": 8050, "debug": True}
    }

# Global state
ser = None
connected = False
status_message = "🔄 Connecting to Arduino..."
positions = {'x': [], 'y': []}
log_messages = []
session_start_time = None

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def log_position(rel_time, pos):
    filepath = os.path.join(DATA_DIR, "servo_positions.csv")
    try:
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            if os.path.getsize(filepath) == 0:
                writer.writerow(['rel_time_s', 'position_deg'])
            writer.writerow([rel_time, pos])
    except:
        pass

def connect_serial():
    global ser, connected, status_message
    try:
        ser = serial.Serial(
            CONFIG['serial']['port'],
            CONFIG['serial']['baudrate'],
            timeout=CONFIG['serial']['timeout']
        )
        time.sleep(2)
        connected = True
        status_message = f"✅ Connected to {CONFIG['serial']['port']}"
        return True
    except Exception as e:
        connected = False
        status_message = "❌ Arduino not ready"
        return False

def serial_reader():
    global ser, connected, status_message, positions, session_start_time
    while True:
        try:
            if not connected or not ser or not ser.is_open:
                if connect_serial(): pass
                time.sleep(3)
                continue
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('pos:'):
                    try:
                        pos_val = float(line.split(':')[1])
                        if session_start_time is None:
                            session_start_time = time.time()
                        rel_time = time.time() - session_start_time
                        positions['x'].append(rel_time)
                        positions['y'].append(pos_val)
                        log_position(rel_time, pos_val)
                        if len(positions['x']) > 300:
                            positions['x'] = positions['x'][-300:]
                            positions['y'] = positions['y'][-300:]
                    except: pass
            else:
                time.sleep(0.02)
        except:
            connected = False
            time.sleep(1)

threading.Thread(target=serial_reader, daemon=True).start()

app = dash.Dash(__name__, external_stylesheets=['/static/style.css'])
app.title = "BAUV Servo Dashboard"

app.layout = html.Div(className="container", children=[
    html.H1("🐟 BAUV Tail Flapping Dashboard", style={'textAlign': 'center', 'color': '#00d4ff'}),
    html.Div(id='status', style={'textAlign': 'center', 'padding': '15px', 'borderRadius': '10px', 'margin': '20px 0'}),
    dcc.Graph(id='live-plot', style={'height': '500px'}),
    dcc.Interval(id='interval', interval=100, n_intervals=0),
    html.Div([
        html.H3("🎚️ Calibrate Servo", style={'color': '#00d4ff'}),
        html.Div(className="control-panel", children=[
            html.Label("Target Angle (0-180°):"),
            dcc.Slider(id='calib-slider', min=0, max=180, value=90, step=1, marks={i: str(i) for i in range(0, 181, 30)}),
            html.Button('🚀 GO TO ANGLE', id='calib-btn', n_clicks=0, style={'width': '100%', 'marginTop': '15px'})
        ])
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        html.H3("🌊 Tail Flapping", style={'color': '#00d4ff'}),
        html.Div(className="control-panel", children=[
            html.Label("Base Angle:"),
            dcc.Slider(id='base-slider', min=0, max=180, value=90, step=1),
            html.Label("Frequency (Hz):"),
            # UPDATED: Max frequency set to 10.0
            dcc.Slider(id='freq-slider', min=0.1, max=10.0, value=1.0, step=0.1),
            html.Label("Amplitude (°):"),
            dcc.Slider(id='amp-slider', min=10, max=70, value=40, step=5),
            html.Button('🐠 START FLAPPING', id='osc-btn', n_clicks=0, style={'width': '100%', 'marginTop': '15px', 'backgroundColor': '#00d4ff'}),
            html.Button('🛑 STOP FLAPPING', id='stop-btn', n_clicks=0, style={'width': '100%', 'marginTop': '10px', 'backgroundColor': '#ff6b6b'})
        ])
    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    html.Hr(),
    html.Div(id='log', style={'background': 'rgba(0,0,0,0.3)', 'padding': '20px', 'borderRadius': '10px', 'maxHeight': '150px', 'overflowY': 'auto'})
])

@callback([Output('live-plot', 'figure'), Output('status', 'children'), Output('status', 'style')], Input('interval', 'n_intervals'))
def update_plot(n):
    status_style = {'textAlign': 'center', 'fontSize': '18px', 'fontWeight': 'bold', 'padding': '15px', 'borderRadius': '10px', 'margin': '20px 0'}
    if connected: status_style.update({'background': 'rgba(0,255,127,0.3)', 'border': '3px solid #00ff7f'})
    else: status_style.update({'background': 'rgba(255,100,100,0.3)', 'border': '3px solid #ff6464'})
    
    fig = go.Figure()
    if len(positions['x']) > 0:
        fig.add_trace(go.Scatter(x=positions['x'], y=positions['y'], mode='lines', name='Tail Angle', line=dict(color='#00d4ff', width=4)))
        fig.update_layout(title='🦈 Real-time Tail Flapping', xaxis_title='Time (s)', yaxis_title='Angle (°)', yaxis=dict(range=[0, 180]), plot_bgcolor='rgba(10,25,50,0.8)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0e7ff'))
    return fig, status_message, status_style

@callback(Output('log', 'children'), [Input('calib-btn', 'n_clicks'), Input('osc-btn', 'n_clicks'), Input('stop-btn', 'n_clicks')], [State('calib-slider', 'value'), State('base-slider', 'value'), State('freq-slider', 'value'), State('amp-slider', 'value')])
def send_command(c_n, o_n, s_n, c_v, b_v, f_v, a_v):
    global ser, log_messages, positions, session_start_time
    ctx = dash.callback_context
    if not ctx.triggered or not ser or not ser.is_open: return html.Div("❌ Connection Error")
    
    btn = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        if btn in ['calib-btn', 'osc-btn']:
            positions['x'], positions['y'] = [], []
            session_start_time = time.time()
        if btn == 'calib-btn':
            ser.write(b'1\n'); time.sleep(0.1); ser.write(f"{c_v:.1f}\n".encode())
            log_messages.append(f"✅ CALIBRATE → {c_v}°")
        elif btn == 'osc-btn':
            ser.write(b'2\n'); time.sleep(0.1); ser.write(f"{b_v:.1f}\n".encode()); time.sleep(0.1); ser.write(f"{f_v:.2f}\n".encode()); time.sleep(0.1); ser.write(f"{a_v:.1f}\n".encode())
            log_messages.append(f"✅ FLAPPING → {f_v}Hz")
        elif btn == 'stop-btn':
            ser.write(b'3\n')
            log_messages.append("🛑 STOPPED")
    except Exception as e: log_messages.append(f"❌ Error: {str(e)}")
    
    return html.Ul([html.Li(msg) for msg in log_messages[-10:]])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8050, debug=True)