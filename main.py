import time
import threading
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import serial

import tail
import imu
import keyboard_controls

PORT = "COM7"   # change this
BAUD = 115200

latest_status = "Disconnected"
ser = None
connected = False
start_time = time.time()

def connect_serial():
    global ser, connected, latest_status, start_time
    try:
        if ser and ser.is_open:
            ser.close()
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)
        connected = True
        start_time = time.time()
        latest_status = f"Connected to {PORT} @ {BAUD}"
        threading.Thread(target=read_serial, daemon=True).start()
    except Exception as e:
        connected = False
        latest_status = f"Connection failed: {e}"

def read_serial():
    global latest_status, connected
    while connected:
        try:
            if ser and ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                parts = line.split(",")

                if parts[0] == "SERVO" and len(parts) >= 2:
                    val = float(parts[1])
                    t = time.time() - start_time
                    tail.process_data(val, t)

                elif parts[0] == "MPU" and len(parts) == 7:
                    ax, ay, az, gx, gy, gz = map(float, parts[1:])
                    t = time.time() - start_time
                    imu.process_data(ax, ay, az, gx, gy, gz, t)

                elif parts[0] == "STATUS":
                    latest_status = " | ".join(parts[1:])

                elif parts[0] == "SYS":
                    latest_status = " | ".join(parts)

        except Exception as e:
            latest_status = f"Read error: {e}"
            connected = False

def send_command(cmd):
    try:
        if ser and ser.is_open:
            ser.write((cmd + "\n").encode())
            return f"Sent: {cmd}", None
        else:
            return None, "Serial not connected"
    except Exception as e:
        return None, f"Error sending: {e}"

def make_dark_figure(title, y_title, y_range=None):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=320,
        template=None,
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font={"color": "#e2e8f0", "family": "Inter, Arial, sans-serif"},
        margin=dict(l=40, r=20, t=50, b=30),
        xaxis=dict(
            title="Time (s)",
            gridcolor="#334155",
            zerolinecolor="#334155",
            color="#94a3b8"
        ),
        yaxis=dict(
            title=y_title,
            gridcolor="#334155",
            zerolinecolor="#334155",
            color="#94a3b8"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)"
        )
    )
    if y_range is not None:
        fig.update_yaxes(range=y_range)
    return fig

connect_serial()

app = dash.Dash(__name__)
app.title = "BAUV Hardware Dashboard"

# Register callbacks from modules
tail.register_callbacks(app, send_command, make_dark_figure)
imu.register_callbacks(app, send_command, make_dark_figure)
keyboard_controls.register_keyboard_callbacks(app)

app.layout = html.Div([
    keyboard_controls.get_keyboard_layout(),
    html.Div([
        html.Div([
            html.H1("BAUV Servo + MPU6050 Dashboard", className="app-title"),
            html.P("Real-time monitoring and control for servo motion and inertial sensing.", className="app-subtitle"),
            html.Div(id="status-container"),
            html.Button("Reconnect Serial", id="reconnect-btn", n_clicks=0, className="btn-primary", style={"marginTop": "10px"})
        ])
    ], className="header-row"),

    html.Div([
        tail.get_control_layout(),
        imu.get_control_layout()
    ], className="main-grid"),

    html.Div([
        tail.get_graph_layout(),
        *imu.get_graph_layout()
    ], className="graph-grid"),

    dcc.Interval(id="update-interval", interval=200, n_intervals=0)
], className="app-container")

@app.callback(
    Output("status-container", "children"),
    Input("update-interval", "n_intervals")
)
def update_status(n):
    bg_class = "status-bg-green" if connected else "status-bg-red"
    text = f"System Status: {latest_status}"
    return html.Div(text, className=f"compact-status {bg_class}")

@app.callback(
    Output("reconnect-btn", "className"),
    Input("reconnect-btn", "n_clicks"),
    prevent_initial_call=True
)
def handle_reconnect(n_clicks):
    connect_serial()
    return "btn-primary"

if __name__ == "__main__":
    app.run(debug=True, port=8050, use_reloader=False)


