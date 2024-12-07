import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State
from app import app  # Import the app instance from app.py
import sqlite3
import os
from geopy.geocoders import Nominatim
from shapely.geometry import Point
from datetime import datetime, timedelta
from pathlib import Path
import time  # For debugging execution time

# Path to database and other data files
db_path = 'data/full_csvs.db'
gridfile = 'data/Helsinki_Travel_Time_Matrix_2023_grid.gpkg'
csv_folder = 'data/Helsinki_Travel_Time_Matrix_2023'
download_folder = 'download_files'  # Folder for download files
population_csv = 'data/pop.csv'  # Population data file

# Ensure the download folder exists
Path(download_folder).mkdir(parents=True, exist_ok=True)

# Initialize geolocator
geolocator = Nominatim(user_agent="Helsinki_TTM_App")

# Load the grid geodataframe
grid_gdf = gpd.read_file(gridfile)

# Ensure the CRS is set to EPSG:3067 and project to WGS84 (EPSG:4326) for mapping
if grid_gdf.crs is None or grid_gdf.crs != 'EPSG:3067':
    grid_gdf = grid_gdf.to_crs('EPSG:3067')
grid_gdf = grid_gdf[grid_gdf.is_valid]
grid_gdf = grid_gdf.to_crs(epsg=4326)

# Pre-calculate centroid coordinates and the center of the map
latitudes = grid_gdf.geometry.centroid.y
longitudes = grid_gdf.geometry.centroid.x
center_lat = latitudes.mean()
center_lon = longitudes.mean()

# Define the columns and short descriptions
column_descriptions = {
    'walk_avg': 'Walking (average speed)',
    'walk_slo': 'Walking (slow speed)',
    'bike_avg': 'Cycling (average speed)',
    'bike_fst': 'Cycling (fast speed)',
    'bike_slo': 'Cycling (slow speed)',
    'pt_r_avg': 'Public transport (rush hour, average walk)',
    'pt_r_slo': 'Public transport (rush hour, slow walk)',
    'pt_m_avg': 'Public transport (midday, average walk)',
    'pt_m_slo': 'Public transport (midday, slow walk)',
    'pt_n_avg': 'Public transport (night, average walk)',
    'pt_n_slo': 'Public transport (night, slow walk)',
    'car_r': 'Car (rush hour)',
    'car_m': 'Car (midday)',
    'car_n': 'Car (night)'
}

# Load population data
print("[DEBUG] Loading population data...")
start_time = time.time()
population_df = pd.read_csv(population_csv)
print(f"[DEBUG] Population data loaded in {time.time() - start_time:.2f} seconds")

# Function to query the database based on column and threshold
def query_db(column, threshold, clicked_id):
    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT to_id FROM full_DB 
        WHERE {column} <= ? AND from_id = ?
    """
    related_ids = pd.read_sql(query, conn, params=(threshold, clicked_id))['to_id'].tolist()
    conn.close()
    return related_ids

# Function to calculate the total population in highlighted cells
def calculate_population(related_ids):
    print("[DEBUG] Calculating population...")
    start_time = time.time()
    if population_df.empty:
        print("[DEBUG] Population DataFrame is empty.")
        return 0
    relevant_pop = population_df[population_df['id'].isin(related_ids)]
    total_population = relevant_pop['ASUKKAITA'].sum()
    print(f"[DEBUG] Population calculation completed in {time.time() - start_time:.2f} seconds")
    return total_population

# Function to create the GeoPackage of highlighted cells
def create_gpkg(clicked_id, related_ids, dataset_value):
    # Filter the grid GeoDataFrame to only include the related IDs
    highlighted_gdf = grid_gdf[grid_gdf['id'].isin(related_ids)]
    print(highlighted_gdf.head())

    if highlighted_gdf.empty:
        print("Error: No matching rows found in grid_gdf for related_ids.")
        return None  # Skip creating an empty file


    travel_time_df = pd.read_csv(f"data/Helsinki_Travel_Time_Matrix_2023/Helsinki_Travel_Time_Matrix_2023_travel_times_to_{clicked_id}.csv")
    print(travel_time_df.head())


    if travel_time_df.empty:
        print("Error: No travel time data found for clicked_id.")
        return None

    # Ensure columns align for the merge
    if 'id' not in highlighted_gdf.columns:
        print("Error: 'id' column not found in grid_gdf.")
        return None
    if 'to_id' not in travel_time_df.columns:
        print("Error: 'to_id' column not found in travel_time_df.")
        return None

    # Merge the travel time data with the GeoDataFrame
    highlighted_gdf = highlighted_gdf.merge(travel_time_df, left_on='id', right_on='from_id')

    if highlighted_gdf.empty:
        print("Error: Merge resulted in an empty GeoDataFrame.")
        return None

    # Validate geometries
    if not highlighted_gdf.is_valid.all():
        print("Error: Invalid geometries detected. Cleaning geometries.")
        highlighted_gdf = highlighted_gdf[highlighted_gdf.is_valid]

    # Define the output file path
    gpkg_filename = f'{download_folder}/highlighted_cells_{clicked_id}.gpkg'

    # Save the GeoDataFrame to a GeoPackage
    try:
        highlighted_gdf.to_file(gpkg_filename, driver="GPKG")
    except Exception as e:
        print(f"Error saving GeoPackage: {e}")
        return None

    print(f"GeoPackage successfully created: {gpkg_filename}")
    return gpkg_filename


# Function to delete files older than 7 days
def delete_old_files(folder, days=7):
    now = datetime.now()
    cutoff = now - timedelta(days=days)

    for file in Path(folder).glob('*'):
        if file.is_file() and datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink()


# Function to create the scatter map
def create_map(selected_ids=[], activated_id=None, zoom=9.5, center=None):
    fig = go.Figure()

    # Base scatter plot for all grid cells
    fig.add_trace(
        go.Scattermapbox(
            lat=latitudes,
            lon=longitudes,
            mode='markers',
            marker=dict(size=22, color='blue', opacity=0.2),
            hoverinfo='text',
            hovertext=grid_gdf['id'],
            name='All Cells'
        )
    )

    # Highlight reachable cells
    if selected_ids:
        highlighted_gdf = grid_gdf[grid_gdf['id'].isin(selected_ids) & (grid_gdf['id'] != activated_id)]
        fig.add_trace(
            go.Scattermapbox(
                lat=highlighted_gdf.geometry.centroid.y,
                lon=highlighted_gdf.geometry.centroid.x,
                mode='markers',
                marker=dict(size=22, color='red', opacity=0.3),
                hoverinfo='text',
                hovertext=highlighted_gdf['id'],
                name='Highlighted Cells'
            )
        )

    # Highlight the activated cell
    if activated_id:
        activated_gdf = grid_gdf[grid_gdf['id'] == activated_id]
        fig.add_trace(
            go.Scattermapbox(
                lat=activated_gdf.geometry.centroid.y,
                lon=activated_gdf.geometry.centroid.x,
                mode='markers',
                marker=dict(size=22, color='green', opacity=0.8),
                hoverinfo='text',
                hovertext=activated_gdf['id'],
                name='Activated Cell'
            )
        )

    if center is None:
        center = dict(lat=center_lat, lon=center_lon)

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            zoom=zoom,
            center=center
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False
    )

    return fig

# Define layout for this page with a vertical box on the left and map on the right
scatterplot_layout = html.Div([
    html.Div(id='floating-box', children=[
        html.H4("Travel Time Matrix"),
        html.P(id='floating-box-content', children="Click on a grid cell to view data."),
        dcc.Download(id="download-datafile"),

        # Search for cell by ID
        html.Br(),
        html.H5("Search Cell by ID"),
        dcc.Input(id='cell-id-input', type='number', placeholder='Enter cell ID'),
        html.Button('Search', id='cell-id-search', n_clicks=0),
        html.Br(), html.Br(),

        # Address search
        html.H5("Search by Address"),
        dcc.Input(id='address-input', type='text', placeholder='Enter address', n_submit=0),
        html.Button('Search Address', id='address-search-btn', n_clicks=0),
        html.Div(id='address-error', style={'color': 'red', 'marginTop': '10px'}),
        html.Br(), html.Br(),

        # Dropdown for dataset selection with short descriptions
        html.Hr(),
        html.H5("Travel Mode"),
        dcc.Dropdown(
            id='dataset-selector',
            options=[{'label': f"{desc}", 'value': col} for col, desc in column_descriptions.items()],
            value='walk_avg',  # Default to 'walk_avg'
            clearable=False
        ),
        html.Br(),
        # Slider for threshold selection
        html.H5("Threshold (minutes)"),
        dcc.Slider(
            id='threshold-slider',
            min=5,
            max=120,
            step=1,
            value=20,  # Default threshold value
            marks={i: str(i) for i in range(5, 121, 15)}
        ),

        # Div to display the current slider value
        html.Div(id='slider-value', style={'margin-top': '10px', 'font-size': '16px'}),

        html.Br(),
        html.Hr(),
        html.H5("Download GPKG file"),
        html.A("Download Helsinki Travel Time Matrix Grid",
               href='/download/Helsinki_Travel_Time_Matrix_2023_grid.gpkg',
               download='Helsinki_Travel_Time_Matrix_2023_grid.gpkg',
               style={'textDecoration': 'none', 'color': 'blue', 'fontSize': '16px'})
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
            id='scatterplot-map',
            figure=create_map(),
            config={'scrollZoom': True},
            style={'height': '100vh', 'width': '100%', 'flexGrow': '1'}
        )
    ], style={'display': 'inline-block', 'width': 'calc(100% - 300px)', 'height': '100vh'})
], style={'display': 'flex', 'flexDirection': 'row', 'height': '100vh'})


# Callback
@app.callback(
    [Output('scatterplot-map', 'figure'),
     Output('floating-box-content', 'children'),
     Output('slider-value', 'children'),
     Output('address-error', 'children')],
    [Input('scatterplot-map', 'clickData'),
     Input('dataset-selector', 'value'),
     Input('threshold-slider', 'value'),
     Input('cell-id-search', 'n_clicks'),
     Input('address-search-btn', 'n_clicks'),
     Input('address-input', 'n_submit')],
    [State('scatterplot-map', 'relayoutData'),
     State('cell-id-input', 'value'),
     State('address-input', 'value')]
)
def update_map(click_data, dataset_value, threshold, n_clicks_id, n_clicks_addr, n_submit, relayout_data, cell_id,
               address):
    zoom = 9.5
    center = None
    error_msg = ""

    if relayout_data:
        zoom = relayout_data.get('mapbox.zoom', 9.5)
        center = relayout_data.get('mapbox.center', None)

    # Handle address search (button click or Enter key press)
    if (n_clicks_addr > 0 or n_submit > 0) and address:
        try:
            location = geolocator.geocode(address)
            if location:
                address_point = gpd.GeoSeries([Point(location.longitude, location.latitude)], crs="EPSG:4326")
                address_point_projected = address_point.to_crs(grid_gdf.crs)
                containing_grid = grid_gdf[grid_gdf.geometry.contains(address_point_projected.iloc[0])]

                if not containing_grid.empty:
                    clicked_id = containing_grid.iloc[0]['id']
                    click_data = {'points': [{'hovertext': clicked_id}]}
                else:
                    error_msg = "Address does not fall within any grid cell."
            else:
                error_msg = "Address not found. Try a different query."
        except Exception as e:
            error_msg = f"Error: {str(e)}"

    # Handle cell ID search or simulated click
    if n_clicks_id > 0 and cell_id is not None:
        clicked_id = cell_id
    elif click_data:
        try:
            clicked_id = int(click_data['points'][0]['hovertext'])
        except (KeyError, ValueError):
            return create_map(zoom=zoom,
                              center=center), "Invalid click - no grid cell ID detected.", f"Threshold: {threshold} min", error_msg
    else:
        return create_map(zoom=zoom,
                          center=center), "Click on a grid cell or type in the cell id below to map how far you can reach.", f"Threshold: {threshold} min", error_msg

    # Delete old files from the download folder
    delete_old_files(download_folder)

    # Query database for related IDs
    related_ids = query_db(dataset_value, threshold, clicked_id)
    center = {'lat': grid_gdf.loc[grid_gdf['id'] == clicked_id].geometry.centroid.y.values[0],
              'lon': grid_gdf.loc[grid_gdf['id'] == clicked_id].geometry.centroid.x.values[0]}
    new_fig = create_map(selected_ids=related_ids, activated_id=clicked_id, zoom=zoom, center=center)

    # Create GeoPackage file
    gpkg_filepath = create_gpkg(clicked_id, related_ids, dataset_value)
    gpkg_filename = os.path.basename(gpkg_filepath)

    # CSV download logic
    csv_filename = f'{download_folder}/Helsinki_Travel_Time_Matrix_2023_travel_times_to_{clicked_id}.csv'
    area_km2 = round(len(related_ids) * 62500 / 1000000, 2)

    # Generate floating box content
    floating_box_content = html.Div([
        f"Clicked Cell ID: {clicked_id}",
        html.Br(), html.Br(),
        html.B(f"{len(related_ids)}"),
        f" cells can be reached within {threshold} minutes using '{dataset_value}'. This is equivalent to an approximate area of ",
        html.B(f"{area_km2} km²."),
        html.Br(), html.Br(),
        html.A("Download CSV", href=f'/{csv_filename}',
               download=f'Helsinki_Travel_Time_Matrix_2023_travel_times_to_{clicked_id}.csv'),
        html.Br(), html.Br(),
        html.A("Download GPKG", href=f'/{gpkg_filename}', download=gpkg_filename)
    ])

    return new_fig, floating_box_content, f"Threshold: {threshold} min", error_msg