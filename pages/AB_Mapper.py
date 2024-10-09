import geopandas as gpd
import sqlite3
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from app import app  # Make sure you import the app instance from app.py

# Path to data files
db_path = 'data/full_csvs.db'
gridfile = 'data/Helsinki_Travel_Time_Matrix_2023_grid.gpkg'

# Load the grid data
grid_gdf = gpd.read_file(gridfile)

# Ensure the CRS is set to EPSG:4326 for mapping
if grid_gdf.crs is None or grid_gdf.crs != 'EPSG:4326':
    grid_gdf = grid_gdf.to_crs('EPSG:4326')

grid_gdf = grid_gdf[grid_gdf.is_valid]

# Calculate the map center and cell centroid coordinates once
center_lat = grid_gdf.geometry.centroid.y.mean()
center_lon = grid_gdf.geometry.centroid.x.mean()
latitudes = grid_gdf.geometry.centroid.y
longitudes = grid_gdf.geometry.centroid.x

# Global variable to store the current queried pair (reset after third click)
current_queries = []

# Create the base map figure with an option to highlight selected and queried grid cells
def create_map(selected_ids=[], queried_ids=[], zoom=9.5):
    fig = go.Figure()

    # Plot all grid cells
    fig.add_trace(
        go.Scattermapbox(
            lat=latitudes,
            lon=longitudes,
            mode='markers',
            marker=dict(size=13, color='blue', opacity=0.3),
            hoverinfo='text',
            hovertext=grid_gdf['id'].astype(str),
            name='All Grid Cells'
        )
    )

    # Highlight the currently selected grid cells (in red)
    if selected_ids:
        selected_gdf = grid_gdf[grid_gdf['id'].isin(selected_ids)]
        fig.add_trace(
            go.Scattermapbox(
                lat=selected_gdf.geometry.centroid.y,
                lon=selected_gdf.geometry.centroid.x,
                mode='markers',
                marker=dict(size=20, color='red', opacity=0.8),
                hoverinfo='text',
                hovertext=selected_gdf['id'].astype(str)
            )
        )

    # Highlight the currently queried pair (in green)
    if queried_ids:
        queried_gdf = grid_gdf[grid_gdf['id'].isin(queried_ids)]
        fig.add_trace(
            go.Scattermapbox(
                lat=queried_gdf.geometry.centroid.y,
                lon=queried_gdf.geometry.centroid.x,
                mode='markers',
                marker=dict(size=20, color='orange', opacity=0.8),
                hoverinfo='text',
                hovertext=queried_gdf['id'].astype(str),
                name='Queried Pairs'
            )
        )

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            zoom=zoom,
            center=dict(lat=center_lat, lon=center_lon)
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False
    )

    return fig

# Define layout for this page with a vertical box on the left and map on the right
toast_map_layout = html.Div([
    html.Div(id='floating-box', children=[
        html.H4("A-B Query"),
        html.Div(
            id="query-result",
            children="Click on two grid cells to query the database.",
            style={'width': '100%', 'height': 'auto'}
        )
    ], style={
        'width': '300px',
        'backgroundColor': 'rgba(255, 255, 255, 0.9)',
        'border': '1px solid black',
        'padding': '10px',
        'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.4)',
        'zIndex': '1000',
        'overflowY': 'auto',
        'height': '100vh',
        'display': 'inline-block',
        'verticalAlign': 'top'
    }),

    html.Div([
        dcc.Graph(
            id='toast-map',
            figure=create_map(),
            config={'scrollZoom': True},
            style={'height': '100vh', 'width': '100%', 'flexGrow': '1'}
        )
    ], style={'display': 'inline-block', 'width': 'calc(100% - 300px)', 'height': '100vh'})
], style={'display': 'flex', 'flexDirection': 'row', 'height': '100vh'})

# Define the query_db function
def query_db(from_id, to_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query the database for the travel time details including walk_d
        query = """
            SELECT walk_d, walk_avg, walk_slo, bike_avg, bike_fst, bike_slo, 
                   pt_r_avg, pt_r_slo, pt_m_avg, pt_m_slo, 
                   pt_n_avg, pt_n_slo, car_r, car_m, car_n
            FROM full_DB 
            WHERE from_id = ? AND to_id = ?
        """
        cursor.execute(query, (from_id, to_id))
        result = cursor.fetchone()

        conn.close()

        if not result:
            return None

        travel_times = [
            ("Walking (average speed):", result[1]),
            ("Walking (slow speed):", result[2]),
            ("Cycling (average speed):", result[3]),
            ("Cycling (fast speed):", result[4]),
            ("Cycling (slow speed):", result[5]),
            ("Public transport (rush hour, average walk):", result[6]),
            ("Public transport (rush hour, slow walk):", result[7]),
            ("Public transport (midday, average walk):", result[8]),
            ("Public transport (midday, slow walk):", result[9]),
            ("Public transport (night, average walk):", result[10]),
            ("Public transport (night, slow walk):", result[11]),
            ("Car (rush hour):", result[12]),
            ("Car (midday):", result[13]),
            ("Car (night):", result[14])
        ]

        description = [
            html.Div([html.B("Walking distance:"), f" {int(result[0])} meters"]),
            html.Br(),
            html.Div(["Travel Times:"])
        ]
        description.extend([html.Div([label, f" {int(time)}"]) for label, time in travel_times])
        description.append(html.Div(["All times in minutes."]))

        return description
    except Exception as e:
        return None

# Callback for updating the map and selecting cells
@app.callback(
    [Output('toast-map', 'figure'),
     Output('query-result', 'children')],
    [Input('toast-map', 'clickData')],
    [State('query-result', 'children'),
     State('toast-map', 'relayoutData')]  # Capture current zoom from the map
)
def update_map(click_data, current_output, relayout_data):
    global current_queries

    zoom = 9.5
    if relayout_data:
        zoom = relayout_data.get('mapbox.zoom', zoom)

    if click_data is None:
        return create_map(zoom=zoom), "Click on two grid cells to query the database."

    try:
        clicked_id = int(click_data['points'][0]['hovertext'])
    except (KeyError, ValueError):
        return create_map(zoom=zoom), "Invalid click - no grid cell ID detected."

    if "Clicked IDs" in current_output:
        previous_clicks = [int(id) for id in current_output.split(": ")[1].split(", ")]
    else:
        previous_clicks = []

    previous_clicks.append(clicked_id)

    if len(previous_clicks) > 2:
        current_queries = []
        previous_clicks = [clicked_id]

    if len(previous_clicks) == 2:
        from_id = previous_clicks[0]
        to_id = previous_clicks[1]

        result = query_db(from_id, to_id)

        if result:
            result_message = html.Div([
                html.Div([f"From id: {from_id}, to id: {to_id} (minutes)"]),
                html.Hr(),
            ] + result)

            current_queries = [from_id, to_id]

        else:
            result_message = f"No data found for from_id: {from_id}, to_id: {to_id}"

        previous_clicks = []
        return create_map(queried_ids=current_queries, zoom=zoom), result_message

    output_message = f"Clicked IDs: {', '.join(map(str, previous_clicks))}"
    new_fig = create_map(selected_ids=previous_clicks, queried_ids=current_queries, zoom=zoom)
    return new_fig, output_message
