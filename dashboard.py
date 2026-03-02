import dash
from dash import dcc, html, Input, Output, callback, State
import plotly.graph_objs as go
import serial
import threading
import queue
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
positions = {'x': [], 'y': []}
log_messages = []

# Ensure data directory exists
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def log_position(timestamp, pos):
    filepath = os.path.join(DATA_DIR, "servo_positions.csv")
    try:
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            if os.path.getsize(filepath) == 0:
                writer.writerow(['timestamp', 'position_deg'])
            writer.writerow([timestamp, pos])
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
        time.sleep(2)  # Arduino reset delay
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
    global ser, connected, status_message
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
                        positions['x'].append(time.time())
                        positions['y'].append(pos_val)
                        log_position(time.time(), pos_val)
                        
                        # Keep last 300 points
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
    html.H1("🐟 BAUV Servo Dashboard", style={'textAlign': 'center', 'color': '#00d4ff'}),
    
    html.Div(id='status', style={
        'textAlign': 'center', 'fontSize': '18px', 'fontWeight': 'bold', 
        'padding': '15px', 'borderRadius': '10px', 'margin': '20px 0'
    }),
    
    dcc.Graph(id='live-plot', style={'height': '450px'}),
    dcc.Interval(id='interval', interval=100, n_intervals=0),
    
    html.Div([
        html.H3("🎚️ Calibrate Mode (Send: 1)", 
                style={'color': '#00d4ff', 'margin': '30px 0 15px 0'}),
        html.Div(className="control-panel", children=[
            html.Label("Servo Angle (0-180°):"),
            dcc.Slider(
                id='calib-slider', min=0, max=180, value=90, step=1,
                marks={i: str(i) for i in range(0, 181, 30)}
            ),
            html.Br(),
            html.Button('🚀 CALIBRATE SERVO', id='calib-btn', n_clicks=0,
                       style={'width': '100%', 'marginTop': '15px'})
        ])
    ]),
    
    html.Div([
        html.H3("🌊 Oscillate Mode (Send: 2)", 
                style={'color': '#00d4ff', 'margin': '30px 0 15px 0'}),
        html.Div(className="control-panel", children=[
            html.Label("Base Angle:"),
            dcc.Slider(id='base-slider', min=0, max=180, value=90, step=1),
            html.Label("Frequency (Hz):"),
            dcc.Slider(id='freq-slider', min=0.1, max=5.0, value=1.0, step=0.1),
            html.Label("Amplitude (°):"),
            dcc.Slider(id='amp-slider', min=5, max=60, value=30, step=5),
            html.Br(),
            html.Button('🐠 START TAIL FLAPPING', id='osc-btn', n_clicks=0,
                       style={'width': '100%', 'marginTop': '15px'})
        ])
    ]),
    
    html.Hr(),
    html.H3("📋 Command Log", style={'color': '#ff6b6b'}),
    html.Div(id='log', style={
        'background': 'rgba(0,0,0,0.3)', 'padding': '20px', 
        'borderRadius': '10px', 'maxHeight': '200px', 'overflowY': 'auto'
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
    
    # Status styling
    status_style = {
        'textAlign': 'center', 'fontSize': '18px', 'fontWeight': 'bold', 
        'padding': '15px', 'borderRadius': '10px', 'margin': '20px 0'
    }
    if connected:
        status_style.update({'background': 'rgba(0,255,127,0.2)', 'border': '2px solid #00ff7f'})
    else:
        status_style.update({'background': 'rgba(255,100,100,0.2)', 'border': '2px solid #ff6464'})
    
    # Live plot
    fig = go.Figure()
    if len(positions['x']) > 0:
        df = pd.DataFrame({'time': positions['x'], 'pos': positions['y']})
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['pos'], mode='lines', 
            name='Tail Position', line=dict(color='#00d4ff', width=4)
        ))
        fig.update_layout(
            title='🦈 Real-time Tail Flapping (ES9257 Servo)',
            xaxis_title='Time (s)', yaxis_title='Angle (°)',
            yaxis=dict(range=[0, 180]), height=450,
            plot_bgcolor='rgba(10,20,40,0.8)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e7ff')
        )
    else:
        fig.update_layout(
            title='📡 Waiting for servo feedback... (Upload .ino code)',
            height=450, plot_bgcolor='rgba(10,20,40,0.8)'
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
    global ser, log_messages
    
    ctx = dash.callback_context
    if not ctx.triggered or not ser or not ser.is_open:
        return html.Div("Waiting for Arduino connection...", 
                       style={'color': '#ff6b6b', 'padding': '20px'})
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    log_entry = []
    
    try:
        if button_id == 'calib-btn':
            ser.write(b'1\n')
            time.sleep(0.1)
            ser.write(f"{calib_val:.1f}\n".encode())
            log_entry.append(f"✅ CALIBRATE: {calib_val}° sent")
        elif button_id == 'osc-btn':
            ser.write(b'2\n')
            time.sleep(0.1)
            ser.write(f"{base_val:.1f}\n".encode())
            time.sleep(0.1)
            ser.write(f"{freq_val:.1f}\n".encode())
            time.sleep(0.1)
            ser.write(f"{amp_val:.1f}\n".encode())
            log_entry.append(f"✅ OSCILLATE: base={base_val}° freq={freq_val}Hz amp={amp_val}°")
    except Exception as e:
        log_entry.append(f"❌ Send failed: {str(e)[:50]}")
    
    log_messages.extend(log_entry)
    if len(log_messages) > 10:
        log_messages = log_messages[-10:]
    
    return html.Div([
        html.Ul([html.Li(msg, style={'margin': '8px 0', 'color': '#a0c4ff'}) 
                for msg in log_messages])
    ])

if __name__ == '__main__':
    print("🚀 BAUV Servo Dashboard v1.0")
    print(f"📡 Serial: {CONFIG['serial']['port']} @ {CONFIG['serial']['baudrate']}")
    print("🌐 UI: http://127.0.0.1:8050")
    print("⚠️  1. Upload servo_controller/servo_controller.ino")
    print("   2. Close Arduino IDE completely")
    print("   3. Watch live tail flapping! 🐠")
    
    app.run(
        host=CONFIG['dashboard']['host'],
        port=CONFIG['dashboard']['port'],
        debug=CONFIG['dashboard']['debug']
    )
