import time
from collections import deque
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go

servo_data = deque(maxlen=300)
servo_time = deque(maxlen=300)

def process_data(val, t):
    servo_data.append(val)
    servo_time.append(t)

def get_control_layout():
    return html.Div([
        html.H3("Servo Control", className="card-title"),
        html.Div(className="section-divider"),
        dcc.Store(id="turn-state", data="none"),

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

        html.Div([
            html.Button("Turn Left", id="left-btn", n_clicks=0, className="btn-secondary"),
            html.Button("Turn Right", id="right-btn", n_clicks=0, className="btn-secondary"),
        ], className="button-row", style={"marginTop": "10px"}),

        html.Div(id="command-output", className="command-output")
    ], className="control-card")

def get_graph_layout():
    return html.Div([
        dcc.Graph(id="servo-graph", config={"displayModeBar": False})
    ], className="graph-card")

def register_callbacks(app, send_command_func, make_dark_figure_func):
    @app.callback(
        Output("servo-graph", "figure"),
        Input("update-interval", "n_intervals")
    )
    def update_servo_graph(n):
        try:
            s_time = list(servo_time)
            s_data = list(servo_data)
        except RuntimeError:
            raise dash.exceptions.PreventUpdate

        servo_fig = make_dark_figure_func("Servo Angle", "Angle (deg)", y_range=[0, 180])
        servo_fig.add_trace(go.Scatter(x=s_time, y=s_data, mode="lines", name="Angle", line=dict(color="#3b82f6", width=2)))
        return servo_fig

    @app.callback(
        Output("command-output", "children"),
        Output("turn-state", "data"),
        Output("left-btn", "className"),
        Output("right-btn", "className"),
        Input("cal-btn", "n_clicks"),
        Input("osc-btn", "n_clicks"),
        Input("stop-btn", "n_clicks"),
        Input("angle-slider", "value"),
        Input("left-btn", "n_clicks"),
        Input("right-btn", "n_clicks"),
        State("freq-input", "value"),
        State("amp-input", "value"),
        State("turn-state", "data"),
        prevent_initial_call=True
    )
    def handle_servo_commands(cal_clicks, osc_clicks, stop_clicks, angle, left_clicks, right_clicks, freq, amp, turn_state):
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, turn_state, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        cmd = ""
        new_state = turn_state
        
        if trigger_id == "cal-btn":
            cmd = f"CAL,{angle}"
            new_state = "none"
        elif trigger_id == "osc-btn":
            cmd = f"OSC,{angle},{freq},{amp}"
            new_state = "none"
        elif trigger_id == "stop-btn":
            cmd = "STOP"
            new_state = "none"
        elif trigger_id == "angle-slider":
            cmd = f"CAL,{angle}"
            new_state = "none"
        elif trigger_id == "left-btn":
            if turn_state == "left":
                cmd = f"OSC,{angle},{freq},{amp}"
                new_state = "none"
            else:
                cmd = f"OSC,90.0,{freq},10.0"
                new_state = "left"
        elif trigger_id == "right-btn":
            if turn_state == "right":
                cmd = f"OSC,{angle},{freq},{amp}"
                new_state = "none"
            else:
                cmd = f"OSC,110.0,{freq},10.0"
                new_state = "right"
        else:
            return dash.no_update, turn_state, dash.no_update, dash.no_update
            
        msg, err = send_command_func(cmd)
        
        left_class = "btn-primary" if new_state == "left" else "btn-secondary"
        right_class = "btn-primary" if new_state == "right" else "btn-secondary"
        
        if err:
            return err, new_state, left_class, right_class
        return msg, new_state, left_class, right_class
