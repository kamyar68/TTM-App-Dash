import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px  # For color palette
from dash import dcc, html, Input, Output, State
from app import app
import sqlite3
from pathlib import Path

# Paths to data
db_path = 'data/full_csvs.db'
gridfile = 'data/Helsinki_Travel_Time_Matrix_2023_grid.gpkg'

# Ensure the download folder exists
download_folder = 'download_files_compare'
Path(download_folder).mkdir(parents=True, exist_ok=True)

# Load grid GeoDataFrame
grid_gdf_compare = gpd.read_file(gridfile)

if grid_gdf_compare.crs != 'EPSG:4326':
    grid_gdf_compare = grid_gdf_compare.to_crs('EPSG:4326')

# Map centroids for rendering
latitudes_compare = grid_gdf_compare.geometry.centroid.y
longitudes_compare = grid_gdf_compare.geometry.centroid.x
center_lat_compare = latitudes_compare.mean()
center_lon_compare = longitudes_compare.mean()

# Extended column descriptions for travel modes
column_descriptions_compare = {
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
    'car_n': 'Car (night)',
}

# Query database for related cells
def query_db_compare(column, threshold, clicked_id):
    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT to_id FROM full_DB 
        WHERE {column} <= ? AND from_id = ?
    """
    result = pd.read_sql(query, conn, params=(threshold, clicked_id))
    conn.close()
    return result['to_id'].tolist()

# Create map with multiple travel modes
def create_map_compare(selected_ids_dict={}, activated_id=None, zoom=9.5, center=None):
    fig = go.Figure()

    # Base grid
    fig.add_trace(
        go.Scattermapbox(
            lat=latitudes_compare,
            lon=longitudes_compare,
            mode='markers',
            marker=dict(size=10, color='blue', opacity=0.3),
            hoverinfo='text',
            hovertext=grid_gdf_compare['id'].astype(str),
            name='All Grid Cells'
        )
    )

    # Generate a distinct color for each travel mode
    color_palette = px.colors.qualitative.Safe
    mode_colors = {mode: color_palette[i % len(color_palette)] for i, mode in enumerate(selected_ids_dict.keys())}

    # Add highlighted cells for each travel mode
    for mode, ids in selected_ids_dict.items():
        selected_gdf = grid_gdf_compare[grid_gdf_compare['id'].isin(ids)]
        fig.add_trace(
            go.Scattermapbox(
                lat=selected_gdf.geometry.centroid.y,
                lon=selected_gdf.geometry.centroid.x,
                mode='markers',
                marker=dict(size=12, color=mode_colors[mode], opacity=0.8),
                hoverinfo='text',
                hovertext=[f"{mode} - ID: {id}" for id in selected_gdf['id']],
                name=mode
            )
        )

    # Highlight the activated cell
    if activated_id:
        activated_gdf = grid_gdf_compare[grid_gdf_compare['id'] == activated_id]
        fig.add_trace(
            go.Scattermapbox(
                lat=activated_gdf.geometry.centroid.y,
                lon=activated_gdf.geometry.centroid.x,
                mode='markers',
                marker=dict(size=15, color='black', opacity=0.9),
                hoverinfo='text',
                hovertext=f"Activated Cell - ID: {activated_id}",
                name='Activated Cell'
            )
        )

    # Configure the layout with updated legend
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=center or {"lat": center_lat_compare, "lon": center_lon_compare},
            zoom=zoom,
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=True,  # Ensure legend is visible
        legend=dict(
            x=0,  # Position the legend in the bottom-left
            y=1,
            bgcolor="rgba(255,255,255,0.8)",  # Transparent white background
            bordercolor="black",  # Add a border for clarity
            borderwidth=1,
        )
    )
    return fig

# Layout with checkboxes for multiple travel modes
compare_layout = html.Div([
    # Left panel with controls
    html.Div(id='compare-box', children=[
        html.H4("Compare Travel Modes"),
        html.P("Select travel modes to map multiple modes simultaneously."),
        dcc.Checklist(
            id='travel-modes-compare',
            options=[{'label': desc, 'value': col} for col, desc in column_descriptions_compare.items()],
            value=['walk_avg'],  # Default selected mode
            inline=False  # Vertical layout for better spacing
        ),
        html.Br(),
        html.H5("Threshold (minutes)"),
        dcc.Slider(
            id='threshold-slider-compare',
            min=5,
            max=60,
            step=5,
            value=15,  # Default threshold
            marks={i: str(i) for i in range(5, 65, 10)},
        ),
        html.Div(id='slider-value-compare', style={'marginTop': '10px', 'fontSize': '16px'}),
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

    # Right panel with the map
    html.Div([
        dcc.Graph(
            id='map-compare',
            figure=create_map_compare(),
            config={'scrollZoom': True},
            style={
                'height': '100%',  # Full height
                'width': '100%',   # Full width
                'overflow': 'hidden',  # Prevent overflowing
            }
        )
    ], style={
        'display': 'inline-block',
        'width': 'calc(100% - 300px)',
        'height': '100vh',
        'position': 'relative',
    })
], style={
    'display': 'flex',
    'flexDirection': 'row',
    'height': '100vh',
})

# Callback for map update
@app.callback(
    Output('map-compare', 'figure'),
    [Input('travel-modes-compare', 'value'),
     Input('threshold-slider-compare', 'value'),
     Input('map-compare', 'clickData')]
)
def update_map_compare(selected_modes, threshold, click_data):
    if not selected_modes:
        return create_map_compare()

    # Handle clicked cell
    activated_id = None
    if click_data:
        try:
            activated_id = int(click_data['points'][0]['hovertext'])
        except (KeyError, ValueError):
            pass

    # Query database for each mode
    selected_ids_dict = {
        mode: query_db_compare(mode, threshold, activated_id) if activated_id else []
        for mode in selected_modes
    }

    # Create updated map
    center = {"lat": center_lat_compare, "lon": center_lon_compare}
    if activated_id:
        center = {
            "lat": grid_gdf_compare.loc[grid_gdf_compare['id'] == activated_id].geometry.centroid.y.values[0],
            "lon": grid_gdf_compare.loc[grid_gdf_compare['id'] == activated_id].geometry.centroid.x.values[0],
        }
    return create_map_compare(selected_ids_dict=selected_ids_dict, activated_id=activated_id, center=center)
