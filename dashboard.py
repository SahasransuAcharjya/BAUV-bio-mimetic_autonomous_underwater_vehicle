import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
from collections import deque
import serial
import threading
import time

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
    global ser, connected, latest_status
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)
        connected = True
        latest_status = f"Connected to {PORT}"
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

card_style = {
    "backgroundColor": "#ffffff",
    "padding": "16px",
    "borderRadius": "14px",
    "boxShadow": "0 4px 16px rgba(0,0,0,0.08)",
    "marginBottom": "16px"
}

mini_card = {
    "backgroundColor": "#f7f9fc",
    "padding": "14px",
    "borderRadius": "12px",
    "textAlign": "center",
    "boxShadow": "inset 0 0 0 1px rgba(0,0,0,0.05)"
}

app.layout = html.Div([
    html.H1("BAUV Servo + MPU6050 Dashboard", style={"textAlign": "center"}),

    html.Div(id="status-box", style={**card_style, "fontWeight": "600"}),

    html.Div([
        html.Div([
            html.H3("Servo Control"),
            html.Label("Angle"),
            dcc.Slider(0, 180, 1, value=90, id="angle-slider",
                       marks={0: "0", 90: "90", 180: "180"}),
            html.Br(),
            html.Label("Frequency (Hz)"),
            dcc.Input(id="freq-input", type="number", value=0.7, step=0.1),
            html.Br(), html.Br(),
            html.Label("Amplitude"),
            dcc.Input(id="amp-input", type="number", value=20, step=1),
            html.Br(), html.Br(),
            html.Button("Calibrate", id="cal-btn", n_clicks=0, style={"marginRight": "10px"}),
            html.Button("Start Oscillation", id="osc-btn", n_clicks=0, style={"marginRight": "10px"}),
            html.Button("Stop", id="stop-btn", n_clicks=0),
            html.Div(id="command-output", style={"marginTop": "12px"})
        ], style=card_style),

        html.Div([
            html.H3("MPU6050 Live Readings"),
            html.Div([
                html.Div([html.H4("Accel X"), html.Div(id="ax-live")], style=mini_card),
                html.Div([html.H4("Accel Y"), html.Div(id="ay-live")], style=mini_card),
                html.Div([html.H4("Accel Z"), html.Div(id="az-live")], style=mini_card),
                html.Div([html.H4("Gyro X"), html.Div(id="gx-live")], style=mini_card),
                html.Div([html.H4("Gyro Y"), html.Div(id="gy-live")], style=mini_card),
                html.Div([html.H4("Gyro Z"), html.Div(id="gz-live")], style=mini_card),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(3, 1fr)",
                "gap": "12px"
            })
        ], style=card_style)
    ], style={
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr",
        "gap": "16px"
    }),

    html.Div([
        html.Div([
            dcc.Graph(id="servo-graph")
        ], style=card_style),

        html.Div([
            dcc.Graph(id="accel-graph")
        ], style=card_style),

        html.Div([
            dcc.Graph(id="gyro-graph")
        ], style=card_style)
    ]),

    dcc.Interval(id="interval", interval=300, n_intervals=0)
], style={
    "padding": "20px",
    "backgroundColor": "#eef2f7",
    "minHeight": "100vh",
    "fontFamily": "Arial, sans-serif"
})

@app.callback(
    Output("command-output", "children"),
    Input("cal-btn", "n_clicks"),
    Input("osc-btn", "n_clicks"),
    Input("stop-btn", "n_clicks"),
    State("angle-slider", "value"),
    State("freq-input", "value"),
    State("amp-input", "value")
)
def send_command(cal_clicks, osc_clicks, stop_clicks, angle, freq, amp):
    global ser
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    try:
        if ser is None:
            return "Serial not connected"

        if button_id == "cal-btn":
            ser.write(f"CAL,{angle}\n".encode())
            return f"Sent calibrate command: angle={angle}"

        if button_id == "osc-btn":
            ser.write(f"OSC,{angle},{freq},{amp}\n".encode())
            return f"Sent oscillation command: base={angle}, freq={freq}, amp={amp}"

        if button_id == "stop-btn":
            ser.write(b"STOP\n")
            return "Sent stop command"

    except Exception as e:
        return f"Command error: {e}"

    return ""

@app.callback(
    Output("status-box", "children"),
    Output("ax-live", "children"),
    Output("ay-live", "children"),
    Output("az-live", "children"),
    Output("gx-live", "children"),
    Output("gy-live", "children"),
    Output("gz-live", "children"),
    Output("servo-graph", "figure"),
    Output("accel-graph", "figure"),
    Output("gyro-graph", "figure"),
    Input("interval", "n_intervals")
)
def update_dashboard(n):
    servo_fig = go.Figure()
    servo_fig.add_trace(go.Scatter(x=list(servo_time), y=list(servo_data), mode="lines", name="Servo"))
    servo_fig.update_layout(
        title="Servo Position",
        xaxis_title="Time (s)",
        yaxis_title="Angle (deg)",
        yaxis=dict(range=[0, 180]),
        template="plotly_white"
    )

    accel_fig = go.Figure()
    accel_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(ax_data), mode="lines", name="Ax"))
    accel_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(ay_data), mode="lines", name="Ay"))
    accel_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(az_data), mode="lines", name="Az"))
    accel_fig.update_layout(
        title="Accelerometer",
        xaxis_title="Time (s)",
        yaxis_title="Raw value",
        template="plotly_white"
    )

    gyro_fig = go.Figure()
    gyro_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(gx_data), mode="lines", name="Gx"))
    gyro_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(gy_data), mode="lines", name="Gy"))
    gyro_fig.add_trace(go.Scatter(x=list(mpu_time), y=list(gz_data), mode="lines", name="Gz"))
    gyro_fig.update_layout(
        title="Gyroscope",
        xaxis_title="Time (s)",
        yaxis_title="Raw value",
        template="plotly_white"
    )

    return (
        f"Status: {latest_status}",
        str(latest_mpu['ax']),
        str(latest_mpu['ay']),
        str(latest_mpu['az']),
        str(latest_mpu['gx']),
        str(latest_mpu['gy']),
        str(latest_mpu['gz']),
        servo_fig,
        accel_fig,
        gyro_fig
    )

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)