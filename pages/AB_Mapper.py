import geopandas as gpd
import sqlite3
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from app import app  # Make sure you import the app instance from app.py
import dash
from dash import dash_table  # Ensure the DataTable module is explicitly imported

# Path to data files
db_path = 'data/full_csvs.db'
gridfile = 'data/Helsinki_Travel_Time_Matrix_2023_grid.gpkg'
borders= 'assets/vector/borders.gpkg'

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

# add muncipality borders
borders_gdf = gpd.read_file(borders)

print(borders_gdf.head())

# Ensure the CRS is EPSG:4326 (WGS84) for Mapbox compatibility
if borders_gdf.crs is None or borders_gdf.crs != 'EPSG:4326':
    print("[DEBUG] Reprojecting borders CRS to EPSG:4326...")
    borders_gdf = borders_gdf.to_crs(epsg=4326)

# Create the base map figure with an option to highlight selected and queried grid cells
def create_map(selected_ids=[], queried_ids=[], zoom=9.5):
    fig = go.Figure()

    # Plot all grid cells
    fig.add_trace(
        go.Scattermapbox(
            lat=latitudes,
            lon=longitudes,
            mode='markers',
            marker=dict(size=13, color='blue', opacity=0.1),
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
    # Add city borders as a new trace
    for _, row in borders_gdf.iterrows():
        geometry = row.geometry
        if geometry.geom_type == 'Polygon':
            coords = list(geometry.exterior.coords)
            lons, lats = zip(*coords)  # Correct order: longitude (x), latitude (y)
            fig.add_trace(
                go.Scattermapbox(
                    lat=lats,
                    lon=lons,
                    mode='lines',
                    line=dict(width=1, color='black'),
                    hoverinfo='none',
                    name='City Borders'
                )
            )
        elif geometry.geom_type == 'MultiPolygon':
            for polygon in geometry.geoms:
                coords = list(polygon.exterior.coords)
                lons, lats = zip(*coords)  # Correct order: longitude (x), latitude (y)
                fig.add_trace(
                    go.Scattermapbox(
                        lat=lats,
                        lon=lons,
                        mode='lines',
                        line=dict(width=1, color='black'),
                        hoverinfo='none',
                        name='City Borders'
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
            FROM FULL_CV 
            WHERE from_id = ? AND to_id = ?
        """
        cursor.execute(query, (from_id, to_id))
        result = cursor.fetchone()

        conn.close()

        if not result:
            return None

        # Format time values for hours and minutes if > 60
        def format_time(minutes):
            if minutes > 60:
                hours = minutes // 60
                mins = minutes % 60
                return f"{int(hours)} h {int(mins)} m"
            return f"{int(minutes)} m"

        # Extract distance separately
        distance = f"{result[0] / 1000:.1f} km"

        # Organize data for compact presentation
        travel_times = [
            {"Mode": "Walking", "Type/Speed": "Average speed", "Time": format_time(result[1])},
            {"Mode": "Walking", "Type/Speed": "Slow speed", "Time": format_time(result[2])},
            {"Mode": "Cycling", "Type/Speed": "Average speed", "Time": format_time(result[3])},
            {"Mode": "Cycling", "Type/Speed": "Fast speed", "Time": format_time(result[4])},
            {"Mode": "Cycling", "Type/Speed": "Slow speed", "Time": format_time(result[5])},
            {"Mode": "Public Transport", "Type/Speed": "Rush hour (avg. walk)", "Time": format_time(result[6])},
            {"Mode": "Public Transport", "Type/Speed": "Rush hour (slow walk)", "Time": format_time(result[7])},
            {"Mode": "Public Transport", "Type/Speed": "Midday (avg. walk)", "Time": format_time(result[8])},
            {"Mode": "Public Transport", "Type/Speed": "Midday (slow walk)", "Time": format_time(result[9])},
            {"Mode": "Public Transport", "Type/Speed": "Night (avg. walk)", "Time": format_time(result[10])},
            {"Mode": "Public Transport", "Type/Speed": "Night (slow walk)", "Time": format_time(result[11])},
            {"Mode": "Car", "Type/Speed": "Rush hour", "Time": format_time(result[12])},
            {"Mode": "Car", "Type/Speed": "Midday", "Time": format_time(result[13])},
            {"Mode": "Car", "Type/Speed": "Night", "Time": format_time(result[14])}
        ]

        return distance, travel_times
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

    # Default zoom level
    zoom = 9.5
    if relayout_data:
        zoom = relayout_data.get('mapbox.zoom', zoom)

    # Handle no clicks
    if click_data is None:
        return create_map(zoom=zoom), "Click on two grid cells to query the database."

    try:
        clicked_id = int(click_data['points'][0]['hovertext'])
    except (KeyError, ValueError):
        return create_map(zoom=zoom), "Invalid click - no grid cell ID detected."

    # Get previously clicked IDs from the output
    if "Clicked IDs" in current_output:
        previous_clicks = [int(id) for id in current_output.split(": ")[1].split(", ")]
    else:
        previous_clicks = []

    # Add the new clicked ID
    previous_clicks.append(clicked_id)

    # Reset if more than two clicks are made
    if len(previous_clicks) > 2:
        current_queries = []
        previous_clicks = [clicked_id]

    # If exactly two IDs are clicked, query the database
    if len(previous_clicks) == 2:
        from_id = previous_clicks[0]
        to_id = previous_clicks[1]

        # Query the database
        result = query_db(from_id, to_id)

        if result:
            distance, travel_times = result
            result_message = html.Div([
                # Display distance
                html.Div([html.B("Walking distance: "), distance], style={"marginBottom": "10px"}),

                # Display table for travel times
                dash.dash_table.DataTable(
                    data=travel_times,
                    columns=[
                        {"name": "Mode", "id": "Mode"},
                        {"name": "Type/Speed", "id": "Type/Speed"},
                        {"name": "Time", "id": "Time"}
                    ],
                    style_table={'overflowX': 'auto', 'minWidth': '100%'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    }
                )
            ])

            current_queries = [from_id, to_id]  # Update current queries

        else:
            result_message = f"No data found for From ID: {from_id}, To ID: {to_id}"

        # Reset clicks
        previous_clicks = []

        # Return updated map and query results
        return create_map(queried_ids=current_queries, zoom=zoom), result_message

    # If only one ID is clicked, update the map with selected IDs
    output_message = f"Clicked IDs: {', '.join(map(str, previous_clicks))}"
    new_fig = create_map(selected_ids=previous_clicks, queried_ids=current_queries, zoom=zoom)
    return new_fig, output_message

