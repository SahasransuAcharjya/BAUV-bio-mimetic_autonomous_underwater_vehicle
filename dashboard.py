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
from datetime import datetime

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
status_message = "Connecting to Controller..."
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
        status_message = f"System Online: {CONFIG['serial']['port']}"
        return True
    except Exception as e:
        connected = False
        status_message = "Controller Offline - Check Connection"
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
app.title = "BAUV Telemetry"

app.layout = html.Div(className="container", children=[
    html.H1("BAUV Telemetry Dashboard", style={'textAlign': 'center'}),
    
    html.Div(id='status', style={'textAlign': 'center', 'padding': '12px', 'borderRadius': '8px', 'margin': '0 0 20px 0', 'fontWeight': '600'}),
    
    dcc.Graph(id='live-plot', style={'height': '450px', 'marginBottom': '30px'}),
    dcc.Interval(id='interval', interval=100, n_intervals=0),
    
    html.Div([
        html.H3("Actuator Calibration"),
        html.Div(className="control-panel", children=[
            html.Label("Target Angle (0-180°)"),
            dcc.Slider(id='calib-slider', min=0, max=180, value=90, step=1, marks={i: str(i) for i in range(0, 181, 30)}),
            html.Button('Set Angle', id='calib-btn', n_clicks=0, className='btn-primary')
        ])
    ], style={'width': '48%', 'display': 'inline-block'}),
    
    html.Div([
        html.H3("Kinematic Control"),
        html.Div(className="control-panel", children=[
            html.Label("Base Offset Angle (°)"),
            dcc.Slider(id='base-slider', min=0, max=180, value=90, step=1),
            html.Label("Oscillation Frequency (Hz)"),
            dcc.Slider(id='freq-slider', min=0.1, max=10.0, value=1.0, step=0.1),
            html.Label("Sweep Amplitude (°)"),
            dcc.Slider(id='amp-slider', min=10, max=70, value=40, step=5),
            html.Button('Initiate Oscillation', id='osc-btn', n_clicks=0, className='btn-success'),
            html.Button('Halt Actuator', id='stop-btn', n_clicks=0, className='btn-danger', style={'marginTop': '10px'})
        ])
    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'float': 'right'}),
    
    html.Div(style={'clear': 'both', 'paddingTop': '30px'}),
    
    html.H3("System Output Log"),
    html.Div(id='log', style={'background': '#020617', 'padding': '15px', 'borderRadius': '8px', 'maxHeight': '150px', 'overflowY': 'auto', 'border': '1px solid #1e293b'})
])

@callback([Output('live-plot', 'figure'), Output('status', 'children'), Output('status', 'style')], Input('interval', 'n_intervals'))
def update_plot(n):
    status_style = {'textAlign': 'center', 'fontSize': '15px', 'fontWeight': '600', 'padding': '12px', 'borderRadius': '6px'}
    if connected: 
        status_style.update({'background': 'rgba(16, 185, 129, 0.1)', 'color': '#10b981', 'border': '1px solid rgba(16, 185, 129, 0.3)'})
    else: 
        status_style.update({'background': 'rgba(239, 68, 68, 0.1)', 'color': '#ef4444', 'border': '1px solid rgba(239, 68, 68, 0.3)'})
    
    fig = go.Figure()
    if len(positions['x']) > 0:
        fig.add_trace(go.Scatter(x=positions['x'], y=positions['y'], mode='lines', name='Tail Angle', line=dict(color='#38bdf8', width=3)))
        
        # High-contrast bright text layout
        fig.update_layout(
            title=dict(text='Real-time Actuator Telemetry', font=dict(size=16, color='#f8fafc')),
            xaxis_title='Time (s)', 
            yaxis_title='Angle (°)', 
            yaxis=dict(range=[0, 180], gridcolor='#334155'),
            xaxis=dict(gridcolor='#334155', autorange=True),
            plot_bgcolor='#0f172a', 
            paper_bgcolor='#0f172a', 
            font=dict(color='#f8fafc', size=13), # Updated for high contrast
            margin=dict(l=40, r=20, t=50, b=40),
            hovermode='x unified'
        )
    else:
        fig.update_layout(
            title=dict(text='Awaiting Telemetry Data...', font=dict(size=16, color='#f8fafc')),
            yaxis=dict(range=[0, 180], gridcolor='#334155'),
            xaxis=dict(gridcolor='#334155'),
            plot_bgcolor='#0f172a', paper_bgcolor='#0f172a', font=dict(color='#f8fafc', size=13)
        )
    return fig, status_message, status_style

@callback(Output('log', 'children'), [Input('calib-btn', 'n_clicks'), Input('osc-btn', 'n_clicks'), Input('stop-btn', 'n_clicks')], [State('calib-slider', 'value'), State('base-slider', 'value'), State('freq-slider', 'value'), State('amp-slider', 'value')])
def send_command(c_n, o_n, s_n, c_v, b_v, f_v, a_v):
    global ser, log_messages, positions, session_start_time
    ctx = dash.callback_context
    if not ctx.triggered or not ser or not ser.is_open: return html.Div("SYS_ERR: Hardware disconnected.")
    
    btn = ctx.triggered[0]['prop_id'].split('.')[0]
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        if btn in ['calib-btn', 'osc-btn']:
            positions['x'], positions['y'] = [], []
            session_start_time = time.time()
            
        if btn == 'calib-btn':
            ser.write(b'1\n'); time.sleep(0.1); ser.write(f"{c_v:.1f}\n".encode())
            log_messages.append(f"[{timestamp}] CALIBRATION_SET -> Angle: {c_v}°")
        elif btn == 'osc-btn':
            ser.write(b'2\n'); time.sleep(0.1); ser.write(f"{b_v:.1f}\n".encode()); time.sleep(0.1); ser.write(f"{f_v:.2f}\n".encode()); time.sleep(0.1); ser.write(f"{a_v:.1f}\n".encode())
            log_messages.append(f"[{timestamp}] OSCILLATION_INIT -> Base: {b_v}°, Freq: {f_v}Hz, Amp: {a_v}°")
        elif btn == 'stop-btn':
            ser.write(b'3\n')
            log_messages.append(f"[{timestamp}] HALT_COMMAND_ISSUED")
    except Exception as e: log_messages.append(f"[{timestamp}] ERROR: {str(e)}")
    
    return html.Ul([html.Li(msg, style={'margin': '4px 0', 'listStyleType': 'none'}) for msg in log_messages[-10:]], style={'padding': 0, 'margin': 0})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8050, debug=True)