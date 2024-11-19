import pandas as pd
from shapely import wkt
import geopandas as gpd
import re
from shapely.geometry import Polygon, Point
from pyproj import CRS, Transformer
import numpy as np
import random
from geopy.distance import geodesic
import matplotlib.pyplot as plt

# 데이터 로드 및 전처리
def preprocess_safe_center_point(point_str):
    match = re.match(r'\(?([-\d.]+),\s*([-\d.]+)\)?', point_str)
    if match:
        x, y = match.groups()
        return f"POINT ({x} {y})"
    return None

def load_and_preprocess_data(file_path):
    # CSV 파일을 로드합니다
    data = pd.read_csv(file_path)
    
    # Safe Center Point 열을 WKT 형식으로 변환한 후 Shapely Point 객체로 변환
    data['safe_center_point'] = data['Safe Center Point'].apply(preprocess_safe_center_point)
    data['safe_center_point'] = data['safe_center_point'].apply(wkt.loads)
    
    # WKT 형식의 폴리곤을 Shapely geometry 객체로 변환
    data['geometry'] = data['Polygon'].apply(wkt.loads)
    
    # GeoDataFrame 생성 및 좌표계 설정
    gdf = gpd.GeoDataFrame(data, geometry='geometry')
    gdf.set_crs(epsg=4326, inplace=True)  # WGS84 좌표계 설정
    
    return gdf

######################################

def transform_coordinates(center_lat, center_lon, radius_m, crs_from='EPSG:4326', crs_to='EPSG:32652'):
    # 좌표 변환기 생성 (WGS84 -> UTM)
    transformer = Transformer.from_crs(crs_from, crs_to, always_xy=True)
    center_x, center_y = transformer.transform(center_lon, center_lat)
    
    # 반경을 고려한 원 생성
    num_points = 100  # 원을 구성할 포인트 수
    angles = np.linspace(0, 2 * np.pi, num_points)
    x_circle = center_x + radius_m * np.cos(angles)
    y_circle = center_y + radius_m * np.sin(angles)
    circle_polygon = Polygon(zip(x_circle, y_circle))
    
    # UTM 좌표계를 WGS84로 변환
    transformer_back = Transformer.from_crs(crs_to, crs_from, always_xy=True)
    circle_wgs84 = Polygon([transformer_back.transform(x, y) for x, y in zip(x_circle, y_circle)])
    
    return center_x, center_y, circle_polygon, circle_wgs84

def random_point_in_polygon(polygon):
    """
    주어진 폴리곤 내부에서 랜덤한 포인트를 생성하는 함수.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 포인트를 생성할 폴리곤.
    
    Returns:
    - Point: 폴리곤 내부의 랜덤 포인트.
    """
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        random_point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(random_point):
            return random_point

######################################
# 거리 계산 
def calculate_distance(point1, point2):
    """
    두 지점 간의 거리를 계산하는 함수 (미터 단위).
    
    Parameters:
    - point1 (shapely.geometry.Point): 첫 번째 지점.
    - point2 (shapely.geometry.Point): 두 번째 지점.
    
    Returns:
    - float: 두 지점 간의 거리 (미터 단위).
    """
    return geodesic((point1.y, point1.x), (point2.y, point2.x)).meters

def calculate_distances_to_obstacles(uam_location, obstacles_gdf):
    """
    UAM 위치와 여러 장애물 간의 거리를 계산하는 함수.
    
    Parameters:
    - uam_location (shapely.geometry.Point): UAM 위치.
    - obstacles_gdf (geopandas.GeoDataFrame): 장애물 위치를 포함한 GeoDataFrame.
    
    Returns:
    - dict: 장애물 ID와 해당 장애물까지의 거리 (미터 단위).
    """
    distances = {}
    for idx, obstacle in obstacles_gdf.iterrows():
        obstacle_point = obstacle.geometry
        distance = calculate_distance(uam_location, obstacle_point)
        distances[idx] = distance
    return distances

def generate_obstacles_in_polygon(polygon, num_obstacles):
    """
    지정된 폴리곤 내부에 임의의 장애물 위치를 생성하는 함수.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 장애물을 생성할 폴리곤.
    - num_obstacles (int): 생성할 장애물 개수.
    
    Returns:
    - GeoDataFrame: 생성된 장애물 위치를 포함한 GeoDataFrame.
    """
    obstacles = [random_point_in_polygon(polygon) for _ in range(num_obstacles)]
    obstacles_gdf = gpd.GeoDataFrame(geometry=obstacles, crs="EPSG:4326")
    return obstacles_gdf

######################################

# 장애물 확인 및 필터링 모듈

def count_obstacles_in_polygon(polygon, obstacles_gdf):
    """
    지정된 폴리곤 내에 포함된 장애물의 개수를 계산하는 함수.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 장애물을 확인할 폴리곤.
    - obstacles_gdf (geopandas.GeoDataFrame): 장애물 위치가 저장된 GeoDataFrame.
    
    Returns:
    - int: 폴리곤 내 장애물 개수.
    """
    return sum(obstacles_gdf.within(polygon))

def is_landing_point_valid(polygon, center, radius_m, obstacles_gdf):
    """
    지정된 폴리곤이 착륙지점으로 유효한지 확인하는 함수.
    반경 내에 장애물이 없어야 유효한 착륙지점으로 간주.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 착륙지점으로 검토할 폴리곤.
    - center (shapely.geometry.Point): 착륙지점의 중심 좌표.
    - radius_m (float): 착륙 가능 반경 (미터).
    - obstacles_gdf (geopandas.GeoDataFrame): 장애물 위치가 저장된 GeoDataFrame.
    
    Returns:
    - bool: 착륙지점으로 유효하면 True, 아니면 False.
    """
    # 착륙 반경 내의 원 생성
    landing_circle = center.buffer(radius_m / 111320)  # 미터를 위도/경도로 변환
    
    # 원 내부에 장애물이 있는지 확인
    for obstacle in obstacles_gdf.geometry:
        if landing_circle.contains(obstacle):
            return False
    return True

def get_obstacles_in_polygon(polygon, obstacles_gdf):
    """
    지정된 폴리곤 내에 있는 모든 장애물의 위치를 반환하는 함수.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 장애물을 확인할 폴리곤.
    - obstacles_gdf (geopandas.GeoDataFrame): 장애물 위치가 저장된 GeoDataFrame.
    
    Returns:
    - list: 폴리곤 내에 있는 장애물의 좌표 리스트.
    """
    return [obstacle for obstacle in obstacles_gdf.geometry if polygon.contains(obstacle)]

######################################

def select_landing_candidates(gdf, uam_location, obstacles_gdf, radius_m):
    """
    유효한 착륙지점 후보지를 선정하고, UAM과 가장 가까운 착륙지점을 반환하는 함수.
    
    Parameters:
    - gdf (GeoDataFrame): 폴리곤 및 safe_center_point가 포함된 GeoDataFrame.
    - uam_location (shapely.geometry.Point): UAM의 위치.
    - obstacles_gdf (GeoDataFrame): 장애물 위치가 저장된 GeoDataFrame.
    - radius_m (float): 착륙 가능 반경 (미터).
    
    Returns:
    - dict: 가장 가까운 유효 착륙지점 정보(위치 및 거리) 또는 "유효한 착륙지점이 없습니다" 메시지.
    """
    valid_safe_center_points = []
    valid_landing_polygons = []

    for idx, row in gdf.iterrows():
        polygon = row['geometry']
        safe_center_point = row['safe_center_point']
        
        # 착륙지점 유효성 검사
        uam_size = 10
        safe_radius = 2.5 * uam_size 
        if is_landing_point_valid(polygon, safe_center_point, safe_radius, obstacles_gdf):
            valid_landing_polygons.append(polygon)
            valid_safe_center_points.append(safe_center_point)
            print(f"Polygon {idx}는 유효한 착륙지점입니다.")
        else:
            print(f"Polygon {idx}는 유효하지 않은 착륙지점입니다.")

    # 유효 착륙지점 중 가장 가까운 지점 선택
    if valid_safe_center_points:
        closest_safe_center = min(
            valid_safe_center_points,
            key=lambda point: geodesic((uam_location.y, uam_location.x), (point.y, point.x)).meters
        )
        closest_distance = geodesic((uam_location.y, uam_location.x), (closest_safe_center.y, closest_safe_center.x)).meters
        print(f"선정된 착륙지점: 위도 {closest_safe_center.y}, 경도 {closest_safe_center.x}, 거리: {closest_distance:.2f} m")
        return {"location": closest_safe_center, "distance": closest_distance}, valid_landing_polygons
    else:
        print("유효한 착륙지점이 없습니다.")
        return "유효한 착륙지점이 없습니다", []

######################################

def visualize_uam_and_obstacles(circle_wgs84, uam_location, obstacles_gdf, polygons_gdf, valid_landing_polygons, selected_landing_point=None):
    """
    circle_wgs84 내에 UAM 위치, 장애물 위치, 모든 폴리곤 및 유효 착륙지점을 시각화하는 함수.
    
    Parameters:
    - circle_wgs84 (shapely.geometry.Polygon): WGS84 좌표계의 원 (착륙 가능 범위).
    - uam_location (shapely.geometry.Point): UAM 위치.
    - obstacles_gdf (GeoDataFrame): 장애물 위치가 저장된 GeoDataFrame.
    - polygons_gdf (GeoDataFrame): circle_wgs84 내의 모든 폴리곤과 safe_center_point를 포함한 GeoDataFrame.
    - valid_landing_polygons (list): 유효한 착륙지점 폴리곤 리스트.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # circle_wgs84 원 시각화
    circle_gdf = gpd.GeoDataFrame(geometry=[circle_wgs84], crs="EPSG:4326")
    circle_gdf.boundary.plot(ax=ax, color="blue", linewidth=1, label="Landing Radius (circle_wgs84)")
    
    # 장애물 위치 시각화
    obstacles_gdf.plot(ax=ax, color="red", markersize=5, label="Obstacles")
    
    # circle_wgs84 내의 모든 폴리곤 시각화
    polygons_gdf.plot(ax=ax, color="plum", edgecolor="black", label="Polygons in Landing Radius")
    
    if valid_landing_polygons:
        # 유효 착륙지점 폴리곤 시각화 (초록색 경계선)
        valid_polygons_gdf = gpd.GeoDataFrame(geometry=valid_landing_polygons, crs="EPSG:4326")
        valid_polygons_gdf.boundary.plot(ax=ax, color="green", linewidth=2, label="Valid Landing Polygons")
    
    # 각 폴리곤의 safe_center_point 시각화
    for idx, row in polygons_gdf.iterrows():
        safe_center_point = row['safe_center_point']
        plt.plot(safe_center_point.x, safe_center_point.y, 'ko', markersize=6, label="Safe Center Point" if idx == 0 else "")
    
    # UAM 위치 시각화
    plt.plot(uam_location.x, uam_location.y, 'b*', markersize=20, label="UAM Location")

    # 선정된 착륙지점 시각화 (파란색 점)
    if selected_landing_point:
        plt.plot(selected_landing_point.x, selected_landing_point.y, 'bo', markersize=10, label="Selected Landing Point")

    # 범례 및 제목 설정
    plt.legend()
    plt.title("UAM Location, Obstacles, Landing Radius, and Polygons with Safe Center Points")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # Aspect 설정을 'auto'로 변경
    ax.set_aspect('auto')

    plt.show()

# main
def main():
    # 1. 데이터 로드 및 전처리
    # 데이터 파일 경로 설정
    file_path = 'results/filtering/Database/군위군_final_filtered_polygons_with_center.csv'
    
    # 데이터를 로드하고 전처리
    gdf = load_and_preprocess_data(file_path)

    # 2. 랜덤한 폴리곤 내에서 랜덤한 포인트 생성
    random_polygon = gdf['geometry'].sample(1).values[0]
    uam_location = random_point_in_polygon(random_polygon)  # 랜덤 포인트 생성

    # print('uam_location: ', uam_location)

    # 3. 중심점 및 반경 설정
    uam_lat = uam_location.y
    uam_lon = uam_location.x
    radius_m = 600
    
    # 좌표 변환 및 원 생성
    center_x, center_y, circle_polygon, circle_wgs84 = transform_coordinates(uam_lat, uam_lon, radius_m)

    # 4. 장애물 생성 및 UAM 착륙지점과의 거리 계산
    # circle_wgs84 내에서 1000개의 장애물 생성
    num_obstacles = 1000
    obstacles_gdf = generate_obstacles_in_polygon(circle_wgs84, num_obstacles)
    print(obstacles_gdf)

    # UAM 위치와 장애물 간 거리 계산
    distances_to_obstacles = calculate_distances_to_obstacles(uam_location, obstacles_gdf)
    # print("\nUAM 위치와 장애물 간 거리:")
    # for obstacle_id, distance in distances_to_obstacles.items():
    #     print(f"장애물 {obstacle_id}: {distance:.2f} m")

    # 5. 유효 착륙지점 확인 및 필터링
    # circle_wgs84 내에 safe_center_point가 포함된 폴리곤만 선택
    polygons_within_circle = gdf[
        gdf['geometry'].intersects(circle_wgs84) & 
        gdf['safe_center_point'].apply(lambda point: point is not None and circle_wgs84.contains(point))
    ]

    # 유효 착륙지점 후보지 선정
    safe_radius = 25
    result, valid_landing_polygons = select_landing_candidates(polygons_within_circle, uam_location, obstacles_gdf, safe_radius)
    
    # 결과에 따라 출력
    if isinstance(result, dict):
        selected_landing_point = result['location']
        print(f"선정된 착륙지점 위치: {result['location']}, 거리: {result['distance']:.2f} m")

        # 선정된 착륙지점에서 가장 가까운 장애물 거리 계산
        closest_obstacle_distance = min(
            calculate_distance(selected_landing_point, obstacle) for obstacle in obstacles_gdf.geometry
        )
        print(f"선정된 착륙지점에서 가장 가까운 장애물까지의 거리: {closest_obstacle_distance:.2f} m")
    else:
        selected_landing_point = []
        print(result)

    # 6. circle_wgs84 내의 모든 폴리곤 및 유효 착륙지점 시각화
    # circle_wgs84 내에 존재하는 모든 폴리곤 필터링하여 GeoDataFrame 생성
    polygons_gdf = gpd.GeoDataFrame(polygons_within_circle, geometry='geometry', crs="EPSG:4326")

    # 시각화 함수 호출
    visualize_uam_and_obstacles(circle_wgs84, uam_location, obstacles_gdf, polygons_gdf, valid_landing_polygons, selected_landing_point)

# 메인 실행 부분
if __name__ == "__main__":
    main()
