import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
from shapely import wkt
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

# UAM 노선의 주요 경로 좌표 정의 (실제 경로는 업데이트 가능)
uam_route_points = [
    (35.8796, 128.6284),  # 동대구역 -> 
    (35.87467, 128.61038),  # 신천철로 end point
    (35.904685, 128.592246), # 금호강 end point
    # (35.9133, 128.5730),  # 금호JC
    (35.88881, 128.52540),  # 금호JC
    (36.28081, 128.58175),   # 중앙고속도로 end point
    # (36.3026, 128.5237)   # 대구경북통합신공항 예정지
    (36.30309, 128.50657)   # 대구경북통합신공항 예정지
]

# 1km 간격으로 웨이포인트 생성 함수
def generate_waypoints(route_points, interval_km=1):
    waypoints = []
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
    
    return waypoints

# 중심점(centroid)과 웨이포인트 사이의 거리를 계산하여 최소 거리를 반환하는 함수
def calculate_min_distance(centroid, waypoints):
    centroid_coords = (centroid[1], centroid[0])  # (위도, 경도) 형식으로 변환
    # 각 웨이포인트와의 거리 계산 후 최소 거리 반환
    return min(geodesic(centroid_coords, waypoint).km for waypoint in waypoints)

# 모든 CSV 파일을 로드하고, 웨이포인트 기반으로 필터링하는 함수
def process_all_csv_files(folder, csv_list, waypoints, buffer_distance=2.5):
    all_filtered_polygons = []
    
    for file_name in csv_list:
        file_path = os.path.join(folder, file_name)
        data = pd.read_csv(file_path)

        # 각 폴리곤의 중심점과 웨이포인트 사이의 거리를 계산하고, 웨이포인트에서 buffer_distance 이내의 폴리곤만 필터링
        data['Distance_to_UAM_route'] = data['Centroid'].apply(eval).apply(lambda centroid: calculate_min_distance(centroid, waypoints))
        filtered_data = data[data['Distance_to_UAM_route'] <= buffer_distance]
        
        # WKT 형식으로 저장된 폴리곤 데이터를 shapely Polygon 객체로 변환
        filtered_polygons = [wkt.loads(row['Polygon']) for i, row in filtered_data.iterrows()]
        
        # 모든 구의 필터링된 폴리곤을 저장
        all_filtered_polygons.extend(filtered_polygons)

    return all_filtered_polygons

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

# # 필터링 결과 시각화
# def visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints):
#     """
#     필터링된 폴리곤과 웨이포인트를 시각화
#     :param boundary_gdf: 결합된 경계 데이터 (geopandas GeoDataFrame)
#     :param filtered_polygons: 1차 필터링된 폴리곤 리스트 (shapely.geometry.Polygon 객체)
#     :param waypoints: 생성된 웨이포인트 리스트
#     :return: fig
#     """
#     # 시각화할 데이터가 있는지 확인
#     if not filtered_polygons:
#         print("No polygons to visualize.")
#         return None

#     # 시각화 준비    
#     fig, ax = plt.subplots(1, 1, figsize=(12, 12))

#     # 경계 데이터 시각화
#     boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

#     # 필터링된 폴리곤 시각화
#     for poly in filtered_polygons:
#         gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color='green', alpha=0.6)

#     # 웨이포인트 시각화
#     waypoint_x = [point[1] for point in waypoints]
#     waypoint_y = [point[0] for point in waypoints]
#     ax.scatter(waypoint_x, waypoint_y, color='orange', label='Waypoints (1km intervals)', s=50)

#     # 수동으로 범례 생성
#     legend_patches = [
#         Patch(color='green', alpha=0.5, label='Landing Able Sites'),
#         Patch(facecolor='white', edgecolor='green', alpha=0.5, label='No landing Area'),
#         Patch(facecolor='orange', edgecolor='orange', label='Waypoints (1km intervals)')
#     ]
#     ax.legend(handles=legend_patches)

#     # 축 및 제목 설정
#     ax.set_xlabel('Longitude')
#     ax.set_ylabel('Latitude')
#     ax.set_title('Polygons with Waypoints')

#     # 결과 시각화 표시
#     plt.show()

#     return fig

# 필터링 결과 시각화
def visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints, uam_route_points):
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

    # 시각화 준비    
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))

    # 경계 데이터 시각화
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

    # 필터링된 폴리곤 시각화
    for poly in filtered_polygons:
        gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color='green', alpha=0.6)

    # 웨이포인트 시각화 (오렌지색)
    waypoint_x = [point[1] for point in waypoints]
    waypoint_y = [point[0] for point in waypoints]
    ax.scatter(waypoint_x, waypoint_y, color='orange', label='Waypoints (1km intervals)', s=50)

    # UAM 경로의 주요 지점 시각화 (파란색)
    uam_x = [point[1] for point in uam_route_points]
    uam_y = [point[0] for point in uam_route_points]
    ax.scatter(uam_x, uam_y, color='blue', label='UAM Route Points', s=100, marker='X')

    # 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.5, label='Landing Able Sites'),
        Patch(facecolor='white', edgecolor='green', alpha=0.5, label='No landing Area'),
        Patch(facecolor='orange', edgecolor='orange', label='Waypoints (1km intervals)'),
        Patch(facecolor='blue', edgecolor='blue', label='UAM Route Points')
    ]
    ax.legend(handles=legend_patches)

    # 축 및 제목 설정
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Polygons with Waypoints and UAM Route Points')

    # 결과 시각화 표시
    plt.show()

    return fig



# 경계 데이터 경로
boundary_folder_path = 'data/boundary'

# 모든 경계 데이터를 로드
boundary_gdf = load_all_boundary_data(boundary_folder_path)

# 웨이포인트 생성 (1km 간격)
waypoints = generate_waypoints(uam_route_points, interval_km=1)

# 모든 CSV 파일을 처리 (웨이포인트를 기준으로 필터링)
folder_path = 'results/filtering/Database'
csv_files = [
    '달성군_final_filtered_polygons.csv',
    '달서구_final_filtered_polygons.csv',
    '군위군_final_filtered_polygons.csv',
    '중구_final_filtered_polygons.csv',
    '수성_final_filtered_polygons.csv',
    '서구_final_filtered_polygons.csv',
    '동구_final_filtered_polygons.csv',
    '북구_final_filtered_polygons.csv',
    '남구_final_filtered_polygons.csv'
]
filtered_polygons = process_all_csv_files(folder_path, csv_files, waypoints, buffer_distance=5)  # 반경을 5km로 설정

# 필터링된 폴리곤을 시각화
# visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints)
visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints, uam_route_points)
