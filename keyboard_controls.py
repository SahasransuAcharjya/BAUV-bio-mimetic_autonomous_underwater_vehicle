from dash 
import html, dcc, Input, Output

def get_keyboard_layout():
    return html.Div([
        dcc.Location(id='keyboard-url'),
        html.Div(id='keyboard-out', style={'display': 'none'})
    ])

def register_keyboard_callbacks(app):
    app.clientside_callback(
        """
        function(href) {
            if (!window.keyboardListenerAdded) {
                window.keyboardListenerAdded = true;
                window.isOscillating = false;
                
                document.addEventListener('keydown', function(e) {
                    // Don't trigger if typing in an input box
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                        return;
                    }

                    // Prevent scrolling for Space and Arrows
                    if ([' ', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                        e.preventDefault();
                    }
                    
                    if (e.key === 'c' || e.key === 'C') {
                        let btn = document.getElementById('cal-btn');
                        if (btn) btn.click();
                    } 
                    else if (e.key === ' ') {
                        if (window.isOscillating) {
                            let btn = document.getElementById('stop-btn');
                            if (btn) btn.click();
                            window.isOscillating = false;
                        } else {
                            let btn = document.getElementById('osc-btn');
                            if (btn) btn.click();
                            window.isOscillating = true;
                        }
                    } 
                    else if (e.key === 'ArrowLeft') {
                        let btn = document.getElementById('left-btn');
                        if (btn) btn.click();
                        window.isOscillating = true;
                    } 
                    else if (e.key === 'ArrowRight') {
                        let btn = document.getElementById('right-btn');
                        if (btn) btn.click();
                        window.isOscillating = true;
                    }
                });

                // Listen to actual clicks to keep state in sync
                document.addEventListener('click', function(e) {
                    let id = e.target.id;
                    if (id === 'osc-btn' || id === 'left-btn' || id === 'right-btn') {
                        window.isOscillating = true;
                    } else if (id === 'stop-btn' || id === 'cal-btn') {
                        window.isOscillating = false;
                    }
                });
            }
            return "";
        }
        """,
        Output("keyboard-out", "children"),
        Input("keyboard-url", "href")
    )
