from dash import dcc, html
from dash.dependencies import Input, Output
from app import app  # Import the Dash instance from app.py
import dash_bootstrap_components as dbc

# Import the independent app layouts
from pages.Matrix import scatterplot_layout
from pages.AB_Mapper import toast_map_layout

# Define the main layout with URL-based navigation
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
])

# Callback to dynamically serve pages based on URL
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/matrix':
        return scatterplot_layout
    elif pathname == '/AB_map':
        return toast_map_layout
    else:
        return html.Div([
            html.H2("Welcome to the Dashboard"),
            dcc.Link("Go to Matrix Map", href='/matrix'),
            html.Br(),
            dcc.Link("Go to A-B Map", href='/AB_map'),
        ])

# Run the app
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8050)
