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
        # Return the custom home page layout
        return html.Div([
            # Heading
            html.Div(
                html.H1("Welcome to the Dashboard", style={"textAlign": "center", "marginBottom": "20px"}),
                style={"padding": "20px"}
            ),

            # Row with images and text/links
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Img(src="/assets/image1.jpg", style={"width": "100%"}),
                                html.A("Go to Matrix Map", href="/matrix",
                                       style={"display": "block", "textAlign": "center", "marginTop": "10px"})
                            ]
                        ),
                        width=4
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Img(src="/assets/image2.jpg", style={"width": "100%"}),
                                html.A("Go to A-B Map", href="/AB_map",
                                       style={"display": "block", "textAlign": "center", "marginTop": "10px"})
                            ]
                        ),
                        width=4
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Img(src="/assets/image3.jpg", style={"width": "100%"}),
                                html.A("More Info", href="#",
                                       style={"display": "block", "textAlign": "center", "marginTop": "10px"})
                            ]
                        ),
                        width=4
                    ),
                ],
                style={"marginBottom": "40px"}
            ),

            # Static text box
            html.Div(
                html.P(
                    """
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
                    Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
                    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. 
                    Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
                    """,
                    style={
                        "padding": "20px",
                        "border": "1px solid #ddd",
                        "borderRadius": "5px",
                        "backgroundColor": "#f9f9f9",
                        "fontSize": "16px",
                        "lineHeight": "1.5",
                        "marginBottom": "20px"
                    }
                )
            ),

            # Bottom image
            html.Div(
                html.Img(src="/assets/image4.jpg", style={"width": "20%"}),
                style={"textAlign": "center"}
            )
        ])


# Run the app
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8050)
