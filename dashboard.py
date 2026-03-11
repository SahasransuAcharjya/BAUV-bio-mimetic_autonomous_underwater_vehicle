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
data_queue = queue.Queue()
ser = None
connected = False
status_message = "🔄 Connecting to Arduino..."

# Data storage
positions = {'x': [], 'y': []}
log_messages = []

# Time tracking
session_start_time = None  # Resets when a button is pressed

# Ensure data directory exists
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
        print(f"✓ Serial connected: {CONFIG['serial']['port']}")
        return True
    except Exception as e:
        connected = False
        status_message = "❌ Arduino not ready (upload .ino code)"
        print(f"✗ Serial: {str(e)}")
        return False

def serial_reader():
    global ser, connected, status_message, positions, session_start_time
    retry_count = 0
    
    while True:
        try:
            if not connected or not ser or not ser.is_open:
                retry_count += 1
                status_message = f"🔄 Retry {retry_count}... (Close Arduino IDE)"
                if connect_serial():
                    retry_count = 0
                time.sleep(3)
                continue
            
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('pos:'):
                    try:
                        pos_val = float(line.split(':')[1])
                        
                        # Initialize start time on very first data point if not set
                        if session_start_time is None:
                            session_start_time = time.time()
                            
                        # RELATIVE TIME: Always starts from 0s for current session
                        rel_time = time.time() - session_start_time
                        
                        positions['x'].append(rel_time)
                        positions['y'].append(pos_val)
                        log_position(rel_time, pos_val)
                        
                        # Keep last 300 points for smooth scrolling
                        if len(positions['x']) > 300:
                            positions['x'] = positions['x'][-300:]
                            positions['y'] = positions['y'][-300:]
                    except:
                        pass
            else:
                time.sleep(0.02)
                
        except Exception as e:
            connected = False
            if ser:
                try:
                    ser.close()
                except:
                    pass
                ser = None
            time.sleep(1)

# Start serial thread
threading.Thread(target=serial_reader, daemon=True).start()
time.sleep(1)

# Dash app
app = dash.Dash(__name__, external_stylesheets=['/static/style.css'])
app.title = "BAUV Servo Dashboard"

app.layout = html.Div(className="container", children=[
    html.H1("🐟 BAUV Tail Flapping Dashboard", style={'textAlign': 'center', 'color': '#00d4ff'}),
    
    html.Div(id='status', style={
        'textAlign': 'center', 'fontSize': '18px', 'fontWeight': 'bold', 
        'padding': '15px', 'borderRadius': '10px', 'margin': '20px 0'
    }),
    
    dcc.Graph(id='live-plot', style={'height': '500px'}),
    dcc.Interval(id='interval', interval=100, n_intervals=0),
    
    html.Div([
        html.H3("🎚️ Calibrate Servo", style={'color': '#00d4ff'}),
        html.Div(className="control-panel", children=[
            html.Label("Target Angle (0-180°):"),
            dcc.Slider(id='calib-slider', min=0, max=180, value=90, step=1,
                      marks={i: str(i) for i in range(0, 181, 30)}),
            html.Br(),
            html.Button('🚀 GO TO ANGLE', id='calib-btn', n_clicks=0,
                       style={'width': '100%', 'marginTop': '15px', 'fontSize': '16px'})
        ])
    ], style={'width': '48%', 'display': 'inline-block'}),
    
    html.Div([
        html.H3("🌊 Tail Flapping", style={'color': '#00d4ff'}),
        html.Div(className="control-panel", children=[
            html.Label("Base Angle:"),
            dcc.Slider(id='base-slider', min=0, max=180, value=90, step=1),
            html.Label("Frequency (Hz):"),
            dcc.Slider(id='freq-slider', min=0.1, max=5.0, value=1.0, step=0.1),
            html.Label("Amplitude (°):"),
            dcc.Slider(id='amp-slider', min=10, max=70, value=40, step=5),
            html.Br(),
            html.Button('🐠 START FLAPPING', id='osc-btn', n_clicks=0,
                       style={'width': '100%', 'marginTop': '15px', 'fontSize': '16px'})
        ])
    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    
    html.Hr(),
    html.H3("📋 Activity Log", style={'color': '#ff6b6b'}),
    html.Div(id='log', style={
        'background': 'rgba(0,0,0,0.3)', 'padding': '20px', 
        'borderRadius': '10px', 'maxHeight': '150px', 'overflowY': 'auto'
    })
])

@callback(
    [Output('live-plot', 'figure'),
     Output('status', 'children'),
     Output('status', 'style')],
    Input('interval', 'n_intervals'),
    prevent_initial_call=True
)
def update_plot(n):
    global status_message, connected
    
    status_style = {
        'textAlign': 'center', 'fontSize': '18px', 'fontWeight': 'bold', 
        'padding': '15px', 'borderRadius': '10px', 'margin': '20px 0'
    }
    if connected:
        status_style.update({'background': 'rgba(0,255,127,0.3)', 'border': '3px solid #00ff7f'})
        status_style.update({'boxShadow': '0 0 20px rgba(0,255,127,0.5)'})
    else:
        status_style.update({'background': 'rgba(255,100,100,0.3)', 'border': '3px solid #ff6464'})
    
    fig = go.Figure()
    if len(positions['x']) > 0:
        df = pd.DataFrame({'time': positions['x'], 'pos': positions['y']})
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['pos'], mode='lines', 
            name='Tail Angle', line=dict(color='#00d4ff', width=4),
            hovertemplate='Time: %{x:.1f}s<br>Angle: %{y:.1f}°<extra></extra>'
        ))
        
        # Add smooth trend line to indicate base angle
        if len(df) > 10:
            z = np.polyfit(df['time'], df['pos'], 1)
            trend = np.polyval(z, df['time'])
            fig.add_trace(go.Scatter(
                x=df['time'], y=trend, mode='lines', 
                name='Base Trend', line=dict(color='#ff6b6b', width=2, dash='dot'),
                showlegend=False
            ))
        
        # Let Plotly auto-scale the X axis based on data (fills screen naturally)
        fig.update_layout(
            title='🦈 Real-time Tail Flapping (ES9257 Servo)',
            xaxis_title='Time since start (s)',
            yaxis_title='Servo Angle (°)',
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', autorange=True),  # <-- This fixes the half-screen!
            yaxis=dict(range=[0, 180], gridcolor='rgba(255,255,255,0.2)'),
            plot_bgcolor='rgba(10,25,50,0.8)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e7ff', size=12),
            height=500,
            showlegend=True,
            hovermode='x unified',
            margin=dict(l=50, r=20, t=50, b=50)
        )
    else:
        fig.update_layout(
            title='📡 Waiting for servo feedback... (Press START FLAPPING)',
            xaxis_title='Time since start (s)',
            yaxis_title='Servo Angle (°)',
            yaxis=dict(range=[0, 180]),
            height=500, plot_bgcolor='rgba(10,25,50,0.8)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e7ff')
        )
    
    return fig, status_message, status_style

@callback(
    Output('log', 'children'),
    [Input('calib-btn', 'n_clicks'), Input('osc-btn', 'n_clicks')],
    [State('calib-slider', 'value'),
     State('base-slider', 'value'),
     State('freq-slider', 'value'),
     State('amp-slider', 'value')],
    prevent_initial_call=True
)
def send_command(calib_n, osc_n, calib_val, base_val, freq_val, amp_val):
    global ser, log_messages, positions, session_start_time
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return html.Div()
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    log_entry = []
    
    if not ser or not ser.is_open:
        log_entry.append("❌ Connect Arduino first")
    else:
        try:
            # RESET GRAPH AND TIME TO 0 ON EVERY BUTTON PRESS!
            positions['x'] = []
            positions['y'] = []
            session_start_time = time.time()
            
            if button_id == 'calib-btn':
                ser.write(b'1\n')
                time.sleep(0.2)
                ser.write(f"{calib_val:.1f}\n".encode())
                log_entry.append(f"✅ CALIBRATE → {calib_val}°")
            elif button_id == 'osc-btn':
                ser.write(b'2\n')
                time.sleep(0.2)
                ser.write(f"{base_val:.1f}\n".encode())
                time.sleep(0.2)
                ser.write(f"{freq_val:.2f}\n".encode())
                time.sleep(0.2)
                ser.write(f"{amp_val:.1f}\n".encode())
                log_entry.append(f"✅ FLAPPING → base:{base_val}° f:{freq_val}Hz a:{amp_val}°")
        except Exception as e:
            log_entry.append(f"❌ Error: {str(e)[:40]}")
    
    log_messages.extend(log_entry)
    if len(log_messages) > 12:
        log_messages = log_messages[-12:]
    
    return html.Div([
        html.Ul([html.Li(msg, style={'margin': '6px 0', 'padding': '5px'}) 
                for msg in log_messages])
    ])

if __name__ == '__main__':
    print("🚀 BAUV Tail Dashboard")
    print("🌐 http://127.0.0.1:8050")
    print("✨ Graph fills screen and resets to 0.0s")
    
    app.run(host='127.0.0.1', port=8050, debug=True)
