import numpy as np
import geopandas as gpd
import shapely
from shapely.geometry import Point, LineString, MultiLineString, MultiPoint, box, MultiPolygon
from loguru import logger
from shapely.ops import split
import pandas as pd
import random
import math
import json
from ...utils import api_client, const

AREA_PER_PART = 10_000_000
MAIN_ANGLE_MIN = -45
MAIN_ANGLE_MAX = 45
SECONDARY_ANGLE_MIN = 85
SECONDARY_ANGLE_MAX = 95

def _fetch_project_geometry(project_scenario_id : int, token : str):
    scenario_info = api_client.get_scenario_by_id(project_scenario_id, token)
    project_id = scenario_info['project']['project_id']
    project_info = api_client.get_project_by_id(project_id, token)
    project_geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(project_geometry_json)

def _calculate_num_parts(polygon : shapely.Polygon, area_per_part=AREA_PER_PART) -> int:
  area = polygon.area
  num_parts = int(np.floor(area / area_per_part)) + 1
  return num_parts

def _polygon_to_parts(polygon : shapely.Polygon, num_parts : int, crs) -> gpd.GeoDataFrame:

  if num_parts == 1:
    return gpd.GeoDataFrame(geometry=[polygon], crs=crs)

  minx, miny, maxx, maxy = polygon.bounds
  total_width = maxx - minx
  total_height = maxy - miny

  cols = int(np.ceil(np.sqrt(num_parts)))
  rows = int(np.ceil(num_parts / cols))

  cell_width = total_width / cols
  cell_height = total_height / rows

  polygons = []

  for i in range(cols):
    for j in range(rows):
      cell = shapely.box(minx + i * cell_width, miny + j * cell_height,
                  minx + (i + 1) * cell_width, miny + (j + 1) * cell_height)

      intersection = polygon.intersection(cell)

      if not intersection.is_empty:
        if isinstance(intersection, shapely.MultiPolygon):
          polygons.extend([p for p in intersection.geoms])
        else:
          polygons.append(intersection)

  
  polygons_gdf = gpd.GeoDataFrame(geometry=polygons, crs=crs)

  return polygons_gdf

def _create_line_through_point(point : shapely.Point, angle : float, length : int = 100_000) -> shapely.LineString:
    dx = length * np.cos(np.radians(angle))
    dy = length * np.sin(np.radians(angle))
    point_a = shapely.Point(point.x + dx, point.y + dy)
    point_b = shapely.Point(point.x - dx, point.y - dy)
    line = shapely.LineString([point_a, point_b])
    return line

def _interpolate_points_on_line(line : shapely.LineString, t1 : float, t2 : float) -> tuple[shapely.Point, shapely.Point]:
    point1 = line.interpolate(t1, normalized=True)
    point2 = line.interpolate(t2, normalized=True)
    return point1, point2

def _split_lines(lines_gdf: gpd.GeoDataFrame):
    new_lines = []
    for i, line in enumerate(lines_gdf.geometry):
        split_line = line
        for j, other_line in enumerate(lines_gdf.geometry):
            if split_line is not None and other_line is not None and i != j:
                # Проверка на пересечение (не просто касание)
                if split_line.intersects(other_line) and not split_line.touches(other_line):
                    try:
                        split_result = split(split_line, other_line)
                        if split_result is not None:
                            split_line = shapely.MultiLineString(split_result.geoms)
                    except ValueError as e:
                        print(f"Error splitting lines {i} and {j}: {e}")
                        continue

        if split_line is not None:
            if isinstance(split_line, shapely.LineString):
                new_lines.append(split_line)
            elif isinstance(split_line, shapely.MultiLineString):
                new_lines.extend(split_line.geoms)

    # Создание нового GeoDataFrame
    new_lines = gpd.GeoDataFrame(geometry=new_lines, crs=lines_gdf.crs)
    return new_lines


def _generate_streets(gdf : gpd.GeoDataFrame):

  geometry = gdf.iloc[0].geometry
  center = geometry.centroid

  main_angle = random.uniform(MAIN_ANGLE_MIN, MAIN_ANGLE_MAX)
  main_line = _create_line_through_point(center, angle=main_angle)
  main_line = main_line.intersection(geometry)

  t1 = random.uniform(0.2, 0.4)
  t2 = random.uniform(0.5, 0.8)

  point1, point2 = _interpolate_points_on_line(main_line, t1, t2)

  while True:
    
      secondary_angle_1 = main_angle + random.uniform(SECONDARY_ANGLE_MIN, SECONDARY_ANGLE_MAX)
      secondary_angle_2 = main_angle + random.uniform(SECONDARY_ANGLE_MIN, SECONDARY_ANGLE_MAX)

      secondary_line_1 = _create_line_through_point(point1, angle=secondary_angle_1)
      secondary_line_2 = _create_line_through_point(point2, angle=secondary_angle_2)

      secondary_line_1 = secondary_line_1.intersection(geometry)
      secondary_line_2 = secondary_line_2.intersection(geometry)

      if not secondary_line_1.intersects(secondary_line_2):
          break

  lines_gdf = gpd.GeoDataFrame(geometry=[main_line, secondary_line_1, secondary_line_2], crs=gdf.crs)
  splitted_lines_gdf = _split_lines(lines_gdf)

  return splitted_lines_gdf

def _get_blocks(gdf : gpd.GeoDataFrame, lines_gdf : gpd.GeoDataFrame, buffer : int = 2) -> gpd.GeoDataFrame:
    buffered_lines = lines_gdf.buffer(buffer)
    merged_polygon = buffered_lines.unary_union
    split_territory = gdf.overlay(
        gpd.GeoDataFrame(geometry=[merged_polygon], crs=gdf.crs),
        how='difference'
    )
    split_territory = split_territory.explode(index_parts=False)
    return split_territory

def _create_ring_roads(gdf : gpd.GeoDataFrame, blocks_gdf : gpd.GeoDataFrame, buffer_distance : int = 3):

    points = gdf.centroid
    points_gdf = gpd.GeoDataFrame(geometry=points, crs=gdf.crs)

    buffered_blocks = blocks_gdf.copy()
    buffered_blocks['geometry'] = buffered_blocks['geometry'].buffer(distance=buffer_distance)

    result_gdf = gpd.GeoDataFrame(columns=['block_id', 'point_id', 'geometry'], crs=gdf.crs)

    for block_id, block in buffered_blocks.iterrows():
        for point_id, point in points_gdf.iterrows():
            if block['geometry'].contains(point['geometry']):
                centroid = block['geometry'].centroid
                line = shapely.MultiPoint([point['geometry'], centroid]).convex_hull
                result_gdf = pd.concat([result_gdf, pd.DataFrame({
                    'block_id': [block_id],
                    'point_id': [point_id],
                    'geometry': [line]
                })], ignore_index=True)

    result_gdf = result_gdf[['block_id', 'geometry']]

    blocks_gdf['centroid'] = blocks_gdf.geometry.centroid

    new_lines = []
    for _, polygon in blocks_gdf.iterrows():
        centroid = polygon['centroid']
        intersecting_lines = result_gdf[result_gdf.intersects(polygon.geometry)]

        for line_idx, line in intersecting_lines.iterrows():
            if not line.geometry.is_empty:
                coords = list(line.geometry.coords)
                coords[-1] = (centroid.x, centroid.y)
                new_line = shapely.LineString(coords)
                new_lines.append(new_line)

    final_result_gdf = gpd.GeoDataFrame(new_lines, columns=['geometry'], crs=gdf.crs)

    return final_result_gdf

def _extend_single_line(line : shapely.LineString, distance : float = 0.25) -> shapely.LineString:
    if len(line.coords) < 2:
        return line

    start = shapely.Point(line.coords[0])
    second = shapely.Point(line.coords[1])

    end = shapely.Point(line.coords[-1])
    penultimate = shapely.Point(line.coords[-2])

    dx_start = start.x - second.x
    dy_start = start.y - second.y
    length_start = math.hypot(dx_start, dy_start)
    if length_start == 0:
        new_start = start
    else:
        dx_start /= length_start
        dy_start /= length_start
        new_start = shapely.Point(start.x + dx_start * distance, start.y + dy_start * distance)

    dx_end = end.x - penultimate.x
    dy_end = end.y - penultimate.y
    length_end = math.hypot(dx_end, dy_end)
    if length_end == 0:
        new_end = end
    else:
        dx_end /= length_end
        dy_end /= length_end
        new_end = shapely.Point(end.x + dx_end * distance, end.y + dy_end * distance)

    new_coords = [ (new_start.x, new_start.y) ] + list(line.coords) + [ (new_end.x, new_end.y) ]
    return shapely.LineString(new_coords)

def _extend_line(line : shapely.LineString, distance : float = 0.25) -> shapely.LineString | shapely.MultiLineString:
    if isinstance(line, shapely.LineString):
        return _extend_single_line(line, distance)
    elif isinstance(line, shapely.MultiLineString):
        extended_lines = [_extend_single_line(line, distance) for line in line]
        return shapely.MultiLineString(extended_lines)
    else:
        return line

def _snap_endpoints(gdf : gpd.GeoDataFrame, tolerance : float = 0.2) -> gpd.GeoDataFrame:
    endpoints = []
    for line in gdf.geometry:
      point_a = shapely.Point(line.coords[0])
      point_b = shapely.Point(line.coords[0])
      endpoints.extend([point_a, point_b])

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

        centroid = shapely.unary_union(close_points).centroid
        merged_points.append(centroid)

    new_geometries = []

    for line in gdf.geometry:
        coords = list(line.coords)
        new_coords = []

        for coord in coords:
            point = shapely.Point(coord)
            for merged_point in merged_points:
                if point.distance(merged_point) <= tolerance:
                    point = merged_point
                    break
            new_coords.append((point.x, point.y))

        new_line = shapely.LineString(new_coords)
        new_geometries.append(new_line)

    gdf['geometry'] = new_geometries
    return gdf

def _longify_roads(gdf_a : gpd.GeoDataFrame, gdf_b : gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    combined_gdf = pd.concat([gdf_a, gdf_b], ignore_index=True)
    combined_gdf['geometry'] = combined_gdf['geometry'].apply(lambda geom: _extend_line(geom, distance=0.25))
    combined_gdf = _split_lines(combined_gdf)
    combined_gdf['length'] = combined_gdf.length
    combined_gdf = combined_gdf[combined_gdf['length'] >= 1.5]
    return _snap_endpoints(combined_gdf)

def _calculate_angle(line1 : shapely.LineString, line2 : shapely.LineString) -> float:
    def direction_vector(line):
        x_diff = line.coords[-1][0] - line.coords[0][0]
        y_diff = line.coords[-1][1] - line.coords[0][1]
        return np.array([x_diff, y_diff])

    v1 = direction_vector(line1)
    v2 = direction_vector(line2)

    angle_rad = math.atan2(np.linalg.det([v1, v2]), np.dot(v1, v2))
    angle_deg = abs(math.degrees(angle_rad))
    return min(angle_deg, 360 - angle_deg)

def _process_geodata(gdf : gpd.GeoDataFrame, result_gdf : gpd.GeoDataFrame, split_territory : gpd.GeoDataFrame, buffer_distance : float = 1):

    boundary = gdf.boundary
    buffered_boundary = boundary.buffer(buffer_distance)

    intersecting_polygons = split_territory[split_territory.intersects(buffered_boundary.unary_union)]
    lines_within_polygons = result_gdf[result_gdf.intersects(intersecting_polygons.unary_union)]

    indices_to_remove = lines_within_polygons.index
    result_gdf = result_gdf.drop(indices_to_remove)

    projected_polygons = intersecting_polygons.to_crs(gdf.crs)
    projected_lines = lines_within_polygons.to_crs(gdf.crs)

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

                angle = _calculate_angle(line1, line2)

                if angle > max_min_angle:
                    max_min_angle = angle
                    best_pair = (sorted_lines.iloc[i], sorted_lines.iloc[j])

        if best_pair:
            result_lines = pd.concat([result_lines, pd.DataFrame([best_pair[0], best_pair[1]]).drop(columns='length')], ignore_index=True)

    result_lines = result_lines.drop(columns='length', errors='ignore').set_crs(gdf.crs)

    return result_gdf, result_lines, intersecting_polygons

def _find_intersections_and_create_lines(combined_gdf, intersecting_polygons):
    intersection_points = []

    for i in range(len(combined_gdf)):
        for j in range(i + 1, len(combined_gdf)):
            line1 = combined_gdf.geometry.iloc[i]
            line2 = combined_gdf.geometry.iloc[j]

            if line1.intersects(line2):
                intersection = line1.intersection(line2)

                if isinstance(intersection, shapely.Point):
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

        line = shapely.LineString([nearest_point_geom, centroid])
        lines_to_centroids.append(line)

    lines_gdf = gpd.GeoDataFrame(geometry=lines_to_centroids, crs=intersections_gdf.crs)

    return lines_gdf

def _select_central_polygons(territory, split_territory):
    territory_centroid = territory.geometry.centroid.iloc[0]

    split_territory['distance'] = split_territory.geometry.apply(lambda g: shapely.distance(g, territory_centroid))
    split_sorted = split_territory.sort_values('distance')

    total_polygons = len(split_sorted)
    lower_bound = int(total_polygons * 0.01)
    upper_bound = int(total_polygons * 0.35)

    num_to_select = np.random.randint(lower_bound, upper_bound + 1)

    central_polygons = split_sorted.head(num_to_select)
    central_gdf = gpd.GeoDataFrame(central_polygons, geometry='geometry')

    return central_gdf

def _create_line(midpoint, centroid):
    if midpoint is not None and centroid is not None:
        return shapely.LineString([midpoint, centroid])
    return None

def convert_geodataframe(df, crs):
    gdf = gpd.GeoDataFrame(geometry=df, crs=crs)
    return gdf

def _midpoint(geometry):
    if geometry.geom_type == 'LineString':
        return geometry.interpolate(0.5, normalized=True)
    elif geometry.geom_type == 'MultiLineString':
        longest_line = max(geometry, key=lambda line: line.length)
        return longest_line.interpolate(0.5, normalized=True)
    else:
        return None

def _find_intersecting_centroid(line, polygons):
    intersecting = polygons[polygons.intersects(line)]
    if not intersecting.empty:
        return intersecting.iloc[0].centroid
    return None

def _process_territory_graph(territory, combined_gdf, intersecting_polygons):
    territory_boundary = territory.boundary
    territory_boundary = convert_geodataframe(territory_boundary, territory.crs)
    graph = _longify_roads(territory_boundary, combined_gdf)
    buffered_boundary = territory_boundary.buffer(0.5)
    buffered_boundary = convert_geodataframe(buffered_boundary, territory.crs)
    lines_within_buffer = gpd.sjoin(graph, buffered_boundary, how="inner", predicate="within")
    lines_within_buffer['midpoint'] = lines_within_buffer['geometry'].apply(_midpoint)
    intersecting_polygons['centroid'] = intersecting_polygons.centroid
    lines_within_buffer['centroid'] = lines_within_buffer['geometry'].apply(
        lambda x: _find_intersecting_centroid(x, intersecting_polygons))
    lines_within_buffer['geometry'] = lines_within_buffer.apply(
        lambda row: _create_line(row['midpoint'], row['centroid']), axis=1)
    lines_within_buffer = lines_within_buffer['geometry']
    lines_within_buffer = convert_geodataframe(lines_within_buffer, territory.crs)
    graph = pd.concat([combined_gdf, lines_within_buffer], ignore_index=True)

    return graph

def _process_territory(territory_big, final_result):
    territory_big_boundary = territory_big.boundary
    territory_big_boundary = convert_geodataframe(territory_big_boundary, territory_big.crs)
    final = _longify_roads(territory_big_boundary, final_result)

    return final

def _get_connected_and_unconnected_lines(gdf, buffer_distance=0.1):
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
    unconnected = _snap_endpoints(unconnected_lines_gdf, tolerance=100)
    line_final = pd.concat([connected_lines_gdf, unconnected], ignore_index=True)

    return line_final.set_crs(gdf.crs)

def _generate_network(gdf : gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    project_polygon = gdf.iloc[0].geometry
    num_parts = _calculate_num_parts(project_polygon)
    parts_gdf = _polygon_to_parts(project_polygon, num_parts, gdf.crs)
    results = []

    for part_geometry in parts_gdf.geometry:
        part_gdf = gpd.GeoDataFrame(geometry=[part_geometry], crs=parts_gdf.crs)
        
        streets_gdf = _generate_streets(part_gdf)
        first_blocks_gdf = _get_blocks(part_gdf, streets_gdf)

        ring_roads_gdf = _create_ring_roads(streets_gdf, first_blocks_gdf)
        second_blocks_gdf = _get_blocks(first_blocks_gdf, ring_roads_gdf)

        combined_first_roads = _longify_roads(ring_roads_gdf, streets_gdf)
        street_precenter = _create_ring_roads(combined_first_roads, second_blocks_gdf) # TODO how to name it

        # TODO from now on im not able to refactor and name everything

        result_gdf, result_lines, intersecting_polygons = _process_geodata(part_gdf, street_precenter, second_blocks_gdf)
        lines_gdf = _find_intersections_and_create_lines(combined_first_roads, intersecting_polygons)

        combined = pd.concat([result_lines, result_gdf, lines_gdf], ignore_index=True)
        combined_gdf = _longify_roads(combined_first_roads, combined)

        split_territory = _get_blocks(part_gdf, combined_gdf)
        central_gdf = _select_central_polygons(part_gdf, split_territory)

        result_gdf = _create_ring_roads(combined_gdf, central_gdf)
        combined_gdf = _longify_roads(combined_gdf, result_gdf)

        combined_gdf = _process_territory_graph(part_gdf, combined_gdf, intersecting_polygons)
        # clip lines
        combined_gdf = combined_gdf.clip(part_gdf).explode(index_parts=False).reset_index(drop=True)
        results.append(combined_gdf)

    final_result = gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=gdf.crs)
    final_result = _process_territory(gdf, final_result)
    line_final = _get_connected_and_unconnected_lines(final_result)

    return line_final

def generate_network(project_scenario_id : int, token : str):
    logger.info('Fetching project geometry')
    project_geometry = _fetch_project_geometry(project_scenario_id, token)
    project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=const.DEFAULT_CRS)
    local_crs = project_gdf.estimate_utm_crs()
    project_gdf = project_gdf.to_crs(local_crs)
    project_gdf = project_gdf.explode(index_parts=False).reset_index(drop=True)
    return _generate_network(project_gdf)

# def gedsfsdfsnerate_network(project_scenario_id : int, token : str):


    
#     project, num_parts = calculate_num_parts(project_gdf)
#     project = split_polygon_grid(project, num_parts)

#     results = []

#     for _, poly in project.iterrows():
#         single_poly = gpd.GeoDataFrame([poly], geometry='geometry', crs=project.crs)

#         street_center, single_poly = generation(single_poly)
#         blocks_one = split_territory_by_buffer(single_poly, street_center)

#         street_ring_center = process_geospatial_data(street_center, blocks_one)
#         blocks_two = split_territory_by_buffer(blocks_one, street_ring_center)

#         combined_street_one = process_geodataframes(street_ring_center, street_center)
#         street_precenter = process_geospatial_data(combined_street_one, blocks_two)

#         result_gdf, result_lines, intersecting_polygons = process_geodata(single_poly, street_precenter, blocks_two)
#         lines_gdf = find_intersections_and_create_lines(combined_street_one, intersecting_polygons)

#         combined = pd.concat([result_lines, result_gdf, lines_gdf], ignore_index=True)
#         combined_gdf = process_geodataframes(combined_street_one, combined)

#         split_territory = split_territory_by_buffer(single_poly, combined_gdf)
#         central_gdf = select_central_polygons(single_poly, split_territory)

#         result_gdf = process_geospatial_data(combined_gdf, central_gdf)
#         combined_gdf = process_geodataframes(combined_gdf, result_gdf)

#         combined_gdf = process_territory_graph(single_poly, combined_gdf, intersecting_polygons)
#         results.append(combined_gdf)

#     final_result = gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=project.crs)
#     final_result = process_territory(project_gdf, final_result)
#     line_final = get_connected_and_unconnected_lines(final_result)
#     line_integration = calculate_global_integration(line_final)
#     # blocks_final = split_territory_by_buffer(project_gdf, line_integration)
#     return line_integration
#     # blocks_final.to_file('final_blocks.geojson')