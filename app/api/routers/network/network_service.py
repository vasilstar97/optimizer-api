import numpy as np
import geopandas as gpd
import shapely
from shapely.geometry import Point, LineString, MultiLineString, MultiPoint, box, MultiPolygon
from shapely.ops import unary_union, split
from loguru import logger
import pandas as pd
import random
import math
from math import atan2, degrees
import osmnx as ox
import momepy
import json
from ...utils import api_client, const

def _fetch_project_geometry(project_scenario_id : int, token : str):
    scenario_info = api_client.get_scenario_by_id(project_scenario_id, token)
    project_id = scenario_info['project']['project_id']
    project_info = api_client.get_project_by_id(project_id, token)
    project_geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(project_geometry_json)

def convert_to_crs(territory, epsg=32636):
    territory = territory.to_crs(epsg=epsg)
    return territory

def distance_to_centroid(row, territory_centroid):
    distance = row['centroid'].distance(territory_centroid)
    return distance

def convert_geodataframe(df, crs = 32636):
    gdf = gpd.GeoDataFrame(geometry=df, crs=crs)
    return gdf

def get_centroid(geometry):
    centroid = geometry.centroid.iloc[0]
    return centroid

def find_intersections(polygon, line):
    intersections = polygon.boundary.intersection(line)
    if intersections.geom_type == 'MultiPoint':
        return list(intersections.geoms)
    elif intersections.geom_type == 'Point':
        return [intersections]
    else:
        return []

def create_line_through_point(point, angle, length=10000):
    dx = length * np.cos(np.radians(angle))
    dy = length * np.sin(np.radians(angle))
    point1 = Point(point.x + dx, point.y + dy)
    point2 = Point(point.x - dx, point.y - dy)
    line = LineString([point1, point2])
    return line

def interpolate_points_on_line(line, t1, t2):
    point1 = line.interpolate(t1, normalized=True)
    point2 = line.interpolate(t2, normalized=True)
    return point1, point2

def split_lines(lines, epsg_projected=32636):
    new_lines = []
    for i, line in enumerate(lines.geometry):
        split_line = line
        for j, other_line in enumerate(lines.geometry):
            if split_line is not None and other_line is not None and i != j and split_line.intersects(other_line):
                split_result = split(split_line, other_line)
                if split_result is not None:
                    split_line = MultiLineString(split_result.geoms)

        if split_line is not None:
            if isinstance(split_line, LineString):
                new_lines.append(split_line)
            elif isinstance(split_line, MultiLineString):
                new_lines.extend(split_line.geoms)

    new_lines = gpd.GeoDataFrame(geometry=new_lines, crs=epsg_projected)
    return new_lines

def extend_single_line(line, distance=0.25):
    if len(line.coords) < 2:
        return line

    start = Point(line.coords[0])
    second = Point(line.coords[1])

    end = Point(line.coords[-1])
    penultimate = Point(line.coords[-2])

    dx_start = start.x - second.x
    dy_start = start.y - second.y
    length_start = math.hypot(dx_start, dy_start)
    if length_start == 0:
        new_start = start
    else:
        dx_start /= length_start
        dy_start /= length_start
        new_start = Point(start.x + dx_start * distance, start.y + dy_start * distance)

    dx_end = end.x - penultimate.x
    dy_end = end.y - penultimate.y
    length_end = math.hypot(dx_end, dy_end)
    if length_end == 0:
        new_end = end
    else:
        dx_end /= length_end
        dy_end /= length_end
        new_end = Point(end.x + dx_end * distance, end.y + dy_end * distance)

    new_coords = [ (new_start.x, new_start.y) ] + list(line.coords) + [ (new_end.x, new_end.y) ]
    return LineString(new_coords)

def extend_line_geometry(geometry, distance=0.25):
    if isinstance(geometry, LineString):
        return extend_single_line(geometry, distance)
    elif isinstance(geometry, MultiLineString):
        extended_lines = [extend_single_line(line, distance) for line in geometry]
        return MultiLineString(extended_lines)
    else:
        return geometry

def get_endpoints(line):
    return [Point(line.coords[0]), Point(line.coords[-1])]

def snap_endpoints(gdf, tolerance=0.2):
    endpoints = []
    for line in gdf.geometry:
        endpoints.extend(get_endpoints(line))

    endpoints_gs = gpd.GeoSeries(endpoints)

    merged_points = []
    used = set()

    for i, point1 in enumerate(endpoints_gs):
        if i in used:
            continue

        close_points = [point1]
        for j, point2 in enumerate(endpoints_gs):
            if i != j and j not in used and point1.distance(point2) <= tolerance:
                close_points.append(point2)
                used.add(j)

        centroid = unary_union(close_points).centroid
        merged_points.append(centroid)

    new_geometries = []

    for line in gdf.geometry:
        coords = list(line.coords)
        new_coords = []

        for coord in coords:
            point = Point(coord)
            for merged_point in merged_points:
                if point.distance(merged_point) <= tolerance:
                    point = merged_point
                    break
            new_coords.append((point.x, point.y))

        new_line = LineString(new_coords)
        new_geometries.append(new_line)

    gdf['geometry'] = new_geometries
    return gdf

def calculate_angle(line1, line2):
    def direction_vector(line):
        x_diff = line.coords[-1][0] - line.coords[0][0]
        y_diff = line.coords[-1][1] - line.coords[0][1]
        return np.array([x_diff, y_diff])

    v1 = direction_vector(line1)
    v2 = direction_vector(line2)

    angle_rad = atan2(np.linalg.det([v1, v2]), np.dot(v1, v2))
    angle_deg = abs(degrees(angle_rad))
    return min(angle_deg, 360 - angle_deg)

def process_geospatial_data(new_gd, split_territory, buffer_distance=3, target_crs=32636):
    split_territory = convert_to_crs(split_territory)
    new_gd = convert_to_crs(new_gd)

    points = new_gd.centroid
    points_gdf = gpd.GeoDataFrame(geometry=points, crs=target_crs)

    buffered_blocks = split_territory.copy()
    buffered_blocks['geometry'] = buffered_blocks['geometry'].buffer(distance=buffer_distance)

    result_gdf = gpd.GeoDataFrame(columns=['block_id', 'point_id', 'geometry'])

    for block_id, block in buffered_blocks.iterrows():
        for point_id, point in points_gdf.iterrows():
            if block['geometry'].contains(point['geometry']):
                centroid = block['geometry'].centroid
                line = MultiPoint([point['geometry'], centroid]).convex_hull
                result_gdf = pd.concat([result_gdf, pd.DataFrame({
                    'block_id': [block_id],
                    'point_id': [point_id],
                    'geometry': [line]
                })], ignore_index=True)

    result_gdf = result_gdf[['block_id', 'geometry']]
    result_gdf.crs = target_crs

    split_territory['centroid'] = split_territory.geometry.centroid

    new_lines = []
    for poly_idx, polygon in split_territory.iterrows():
        centroid = polygon['centroid']
        intersecting_lines = result_gdf[result_gdf.intersects(polygon.geometry)]

        for line_idx, line in intersecting_lines.iterrows():
            if not line.geometry.is_empty:
                coords = list(line.geometry.coords)
                coords[-1] = (centroid.x, centroid.y)
                new_line = LineString(coords)
                new_lines.append(new_line)

    final_result_gdf = gpd.GeoDataFrame(new_lines, columns=['geometry'])
    final_result_gdf.crs = target_crs

    return final_result_gdf

def split_territory_by_buffer(territory, new_gd, buffer_distance=2):
    territory = convert_to_crs(territory)
    new_gd = convert_to_crs(new_gd)
    buffered_lines = new_gd.buffer(buffer_distance)

    merged_polygon = buffered_lines.unary_union
    split_territory = territory.overlay(
        gpd.GeoDataFrame(geometry=[merged_polygon], crs=territory.crs),
        how='difference'
    )

    split_territory = split_territory.explode(index_parts=False)

    return split_territory

def process_geodataframes(result_1, result_2):
    result_1 = convert_to_crs(result_1)
    result_2 = convert_to_crs(result_2)
    combined_gdf = pd.concat([result_1, result_2], ignore_index=True)
    combined_gdf['geometry'] = combined_gdf['geometry'].apply(lambda geom: extend_line_geometry(geom, distance=0.25))
    combined_gdf = split_lines(combined_gdf)
    combined_gdf['length'] = combined_gdf.length
    combined_gdf = combined_gdf[combined_gdf['length'] >= 1.5]
    return snap_endpoints(combined_gdf)

def process_geodata(territory, result_gdf, split_territory, buffer_distance=1, epsg_final=32636):
    territory = convert_to_crs(territory)
    result_gdf = convert_to_crs(result_gdf)
    split_territory = convert_to_crs(split_territory)

    boundary = territory.boundary
    buffered_boundary = boundary.buffer(buffer_distance)

    intersecting_polygons = split_territory[split_territory.intersects(buffered_boundary.unary_union)]
    lines_within_polygons = result_gdf[result_gdf.intersects(intersecting_polygons.unary_union)]

    indices_to_remove = lines_within_polygons.index
    result_gdf = result_gdf.drop(indices_to_remove)

    projected_polygons = convert_to_crs(intersecting_polygons)
    projected_lines = convert_to_crs(lines_within_polygons)

    result_lines = gpd.GeoDataFrame(columns=projected_lines.columns, crs=projected_lines.crs)

    for _, polygon in projected_polygons.iterrows():
        lines_within_polygon = projected_lines[projected_lines.intersects(polygon.geometry)]

        if len(lines_within_polygon) < 2:
            continue

        lines_within_polygon = lines_within_polygon.copy()
        lines_within_polygon['length'] = lines_within_polygon.length

        sorted_lines = lines_within_polygon.sort_values(by='length', ascending=False)
        max_min_angle = 0
        best_pair = None

        for i in range(len(sorted_lines) - 1):
            for j in range(i + 1, len(sorted_lines)):
                line1 = sorted_lines.iloc[i].geometry
                line2 = sorted_lines.iloc[j].geometry

                angle = calculate_angle(line1, line2)

                if angle > max_min_angle:
                    max_min_angle = angle
                    best_pair = (sorted_lines.iloc[i], sorted_lines.iloc[j])

        if best_pair:
            result_lines = pd.concat([result_lines, pd.DataFrame([best_pair[0], best_pair[1]]).drop(columns='length')], ignore_index=True)

    result_lines = result_lines.drop(columns='length', errors='ignore')
    result_lines = result_lines.set_crs(epsg=epsg_final)

    return result_gdf, result_lines, intersecting_polygons

def find_intersections_and_create_lines(combined_gdf, intersecting_polygons):
    intersection_points = []

    for i in range(len(combined_gdf)):
        for j in range(i + 1, len(combined_gdf)):
            line1 = combined_gdf.geometry.iloc[i]
            line2 = combined_gdf.geometry.iloc[j]

            if line1.intersects(line2):
                intersection = line1.intersection(line2)

                if isinstance(intersection, Point):
                    intersection_points.append(intersection)
                elif intersection.geom_type == 'MultiPoint':
                    intersection_points.extend([point for point in intersection])

    intersections_gdf = gpd.GeoDataFrame(geometry=intersection_points, crs=combined_gdf.crs)

    intersecting_polygons_copy = intersecting_polygons.copy()
    intersecting_polygons_copy['centroid'] = intersecting_polygons_copy.geometry.centroid

    lines_to_centroids = []

    for idx, polygon in intersecting_polygons_copy.iterrows():
        centroid = polygon['centroid']

        nearest_point = intersections_gdf.distance(centroid).idxmin()
        nearest_point_geom = intersections_gdf.geometry.iloc[nearest_point]

        line = LineString([nearest_point_geom, centroid])
        lines_to_centroids.append(line)

    lines_gdf = gpd.GeoDataFrame(geometry=lines_to_centroids, crs=intersections_gdf.crs)

    return lines_gdf

def select_central_polygons(territory, split_territory):
    territory_centroid = territory.geometry.centroid.iloc[0]

    split_territory['centroid'] = split_territory.geometry.centroid
    split_territory['distance'] = split_territory.apply(lambda row: distance_to_centroid(row, territory_centroid), axis=1)
    split_sorted = split_territory.sort_values('distance')

    total_polygons = len(split_sorted)
    lower_bound = int(total_polygons * 0.01)
    upper_bound = int(total_polygons * 0.35)

    num_to_select = np.random.randint(lower_bound, upper_bound + 1)

    central_polygons = split_sorted.head(num_to_select)
    central_gdf = gpd.GeoDataFrame(central_polygons, geometry='geometry')

    return central_gdf

def split_polygon_grid(polygon, num_parts, crs_final = 32636):
    if num_parts == 1:
      return gpd.GeoDataFrame(geometry=[polygon], crs=crs_final)

    minx, miny, maxx, maxy = polygon.bounds
    total_width = maxx - minx
    total_height = maxy - miny

    cols = int(np.ceil(np.sqrt(num_parts)))
    rows = int(np.ceil(num_parts / cols))

    cell_width = total_width / cols
    cell_height = total_height / rows

    split_polygons = []

    for i in range(cols):
        for j in range(rows):
            cell = box(minx + i * cell_width, miny + j * cell_height,
                       minx + (i + 1) * cell_width, miny + (j + 1) * cell_height)

            intersection = polygon.intersection(cell)

            if not intersection.is_empty:
                if isinstance(intersection, MultiPolygon):
                    split_polygons.extend([p for p in intersection.geoms])
                else:
                    split_polygons.append(intersection)

    split_polygons = convert_geodataframe(split_polygons)

    return split_polygons

def calculate_num_parts(territory, area_per_part=10000000):
    territory = convert_to_crs(territory)
    polygon = territory.geometry[0]
    area = polygon.area
    num_parts = int(np.floor(area / area_per_part)) + 1

    return polygon, num_parts

def midpoint(geometry):
    if geometry.geom_type == 'LineString':
        return geometry.interpolate(0.5, normalized=True)
    elif geometry.geom_type == 'MultiLineString':
        longest_line = max(geometry, key=lambda line: line.length)
        return longest_line.interpolate(0.5, normalized=True)
    else:
        return None

def find_intersecting_centroid(line, polygons):
    intersecting = polygons[polygons.intersects(line)]
    if not intersecting.empty:
        return intersecting.iloc[0].centroid
    return None

def create_line(midpoint, centroid):
    if midpoint is not None and centroid is not None:
        return LineString([midpoint, centroid])
    return None

def process_territory_graph(territory, combined_gdf, intersecting_polygons):
    territory_boundary = territory.boundary
    territory_boundary = convert_geodataframe(territory_boundary)
    graph = process_geodataframes(territory_boundary, combined_gdf)
    buffered_boundary = territory_boundary.buffer(0.5)
    buffered_boundary = convert_geodataframe(buffered_boundary)
    lines_within_buffer = gpd.sjoin(graph, buffered_boundary, how="inner", predicate="within")
    lines_within_buffer['midpoint'] = lines_within_buffer['geometry'].apply(midpoint)
    intersecting_polygons['centroid'] = intersecting_polygons.centroid
    lines_within_buffer['centroid'] = lines_within_buffer['geometry'].apply(
        lambda x: find_intersecting_centroid(x, intersecting_polygons))
    lines_within_buffer['geometry'] = lines_within_buffer.apply(
        lambda row: create_line(row['midpoint'], row['centroid']), axis=1)
    lines_within_buffer = lines_within_buffer['geometry']
    lines_within_buffer = convert_geodataframe(lines_within_buffer)
    graph = pd.concat([combined_gdf, lines_within_buffer], ignore_index=True)

    return graph

def process_territory(territory_big, final_result):
    territory_big = convert_to_crs(territory_big)
    territory_big_boundary = territory_big.boundary
    territory_big_boundary = convert_geodataframe(territory_big_boundary)
    final = process_geodataframes(territory_big_boundary, final_result)

    return final

def get_connected_and_unconnected_lines(gdf, buffer_distance=0.1):
    connected_lines = []
    unconnected_lines = []

    for idx, line in gdf.iterrows():
        geom = line.geometry

        if isinstance(geom, LineString):
            start_buffer = Point(geom.coords[0]).buffer(buffer_distance)
            end_buffer = Point(geom.coords[-1]).buffer(buffer_distance)

            start_intersects = not gdf[(gdf.geometry.intersects(start_buffer)) & (gdf.index != idx)].empty
            end_intersects = not gdf[(gdf.geometry.intersects(end_buffer)) & (gdf.index != idx)].empty

            if start_intersects and end_intersects:
                connected_lines.append(line)
            elif start_intersects != end_intersects:
                unconnected_lines.append(line)

    connected_lines_gdf = gpd.GeoDataFrame(connected_lines, columns=gdf.columns)
    unconnected_lines_gdf = gpd.GeoDataFrame(unconnected_lines, columns=gdf.columns)
    unconnected = snap_endpoints(unconnected_lines_gdf, tolerance=100)
    line_final = pd.concat([connected_lines_gdf, unconnected], ignore_index=True)

    return line_final

def calculate_global_integration(line_gdf):
    dual = momepy.gdf_to_nx(line_gdf, approach='dual')
    global_integration = momepy.closeness_centrality(dual, name='global_integration', verbose=True)
    integration_gdf = momepy.nx_to_gdf(global_integration, points=False)
    integration_gdf = integration_gdf.set_crs('32636')

    return integration_gdf

def process_features(territory, crs=4326):
    territory = territory.to_crs(crs)
    territory_polygon = territory.geometry.unary_union

    water = ox.features.features_from_polygon(territory_polygon, tags={'natural': 'water'})
    water_gdf = gpd.GeoDataFrame(water, geometry='geometry')

    roads = ox.features.features_from_polygon(territory_polygon, tags={'highway': True})
    roads_gdf = gpd.GeoDataFrame(roads, geometry='geometry')

    for column in water_gdf.columns:
        if water_gdf[column].dtype == 'object':
            water_gdf[column] = water_gdf[column].apply(lambda x: str(x) if isinstance(x, list) else x)

    for column in roads_gdf.columns:
        if roads_gdf[column].dtype == 'object':
            roads_gdf[column] = roads_gdf[column].apply(lambda x: str(x) if isinstance(x, list) else x)

    water_gdf = convert_to_crs(water_gdf)
    roads_gdf = convert_to_crs(roads_gdf)

    return water_gdf, roads_gdf

def generation(territory):
    territory = convert_to_crs(territory)
    center = get_centroid(territory.geometry)

    main_angle = random.uniform(-45, 45)
    main_line = create_line_through_point(center, angle=main_angle)
    main_intersections = find_intersections(territory.geometry.iloc[0], main_line)
    main_line = LineString([main_intersections[0], main_intersections[1]])

    t1 = random.uniform(0.2, 0.4)
    t2 = random.uniform(0.5, 0.8)

    point1, point2 = interpolate_points_on_line(main_line, t1, t2)

    while True:
        secondary_angle1 = main_angle + random.uniform(-95, -90)
        secondary_angle2 = main_angle + random.uniform(-95, -90)

        secondary_line1 = create_line_through_point(point1, angle=secondary_angle1)
        secondary_line2 = create_line_through_point(point2, angle=secondary_angle2)

        secondary_intersections1 = find_intersections(territory.geometry.iloc[0], secondary_line1)
        secondary_intersections2 = find_intersections(territory.geometry.iloc[0], secondary_line2)

        secondary_line1 = LineString([secondary_intersections1[0], secondary_intersections1[1]])
        secondary_line2 = LineString([secondary_intersections2[0], secondary_intersections2[1]])

        if not secondary_line1.intersects(secondary_line2):
            break
        else:
            print("Второстепенные линии пересекаются, перегенерация...")

    lines = gpd.GeoDataFrame(geometry=[main_line, secondary_line1, secondary_line2])
    new_gdf = split_lines(lines)
    new_gdf = new_gdf.set_crs('32636')

    return new_gdf, territory

def generate_network(project_scenario_id : int, token : str):

    logger.info('Fetching project geometry')
    project_geometry = _fetch_project_geometry(project_scenario_id, token)
    project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=const.DEFAULT_CRS)
    project, num_parts = calculate_num_parts(project_gdf)
    project = split_polygon_grid(project, num_parts)

    results = []

    for _, poly in project.iterrows():
        single_poly = gpd.GeoDataFrame([poly], geometry='geometry', crs=project.crs)

        street_center, single_poly = generation(single_poly)
        blocks_one = split_territory_by_buffer(single_poly, street_center)

        street_ring_center = process_geospatial_data(street_center, blocks_one)
        blocks_two = split_territory_by_buffer(blocks_one, street_ring_center)

        combined_street_one = process_geodataframes(street_ring_center, street_center)
        street_precenter = process_geospatial_data(combined_street_one, blocks_two)

        result_gdf, result_lines, intersecting_polygons = process_geodata(single_poly, street_precenter, blocks_two)
        lines_gdf = find_intersections_and_create_lines(combined_street_one, intersecting_polygons)

        combined = pd.concat([result_lines, result_gdf, lines_gdf], ignore_index=True)
        combined_gdf = process_geodataframes(combined_street_one, combined)

        split_territory = split_territory_by_buffer(single_poly, combined_gdf)
        central_gdf = select_central_polygons(single_poly, split_territory)

        result_gdf = process_geospatial_data(combined_gdf, central_gdf)
        combined_gdf = process_geodataframes(combined_gdf, result_gdf)

        combined_gdf = process_territory_graph(single_poly, combined_gdf, intersecting_polygons)
        results.append(combined_gdf)

    final_result = gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=project.crs)
    final_result = process_territory(project_gdf, final_result)
    line_final = get_connected_and_unconnected_lines(final_result)
    line_integration = calculate_global_integration(line_final)
    # blocks_final = split_territory_by_buffer(project_gdf, line_integration)
    return line_integration
    # blocks_final.to_file('final_blocks.geojson')