import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiLineString
from shapely import wkt
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import osmnx as ox
import filter
from tqdm import tqdm

# 필터링된 데이터 로드 함수
def load_filtered_data(file_path):
    """
    이미 저장된 CSV 파일에서 필터링된 폴리곤과 중심점을 로드합니다.
    """
    data = pd.read_csv(file_path)
    filtered_polygons = data['Polygon'].apply(wkt.loads).tolist()  # WKT 형식을 Polygon 객체로 변환
    filtered_centers = data['Safe Center Point'].apply(eval).tolist()  # 중심점 좌표 리스트로 변환
    return filtered_polygons, filtered_centers

# 경계 데이터를 로드하는 함수 (CSV 파일에서 WKT 형식으로 로드)
def load_all_boundary_data(boundary_folder):
    all_boundaries = []
    
    # boundary_folder에 있는 모든 경계 CSV 파일을 불러오기
    for boundary_file in os.listdir(boundary_folder):
        if boundary_file.endswith('.csv'):
            boundary_path = os.path.join(boundary_folder, boundary_file)
            boundary_data = pd.read_csv(boundary_path)
            boundary_coords = boundary_data[['Longitude', 'Latitude']].values
            boundary_polygon = Polygon(boundary_coords)
            
            # 각 경계 폴리곤을 GeoDataFrame으로 변환하여 저장
            boundary_gdf = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[boundary_polygon])
            all_boundaries.append(boundary_gdf)
    
    # 모든 구의 경계 데이터를 결합
    return pd.concat(all_boundaries, ignore_index=True)

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

# 1km 간격으로 웨이포인트 생성 함수
def generate_waypoints(route_points, interval_km=1):
    waypoints = [route_points[0]]  # 시작점을 추가
    for i in range(len(route_points) - 1):
        start = route_points[i]
        end = route_points[i + 1]
        
        # 두 지점 사이의 거리 계산
        total_distance = geodesic(start, end).km
        
        # 필요한 웨이포인트 개수 계산
        num_waypoints = int(np.floor(total_distance / interval_km))
        
        # 간격에 따라 웨이포인트 생성
        for j in range(1, num_waypoints + 1):
            fraction = j / num_waypoints
            lat = start[0] + fraction * (end[0] - start[0])
            lon = start[1] + fraction * (end[1] - start[1])
            waypoints.append((lat, lon))
    
    # 구간의 끝 지점을 추가
    waypoints.append(end)
    return waypoints

# Waypoints 사이의 거리가 1km 이상일 때만 유효한 웨이포인트로 선택
def filter_waypoints(waypoints, interval_km=1):
    filtered_waypoints = [waypoints[0]]  # 첫 번째 웨이포인트 추가
    last_added = waypoints[0]

    for waypoint in waypoints[1:]:
        if geodesic(last_added, waypoint).km >= interval_km:
            filtered_waypoints.append(waypoint)
            last_added = waypoint

    return filtered_waypoints

# 중심점(centroid)과 웨이포인트 사이의 거리를 계산하여 최소 거리를 반환하는 함수
def calculate_min_distance(centroid, waypoints):
    centroid_coords = (centroid[1], centroid[0])  # (위도, 경도) 형식으로 변환
    return min(geodesic(centroid_coords, waypoint).km for waypoint in waypoints)

def get_palgongsan_boundary():
    # 'boundary'가 'national_park'인 팔공산 국립공원의 경계 데이터 가져오기
    place_name = "Palgongsan National Park, South Korea"
    tags = {"boundary": "national_park"}
    palgongsan_boundary = ox.geometries_from_place(place_name, tags)
    
    # 경계 데이터에서 multipolygon 형태의 데이터만 필터링
    palgongsan_boundary = palgongsan_boundary[palgongsan_boundary.geometry.type == 'Polygon']
    
    return palgongsan_boundary

# 필터링 결과 시각화
def visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints, uam_route_points, uploaded_data):
    """
    필터링된 폴리곤과 웨이포인트를 시각화
    :param boundary_gdf: 결합된 경계 데이터 (geopandas GeoDataFrame)
    :param filtered_polygons: 1차 필터링된 폴리곤 리스트 (shapely.geometry.Polygon 객체)
    :param waypoints: 생성된 웨이포인트 리스트
    :param uam_route_points: 주요 UAM 경로 좌표 리스트
    :return: fig
    """
    # 시각화할 데이터가 있는지 확인
    if not filtered_polygons:
        print("No polygons to visualize.")
        return None

    # '0' 값 제거
    non_zero_safe_center_data = uploaded_data[uploaded_data['Optimal_Cluster_Safe_Center'] != '0']
    zero_safe_center_data = uploaded_data[uploaded_data['Optimal_Cluster_Safe_Center'] == '0']

    # Optimal_Cluster_Safe_Center 열의 데이터를 GeoDataFrame으로 변환
    non_zero_safe_center_data['geometry'] = non_zero_safe_center_data['Optimal_Cluster_Safe_Center'].apply(wkt.loads)
    safe_center_data = gpd.GeoDataFrame(non_zero_safe_center_data, geometry='geometry', crs="EPSG:4326")

    # UAM_Location 열의 데이터를 GeoDataFrame으로 변환
    uploaded_data['Safe_UAM_Location_geometry'] = non_zero_safe_center_data['UAM_Location'].apply(wkt.loads)
    safe_uam_data = gpd.GeoDataFrame(uploaded_data, geometry='Safe_UAM_Location_geometry', crs="EPSG:4326")

    uploaded_data['Unsafe_UAM_Location_geometry'] = zero_safe_center_data['UAM_Location'].apply(wkt.loads)
    unsafe_uam_data = gpd.GeoDataFrame(uploaded_data, geometry='Unsafe_UAM_Location_geometry', crs="EPSG:4326")

    # uploaded_data['UAM_Location_geometry'] = uploaded_data['UAM_Location'].apply(wkt.loads)
    # uam_location_data = gpd.GeoDataFrame(uploaded_data, geometry='UAM_Location_geometry', crs="EPSG:4326")

    # 시각화 준비    
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))

    # 경계 데이터 시각화
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

    # # 팔공산 국립공원의 경계 데이터 가져오기
    # palgongsan_boundary = get_palgongsan_boundary()
    
    # # 팔공산 국립공원 경계 시각화 (연한 녹색)
    # palgongsan_boundary.plot(ax=ax, color='lightgreen', edgecolor='green', alpha=0.5, linewidth=2, label='Palgongsan National Park')

    # 필터링된 폴리곤 시각화
    for poly in filtered_polygons:
        gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color='plum')

    # 웨이포인트 시각화 (오렌지색)
    waypoint_x = [point[1] for point in waypoints]
    waypoint_y = [point[0] for point in waypoints]
    ax.scatter(waypoint_x, waypoint_y, color='orange', edgecolor='orange' , label='Waypoints', s=50)

    # # UAM_Location 시각화
    # ax.scatter(
    #     safe_uam_data.geometry.x,
    #     safe_uam_data.geometry.y,
    #     color='green',
    #     label='UAM Locations',
    #     s=50
    # )

    # UAM_Location 시각화
    ax.scatter(
        unsafe_uam_data.geometry.x,
        unsafe_uam_data.geometry.y,
        color='red',
        marker ='x',
        label='UAM Locations',
        s=50
    )


    # selected_uam_points = [uam_route_points[0], uam_route_points[3], uam_route_points[-1]]
    # uam_x = [point[1] for point in selected_uam_points]
    # uam_y = [point[0] for point in selected_uam_points]
    # ax.scatter(uam_x, uam_y, color='blue', label='UAM Route Points', s=100)

    # Safe Center 시각화
    # safe_center_data.plot(ax=ax, color='blue', label='Optimal Cluster Safe Center', markersize=20)

    # Safe Center 시각화
    ax.scatter(
        safe_center_data.geometry.x,
        safe_center_data.geometry.y,
        color='blue',
        label='Optimal Cluster Safe Center',
        s=20
    )

    # 범례 생성
    legend_patches = [
        Patch(color='plum', label='Landing Able Sites'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=20, label='40m Waypoints'),  # 원형 범례
        Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=20, label='Cluster Centers')  # 원형 범례
    ]
    # ax.legend(handles=legend_patches)

    ax.legend(
        handles=legend_patches,
        loc="upper left",             # 범례 위치 
        bbox_to_anchor=(1.05, 1),  
        fontsize=20
    )

    # 축 및 제목 설정
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    # 결과 시각화 표시
    plt.show()

    return fig


# GeoJSON 파일 불러오기
river_file_path = 'data/geojson/kumho_river.geojson'    # 금호강
highway_file_path = 'data/geojson/export.geojson'       # 중앙고속도로

# 시작점과 종료점
start_point = (35.88881, 128.52540) # 금호JC
# end_point = (36.28081, 128.58175)   # 대구경북통합신공항 예정지 부근
end_point = (36.2539, 128.5676)   # 대구경북통합신공항 예정지 부근

# 추출된 구간의 좌표
highway_coords = extract_segment_coordinates(highway_file_path, start_point, end_point)

# UAM 노선
uam_route_points = [
    (35.8796, 128.6284),  # 동대구역 -> 
    (35.87467, 128.61038),  # 신천철로 end point
    (35.904685, 128.592246), # 금호강 end point
    (35.88881, 128.52540),  # 금호JC
    *highway_coords,  # 중앙고속도로 웨이포인트
    (36.30309, 128.50657)   # 대구경북통합신공항 예정지
]

# 웨이포인트 생성 (1km 간격)
waypoints_part1 = generate_waypoints(uam_route_points[0:4], interval_km=1)
waypoints_part2 = generate_waypoints([highway_coords[-1], uam_route_points[-1]], interval_km=1)

# 두 부분을 결합하여 최종 waypoints 리스트 생성
waypoints = waypoints_part1 + waypoints_part2

# 중앙고속도로 추가
waypoints.extend(highway_coords)

# 필터링된 데이터 CSV 파일 경로
filtered_csv_path = 'results/filtering/UAM/uam_route_filtered_polygons_4km_with_center.csv'

# 데이터 로드
filtered_polygons, filtered_centers = load_filtered_data(filtered_csv_path)

# 경계 데이터 경로
boundary_folder_path = 'data/boundary'

# 모든 경계 데이터를 로드
boundary_gdf = load_all_boundary_data(boundary_folder_path)

# CSV 파일 로드
# file_path = 'results/clustering/uam_waypoint_cluster_analysis_with_centers.csv'
file_path = 'results/clustering/uam_new_waypoint_cluster_analysis_new.csv'
uploaded_data = pd.read_csv(file_path)

# 필터링 결과 시각화
fig = visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints, uam_route_points, uploaded_data)
