import numpy as np
import geopandas as gpd
from geopy.distance import geodesic
from shapely.geometry import LineString, MultiLineString

def extract_segment_coordinates(file_path, start_point, end_point):
    """
    특정 구간의 좌표를 추출하는 함수.
    
    Parameters:
    - file_path: str, GeoJSON 파일 경로
    - start_point: tuple, 시작점 좌표 (위도, 경도) 형식
    - end_point: tuple, 종료점 좌표 (위도, 경도) 형식
    
    Returns:
    - extracted_segment_coords: list of tuples, 시작점과 종료점 사이의 추출된 구간 좌표 (위도, 경도) 형식
    """
    # GeoJSON 파일 불러오기
    gdf = gpd.read_file(file_path)
    
    # 모든 세그먼트 중 시작점과 종료점에 가장 가까운 세그먼트 선택
    closest_segment = None
    closest_start_index, closest_end_index = None, None
    min_start_distance, min_end_distance = float('inf'), float('inf')
    
    # 첫 번째 geometry 가져오기
    geom = gdf.geometry.iloc[0]
    
    if isinstance(geom, MultiLineString):
        for segment in geom.geoms:
            segment_coords = [(lat, lon) for lon, lat in segment.coords]
            
            # 시작점과 종료점에 가장 가까운 인덱스 찾기
            start_index = min(range(len(segment_coords)), key=lambda i: geodesic(segment_coords[i], start_point).meters)
            end_index = min(range(len(segment_coords)), key=lambda i: geodesic(segment_coords[i], end_point).meters)
            
            # 시작점과 종료점 거리 계산
            start_distance = geodesic(segment_coords[start_index], start_point).meters
            end_distance = geodesic(segment_coords[end_index], end_point).meters

            # 가장 가까운 세그먼트를 업데이트
            if start_distance < min_start_distance and end_distance < min_end_distance:
                closest_segment = segment_coords
                closest_start_index, closest_end_index = start_index, end_index
                min_start_distance, min_end_distance = start_distance, end_distance
                
    elif isinstance(geom, Polygon):
        segment_coords = [(lat, lon) for lon, lat in geom.exterior.coords]
        
        # 시작점과 종료점에 가장 가까운 인덱스 찾기
        start_index = min(range(len(segment_coords)), key=lambda i: geodesic(segment_coords[i], start_point).meters)
        end_index = min(range(len(segment_coords)), key=lambda i: geodesic(segment_coords[i], end_point).meters)
        
        # 인덱스와 거리 정보 업데이트
        closest_segment = segment_coords
        closest_start_index, closest_end_index = start_index, end_index

    # 인덱스 순서 확인 후 범위 설정
    if closest_start_index > closest_end_index:
        closest_start_index, closest_end_index = closest_end_index, closest_start_index  # 인덱스 교환
    
    # 추출된 구간의 좌표
    extracted_segment_coords = closest_segment[closest_start_index:closest_end_index + 1]
    return extracted_segment_coords

def generate_waypoints_along_route(route_points, interval_m=40):
    route_line = LineString([(point[1], point[0]) for point in route_points])  # (경도, 위도) 순서
    projected_line = gpd.GeoSeries([route_line], crs='epsg:4326').to_crs(epsg=3857).iloc[0]
    total_length_m = projected_line.length  # 총 길이 (미터 단위)

    num_waypoints = int(np.floor(total_length_m / interval_m))
    waypoints = []
    for i in range(num_waypoints + 1):
        fraction = (i * interval_m) / total_length_m
        if fraction > 1.0:
            fraction = 1.0
        point = projected_line.interpolate(fraction * projected_line.length)
        lon, lat = gpd.GeoSeries([point], crs='epsg:3857').to_crs(epsg=4326).iloc[0].coords[0]
        waypoints.append((lat, lon))  # (위도, 경도) 순서
    return waypoints

def calculate_total_distance_and_time(waypoints, speed_kmh):
    total_distance = 0  # 총 이동 거리 초기화
    for i in range(len(waypoints) - 1):
        total_distance += geodesic(waypoints[i], waypoints[i + 1]).km
    total_time = total_distance / speed_kmh  # 총 시간 계산
    return total_distance, total_time

# GeoJSON 파일 불러오기
highway_file_path = 'data/geojson/export.geojson'       # 중앙고속도로
dongdaegu_station = (35.8796, 128.6284)  # 동대구역
geumho_jc = (35.88881, 128.52540)        # 금호JC
daegu_airport = (36.30309, 128.50657)    # 대구경북통합신공항 예정지
end_point = (36.2539, 128.5676)   # 대구경북통합신공항 예정지 부근
speed_kmh = 150  # 이동 속도 (km/h)

# 추출된 구간의 좌표
highway_coords = extract_segment_coordinates(highway_file_path, geumho_jc, end_point)

# 주요 경로 설정
uam_route_points = [
    (35.8796, 128.6284),  # 동대구역
    (35.87467, 128.61038),  # 신천철로
    (35.904685, 128.592246),  # 금호강
    (35.88881, 128.52540),  # 금호JC
    *highway_coords,  # 중앙고속도로 웨이포인트
    (36.2539, 128.5676),  # 대구경북통합신공항 예정지 부근
]

# 웨이포인트 생성
waypoints = generate_waypoints_along_route(uam_route_points, interval_m=40)

# 동대구역 → 금호JC 웨이포인트 경로 추출
waypoints_dongdaegu_to_geumho = [
    wp for wp in waypoints if geodesic(wp, dongdaegu_station).km <= geodesic(dongdaegu_station, geumho_jc).km
]

# 금호JC → 대구경북통합신공항 웨이포인트 경로 추출
waypoints_geumho_to_airport = [
    wp for wp in waypoints if geodesic(wp, geumho_jc).km <= geodesic(geumho_jc, daegu_airport).km
]

# 각 구간의 총 이동 거리 및 시간 계산
distance_time_dongdaegu_to_geumho = calculate_total_distance_and_time(waypoints_dongdaegu_to_geumho, speed_kmh)
distance_time_geumho_to_airport = calculate_total_distance_and_time(waypoints_geumho_to_airport, speed_kmh)

# 결과 출력
print(f"동대구역 → 금호JC: 거리 = {distance_time_dongdaegu_to_geumho[0]:.2f} km, 시간 = {distance_time_dongdaegu_to_geumho[1]*60:.2f} 분")
print(f"금호JC → 대구경북통합신공항: 거리 = {distance_time_geumho_to_airport[0]:.2f} km, 시간 = {distance_time_geumho_to_airport[1]*60:.2f} 분")
