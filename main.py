from dash import dcc, html
from dash.dependencies import Input, Output
from app import app  # Import the Dash instance from app.py
import dash_bootstrap_components as dbc
from flask import send_from_directory
# Import the independent app layouts
from pages.Matrix import scatterplot_layout, download_folder, csv_folder
from pages.AB_Mapper import toast_map_layout
from pages.compare import compare_layout  # Import the new compare page layout

app.index_string = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Helsinki Travel Time Matrix</title>
    <link rel="icon" href="/assets/images/ttm-logo-2.png" type="image/x-icon">
    {%metas%}
    {%css%}
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
"""


# Serve files from the 'download_folder'
@app.server.route('/download/<filename>')
def serve_file(filename):
    try:
        # Determine the folder based on the file extension
        if filename.endswith(".csv"):
            folder = csv_folder  # Path to your CSV files
        else:
            folder = download_folder  # Path to your GPKG files

        print(f"[DEBUG] Serving file: {filename} from {folder}")
        return send_from_directory(directory=folder, path=filename, as_attachment=True)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        return f"Error: {filename} not found.", 404
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return f"Error: Unable to serve file {filename}.", 500





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
    elif pathname == '/compare':
        return compare_layout  # Add the new page
    else:
        # Return the custom home page layout
        return html.Div([
            # Heading
            html.Div(
                html.H1("Helsinki Travel Time Matrix", style={"textAlign": "center", "marginBottom": "20px"}),
                style={"padding": "20px"}
            ),

            # Row with images and text/links
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Img(src="/assets/images/matrix.jpg", style={"width": "100%"}),
                                html.A("Go to Matrix Map", href="/matrix",
                                       style={"display": "block", "textAlign": "center", "marginTop": "10px"})
                            ]
                        ),
                        width=4
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Img(src="/assets/images/a-b.jpg", style={"width": "100%"}),
                                html.A("Go to A-B Map", href="/AB_map",
                                       style={"display": "block", "textAlign": "center", "marginTop": "10px"})
                            ]
                        ),
                        width=4
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Img(src="/assets/images/compare.jpg", style={"width": "100%"}),
                                html.A("Go to Compare Page", href="/compare",
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
                    [
                        """
            This travel time matrix records travel times and travel distances for routes between all centroids (N = 13231) of a 250 × 250 m 
            grid over the Helsinki metropolitan area by walking, cycling, public transportation, and private car. If applicable, the routes have been 
            calculated for different times of the day (rush hour, midday, nighttime), and assuming different physical abilities 
            (such as walking and cycling speeds), see details below.
            On this website you can browse this data in three different visual ways (matrix, compare, Origin-Destination mapper) and download in different formats. 
            Read more about """,
                        html.A(
                            "Travel Time Matrix",
                            href="https://www.helsinki.fi/en/researchgroups/digital-geography-lab/helsinki-region-travel-time-matrix-2023",
                            target="_blank",
                            style={"color": "#007bff", "textDecoration": "underline"}
                        ),
                        "."
                    ],
                    style={
                        "padding": "20px",
                        "border": "1px solid #ddd",
                        "borderRadius": "5px",
                        "backgroundColor": "#f9f9f9",
                        "fontSize": "22px",
                        "lineHeight": "1.5",
                        "marginBottom": "20px"
                    }
                )
            ),

            # Bottom image
            html.Div(
                html.Img(src="/assets/images/footer-logo.jpg", style={"width": "35%"}),
                style={"textAlign": "center"}
            )
        ])


# Run the app
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8050)
