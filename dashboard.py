import time
import threading
from collections import deque

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import serial

PORT = "COM3"   # change this
BAUD = 115200

servo_data = deque(maxlen=300)
servo_time = deque(maxlen=300)

mpu_time = deque(maxlen=300)
ax_data = deque(maxlen=300)
ay_data = deque(maxlen=300)
az_data = deque(maxlen=300)
gx_data = deque(maxlen=300)
gy_data = deque(maxlen=300)
gz_data = deque(maxlen=300)

latest_status = "Disconnected"
latest_mpu = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}

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
    global latest_status, latest_mpu, connected
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
                    servo_data.append(val)
                    servo_time.append(t)

                elif parts[0] == "MPU" and len(parts) == 7:
                    ax, ay, az, gx, gy, gz = map(float, parts[1:])
                    t = time.time() - start_time

                    latest_mpu = {
                        "ax": ax, "ay": ay, "az": az,
                        "gx": gx, "gy": gy, "gz": gz
                    }

                    mpu_time.append(t)
                    ax_data.append(ax)
                    ay_data.append(ay)
                    az_data.append(az)
                    gx_data.append(gx)
                    gy_data.append(gy)
                    gz_data.append(gz)

                elif parts[0] == "STATUS":
                    latest_status = " | ".join(parts[1:])

                elif parts[0] == "SYS":
                    latest_status = " | ".join(parts)

        except Exception as e:
            latest_status = f"Read error: {e}"
            connected = False


connect_serial()

app = dash.Dash(__name__)
app.title = "BAUV Hardware Dashboard"


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


app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1("BAUV Servo + MPU6050 Dashboard", className="app-title"),
            html.P("Real-time monitoring and control for servo motion and inertial sensing.", className="app-subtitle"),
            html.Div(id="status-container")
        ])
    ], className="header-row"),

    html.Div([
        html.Div([
            html.H3("Servo Control", className="card-title"),
            html.Div(className="section-divider"),

            html.Div([
                html.Label("Base Angle", className="label"),
                dcc.Slider(
                    0, 180, 1,
                    value=90,
                    id="angle-slider",
                    marks={0: "0", 45: "45", 90: "90", 135: "135", 180: "180"}
                ),
            ], className="input-wrap"),

            html.Div([
                html.Label("Frequency (Hz)", className="label"),
                dcc.Input(id="freq-input", type="number", value=0.7, step=0.1),
            ], className="input-wrap"),

            html.Div([
                html.Label("Amplitude (deg)", className="label"),
                dcc.Input(id="amp-input", type="number", value=20, step=1),
            ], className="input-wrap"),

            html.Div([
                html.Button("Calibrate", id="cal-btn", n_clicks=0, className="btn-primary"),
                html.Button("Start Oscillation", id="osc-btn", n_clicks=0, className="btn-secondary"),
                html.Button("Stop", id="stop-btn", n_clicks=0, className="btn-danger"),
            ], className="button-row"),

            html.Div(id="command-output", className="command-output")
        ], className="control-card"),

        html.Div([
            html.H3("MPU6050 Live Readings", className="card-title"),
            html.Div(className="section-divider"),
            html.Div(id="mpu-readings", className="mpu-grid")
        ], className="control-card")
    ], className="main-grid"),

    html.Div([
        html.Div([
            dcc.Graph(id="servo-graph", config={"displayModeBar": False})
        ], className="graph-card"),

        html.Div([
            dcc.Graph(id="accel-graph", config={"displayModeBar": False})
        ], className="graph-card"),

        html.Div([
            dcc.Graph(id="gyro-graph", config={"displayModeBar": False})
        ], className="graph-card"),
    ], className="graph-grid"),

    dcc.Interval(id="update-interval", interval=200, n_intervals=0)
], className="app-container")


@app.callback(
    Output("status-container", "children"),
    Input("update-interval", "n_intervals")
)
def update_status(n):
    bg_class = "status-bg-green" if connected else "status-bg-red"
    text = f"System Status: {'Connected' if connected else 'Disconnected'}"
    return html.Div(text, className=f"compact-status {bg_class}")


@app.callback(
    Output("mpu-readings", "children"),
    Input("update-interval", "n_intervals")
)
def update_mpu(n):
    return [
        html.Div([html.Span("Ax: "), html.Strong(f"{latest_mpu['ax']:.2f}")]),
        html.Div([html.Span("Ay: "), html.Strong(f"{latest_mpu['ay']:.2f}")]),
        html.Div([html.Span("Az: "), html.Strong(f"{latest_mpu['az']:.2f}")]),
        html.Div([html.Span("Gx: "), html.Strong(f"{latest_mpu['gx']:.2f}")]),
        html.Div([html.Span("Gy: "), html.Strong(f"{latest_mpu['gy']:.2f}")]),
        html.Div([html.Span("Gz: "), html.Strong(f"{latest_mpu['gz']:.2f}")])
    ]


@app.callback(
    [Output("servo-graph", "figure"),
     Output("accel-graph", "figure"),
     Output("gyro-graph", "figure")],
    Input("update-interval", "n_intervals")
)
def update_graphs(n):
    servo_fig = make_dark_figure("Servo Angle", "Angle (deg)", y_range=[0, 180])
    servo_fig.add_trace(go.Scatter(x=list(servo_time), y=list(servo_data), mode="lines", name="Angle", line=dict(color="#3b82f6", width=2)))

    accel_fig = make_dark_figure("Linear Acceleration", "g")
    accel_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(ax_data), mode="lines", name="Ax", line=dict(color="#ef4444")))
    accel_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(ay_data), mode="lines", name="Ay", line=dict(color="#10b981")))
    accel_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(az_data), mode="lines", name="Az", line=dict(color="#3b82f6")))

    gyro_fig = make_dark_figure("Angular Velocity", "deg/s")
    gyro_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(gx_data), mode="lines", name="Gx", line=dict(color="#f59e0b")))
    gyro_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(gy_data), mode="lines", name="Gy", line=dict(color="#8b5cf6")))
    gyro_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(gz_data), mode="lines", name="Gz", line=dict(color="#ec4899")))

    return servo_fig, accel_fig, gyro_fig


@app.callback(
    Output("command-output", "children"),
    Input("cal-btn", "n_clicks"),
    Input("osc-btn", "n_clicks"),
    Input("stop-btn", "n_clicks"),
    Input("angle-slider", "value"),
    State("freq-input", "value"),
    State("amp-input", "value"),
    prevent_initial_call=True
)
def handle_commands(cal_clicks, osc_clicks, stop_clicks, angle, freq, amp):
    ctx = callback_context
    if not ctx.triggered:
        return ""
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "cal-btn":
        cmd = "CAL"
    elif trigger_id == "osc-btn":
        cmd = f"OSC,{freq},{amp}"
    elif trigger_id == "stop-btn":
        cmd = "STOP"
    elif trigger_id == "angle-slider":
        cmd = f"SET,{angle}"
    else:
        return ""
        
    try:
        if ser and ser.is_open:
            ser.write((cmd + "\n").encode())
            return f"Sent: {cmd}"
        return "Serial not connected"
    except Exception as e:
        return f"Error sending: {e}"


if __name__ == "__main__":
    app.run(debug=True, port=8050)