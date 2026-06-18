import time
from collections import deque
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go

mpu_time = deque(maxlen=300)
ax_data = deque(maxlen=300)
ay_data = deque(maxlen=300)
az_data = deque(maxlen=300)
gx_data = deque(maxlen=300)
gy_data = deque(maxlen=300)
gz_data = deque(maxlen=300)

latest_mpu = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}

def process_data(ax, ay, az, gx, gy, gz, t):
    latest_mpu.update({
        "ax": ax, "ay": ay, "az": az,
        "gx": gx, "gy": gy, "gz": gz
    })

    mpu_time.append(t)
    ax_data.append(ax)
    ay_data.append(ay)
    az_data.append(az)
    gx_data.append(gx)
    gy_data.append(gy)
    gz_data.append(gz)

def get_control_layout():
    return html.Div([
        html.H3("MPU6050 Live Readings", className="card-title"),
        html.Div(className="section-divider"),
        html.Div([
            html.Button("Start MPU", id="mpu-start-btn", n_clicks=0, className="btn-primary"),
            html.Button("Stop MPU", id="mpu-stop-btn", n_clicks=0, className="btn-danger", style={"marginLeft": "10px"}),
        ], className="button-row", style={"marginBottom": "15px"}),
        html.Div(id="mpu-command-output", className="command-output", style={"marginBottom": "15px"}),
        html.Div(id="mpu-readings", className="mpu-grid")
    ], className="control-card")

def get_graph_layout():
    return [
        html.Div([
            dcc.Graph(id="accel-graph", config={"displayModeBar": False})
        ], className="graph-card"),

        html.Div([
            dcc.Graph(id="gyro-graph", config={"displayModeBar": False})
        ], className="graph-card")
    ]

def register_callbacks(app, send_command_func, make_dark_figure_func):
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
        [Output("accel-graph", "figure"),
         Output("gyro-graph", "figure")],
        Input("update-interval", "n_intervals")
    )
    def update_graphs(n):
        try:
            m_time = list(mpu_time)
            ax = list(ax_data)
            ay = list(ay_data)
            az = list(az_data)
            gx = list(gx_data)
            gy = list(gy_data)
            gz = list(gz_data)
        except RuntimeError:
            raise dash.exceptions.PreventUpdate

        accel_fig = make_dark_figure_func("Linear Acceleration", "g")
        accel_fig.add_trace(go.Scatter(x=m_time, y=ax, mode="lines", name="Ax", line=dict(color="#ef4444")))
        accel_fig.add_trace(go.Scatter(x=m_time, y=ay, mode="lines", name="Ay", line=dict(color="#10b981")))
        accel_fig.add_trace(go.Scatter(x=m_time, y=az, mode="lines", name="Az", line=dict(color="#3b82f6")))

        gyro_fig = make_dark_figure_func("Angular Velocity", "deg/s")
        gyro_fig.add_trace(go.Scatter(x=m_time, y=gx, mode="lines", name="Gx", line=dict(color="#f59e0b")))
        gyro_fig.add_trace(go.Scatter(x=m_time, y=gy, mode="lines", name="Gy", line=dict(color="#8b5cf6")))
        gyro_fig.add_trace(go.Scatter(x=m_time, y=gz, mode="lines", name="Gz", line=dict(color="#ec4899")))

        return accel_fig, gyro_fig

    @app.callback(
        Output("mpu-command-output", "children"),
        Input("mpu-start-btn", "n_clicks"),
        Input("mpu-stop-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def handle_mpu_commands(start_clicks, stop_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "mpu-start-btn":
            cmd = "MPU_START"
        elif trigger_id == "mpu-stop-btn":
            cmd = "MPU_STOP"
        else:
            return dash.no_update
            
        msg, err = send_command_func(cmd)
        if err:
            return err
        return msg
