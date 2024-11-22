import pandas as pd
from shapely import wkt
from shapely.wkt import loads as wkt_loads
import geopandas as gpd
import re
from shapely.geometry import Polygon, Point
from pyproj import CRS, Transformer
import numpy as np
import random
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from tqdm import tqdm
import math
from uam_route_clustering_analysis_new import *

# 데이터 로드 및 전처리
def load_and_preprocess_data(file_path, polygon):
    """
    CSV 파일에서 데이터를 로드하고, 폴리곤과 중심점을 전처리하는 함수.

    Parameters:
    - file_path (str): CSV 파일 경로.

    Returns:
    - pd.DataFrame: 전처리된 데이터프레임 (geometry 및 centroid 포함).
    """
    data = pd.read_csv(file_path)

    if polygon:
        data['geometry'] = data['Polygon'].apply(safe_load_wkt)
        data = data[data['geometry'].notnull()]
        data['safe_center'] = data['Safe Center Point'].apply(lambda x: Point(eval(x)) if pd.notnull(x) else None)
    else:
        # WKT 형식 문자열을 shapely.geometry 객체로 변환
        data['optimal_safe_center'] = data['Optimal_Cluster_Safe_Center'].apply(
            lambda x: wkt_loads(x) if pd.notnull(x) else None
        )
        data['uam_location'] = data['UAM_Location'].apply(
            lambda x: wkt_loads(x) if pd.notnull(x) else None
        )

    # data['geometry'] = data['Polygon'].apply(safe_load_wkt)
    # data = data[data['geometry'].notnull()]
    # data['centroid'] = data['Centroid'].apply(lambda x: Point(eval(x)) if pd.notnull(x) else None)
    # data['safe_center'] = data['Safe Center Point'].apply(lambda x: Point(eval(x)) if pd.notnull(x) else None)

    return data

def safe_load_wkt(wkt_str):
    """
    WKT 문자열을 안전하게 로드하는 함수. 오류가 발생할 경우 None을 반환.

    Parameters:
    - wkt_str (str): WKT 형식의 문자열.

    Returns:
    - shapely.geometry (or None): 유효한 경우 로드된 geometry 객체, 아니면 None.
    """
    try:
        return wkt_loads(wkt_str)
    except (shapely.errors.WKTReadingError, TypeError):
        return None


def generate_sector(center, radius, angle, heading):
    """
    중심점에서 주어진 반경과 각도로 섹터(부채꼴 형태)를 생성하는 함수.

    Parameters:
    - center (Point): 섹터의 중심점.
    - radius (float): 섹터의 반경 (도 단위).
    - angle (float): 섹터의 각도 (도 단위).
    - heading (float): 섹터의 중심 방향 (도 단위, 북쪽을 0도로 간주).

    Returns:
    - list[Point]: 섹터를 구성하는 포인트들의 리스트.
    """
    points = [center]
    num_points = 100  # 부드러운 곡선을 위해 포인트 수 설정
    for i in range(num_points + 1):
        angle_rad = np.radians(heading - angle / 2 + i * angle / num_points)
        x = center.x + radius * np.cos(angle_rad)
        y = center.y + radius * np.sin(angle_rad)
        points.append(Point(x, y))
    points.append(center)  # 부채꼴을 닫기 위해 중심점 추가
    return points

def is_within_sector(point, center, radius, angle, heading):
    """
    주어진 포인트가 섹터 내부에 있는지 여부를 확인하는 함수.

    Parameters:
    - point (Point): 확인할 포인트.
    - center (Point): 섹터의 중심점.
    - radius (float): 섹터의 반경 (도 단위).
    - angle (float): 섹터의 각도 (도 단위).
    - heading (float): 섹터의 중심 방향 (도 단위).

    Returns:
    - bool: 포인트가 섹터 내에 있으면 True, 아니면 False.
    """
    distance = center.distance(point)
    if distance > radius:
        return False

    dx = point.x - center.x
    dy = point.y - center.y
    point_angle = (math.degrees(math.atan2(dy, dx))) % 360

    return heading-angle / 2 <= point_angle <= heading+angle / 2

######################################
# 결과 분석 #
def print_color(text, color="white"):
    """
    터미널에 컬러 텍스트를 출력하는 함수.

    Parameters:
    - text (str): 출력할 텍스트.
    - color (str): 출력할 색상. (기본값: 'white')
                   사용할 수 있는 색상: black, red, green, yellow, blue, magenta, cyan, white.
    """
    colors = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m"
    }
    reset = "\033[0m"
    color_code = colors.get(color.lower(), colors["white"])  # 기본값: white
    print(f"{color_code}{text}{reset}")

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

# def generate_obstacles_in_polygon(polygon, num_obstacles):
#     """
#     지정된 폴리곤 내부에 임의의 장애물 위치를 생성하는 함수.
    
#     Parameters:
#     - polygon (shapely.geometry.Polygon): 장애물을 생성할 폴리곤.
#     - num_obstacles (int): 생성할 장애물 개수.
    
#     Returns:
#     - GeoDataFrame: 생성된 장애물 위치를 포함한 GeoDataFrame.
#     """
#     obstacles = [random_point_in_polygon(polygon) for _ in range(num_obstacles)]
#     obstacles_gdf = gpd.GeoDataFrame(geometry=obstacles, crs="EPSG:4326")
#     return obstacles_gdf

# 장애물 생성 함수 수정
def generate_obstacles_in_polygon(polygon, num_obstacles):
    """
    지정된 폴리곤 내부에 임의의 장애물 위치를 생성하는 함수.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 장애물을 생성할 폴리곤.
    - num_obstacles (int): 생성할 장애물 개수.
    
    Returns:
    - GeoDataFrame: 생성된 장애물 위치를 포함한 GeoDataFrame.
    """
    obstacles = []
    minx, miny, maxx, maxy = polygon.bounds
    while len(obstacles) < num_obstacles:
        random_point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(random_point):
            obstacles.append(random_point)
    return gpd.GeoDataFrame(geometry=obstacles, crs="EPSG:4326")

# 섹터를 Polygon으로 변환
def generate_sector_polygon(center, radius, angle, heading):
    """
    중심점에서 주어진 반경과 각도로 섹터(Polygon 형태)를 생성하는 함수.

    Parameters:
    - center (Point): 섹터의 중심점.
    - radius (float): 섹터의 반경 (도 단위).
    - angle (float): 섹터의 각도 (도 단위).
    - heading (float): 섹터의 중심 방향 (도 단위, 북쪽을 0도로 간주).

    Returns:
    - Polygon: 섹터를 구성하는 Polygon 객체.
    """
    points = generate_sector(center, radius, angle, heading)
    return Polygon([(point.x, point.y) for point in points])

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

def is_landing_point_valid(center, obstacles_gdf, radius_m=2.5):
    """
    지정된 착륙지점이 유효한지 확인하는 함수.
    반경 내에 장애물이 없어야 유효한 착륙지점으로 간주.
    
    Parameters:
    - center (shapely.geometry.Point): 착륙지점의 중심 좌표.
    - radius_m (float): 착륙 가능 반경 (미터).
    - obstacles_gdf (geopandas.GeoDataFrame): 장애물 위치가 저장된 GeoDataFrame.
    
    Returns:
    - bool: 착륙지점으로 유효하면 True, 아니면 False.
    """
    # 착륙 반경 내의 원 생성
    landing_circle = center.buffer(radius_m / 111320)  # 미터를 위도/경도로 변환
    # print('center: ', center)
    # print('obstacles_gdf: ', obstacles_gdf)
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

def is_safe(center, obstacles_gdf):
    radius_m = 2.5

    # 착륙 반경 내의 원 생성
    landing_circle = center.buffer(radius_m / 111320)  # 미터를 위도/경도로 변환
    
    # 원 내부에 장애물이 있는지 확인
    for obstacle in obstacles_gdf.geometry:
        if landing_circle.contains(obstacle):
            return False
    return True

def save_final_landing_location(output_file, uam_location, final_landing_location, region):
    """
    최종 착륙지점을 파일로 저장하는 함수.

    Parameters:
    - output_file (str): 저장할 파일 경로 (CSV 또는 GeoJSON).
    - uam_location (Point): UAM의 현재 위치.
    - final_landing_location (Point or None): 최종 착륙지점 (없을 경우 None).
    """
    data = []
    if final_landing_location:
        data.append({
            "Region": region,
            "UAM_Location_Lat": uam_location.y,
            "UAM_Location_Lon": uam_location.x,
            "Final_Landing_Location_Lat": final_landing_location.y,
            "Final_Landing_Location_Lon": final_landing_location.x,
        })
    else:
        data.append({
            "Region": region,
            "UAM_Location_Lat": uam_location.y,
            "UAM_Location_Lon": uam_location.x,
            "Final_Landing_Location_Lat": None,
            "Final_Landing_Location_Lon": None,
        })

    df = pd.DataFrame(data)
    df.to_csv(output_file, mode='a', index=False, header=not pd.io.common.file_exists(output_file))  # append 모드로 저장


# main
def main():
    # 데이터 파일 경로 설정
    file_path = 'results/clustering/region_cluster_analysis.csv'
    cluster_data = load_and_preprocess_data(file_path, polygon=False)

    region_names = ['중구', '동구', '서구', '남구', '북구', '수성', '달서구', '달성군', '군위군']
    region_data_chunks = [cluster_data.iloc[i:i + 30] for i in range(0, len(cluster_data), 30)]  # 30개씩 나누기

    no_data = 0

    output_file = "results/select_landing_location/region_final_landing_locations.csv"  # 저장할 파일 경로

    # for region_name in region_names:
    for region_name, region_chunk in zip(region_names, region_data_chunks):
        print('region_name: ', region_name)
        file_path = f'results/filtering/Database/{region_name}_final_filtered_polygons_with_center.csv'
        processed_data = load_and_preprocess_data(file_path, polygon=True)

        # # cluster_data를 순차적으로 사용
        # for _, row in tqdm(cluster_data.iterrows(), total=len(cluster_data), desc="Processing"):
        # 지역별 데이터 처리
        for _, row in tqdm(region_chunk.iterrows(), total=len(region_chunk), desc=f"Processing {region_name}"):
            uam_location = row['uam_location']
            heading = row['UAM_Heading']
            optimal_safe_center = row['optimal_safe_center']

            # 섹터 생성
            radius_km = 1.8
            radius_deg = radius_km / 111
            sector_angle = 180
            sector_points = generate_sector(uam_location, radius_deg, sector_angle, heading)

            sector_polygon = generate_sector_polygon(uam_location, radius_deg, sector_angle, heading)

            # 장애물 생성
            # num_obstacles = 100
            num_obstacles = 2600
            obstacles_gdf = generate_obstacles_in_polygon(sector_polygon, num_obstacles)

            if is_landing_point_valid(optimal_safe_center, obstacles_gdf):
                final_landing_location = optimal_safe_center
            else:
                print_color("유효한 착륙지점 재탐색 중...", color="yellow")
                
                # 섹터 내 폴리곤 필터링
                filtered_data = processed_data[processed_data['safe_center'].apply(
                    lambda c: is_within_sector(c, uam_location, radius_deg, sector_angle, heading)
                )]

                # 클러스터링 수행
                clusters, vertices_array = perform_dbscan_clustering(filtered_data)

                if vertices_array.size != 0:
                    # 같은 폴리곤이 여러 클러스터에 걸쳐 있는지 확인
                    multiple_cluster_polygons = find_polygons_in_multiple_clusters(filtered_data, clusters, vertices_array)
                    if multiple_cluster_polygons:
                        # 클러스터 병합
                        clusters = merge_clusters(filtered_data, clusters, vertices_array)

                    # 클러스터 속성 계산
                    cluster_areas, cluster_distances, cluster_counts, cluster_safe_center = assign_cluster_properties_new(
                        filtered_data, clusters, vertices_array, uam_location
                    )

                    # 클러스터별 가중치 계산
                    cluster_weights = calculate_cluster_weights_new(cluster_areas, cluster_distances, cluster_counts)

                    # 8. 최적의 클러스터 선택
                    optimal_cluster_id, optimal_weight = select_optimal_cluster(cluster_weights)

                    if optimal_cluster_id is not None:    
                        optimal_polygon = []
                        safe_centers = []
                        # 최적 클러스터에 해당하는 폴리곤 선택
                        for polygon_idx, geom in enumerate(filtered_data['geometry']):
                            coords = np.array(geom.exterior.coords)
                            cluster_labels = [clusters[i] for i, vertex in enumerate(vertices_array) if tuple(vertex) in coords]

                            if cluster_labels[0] == optimal_cluster_id:
                                optimal_polygon.append(geom)
                                safe_centers.append(filtered_data.iloc[polygon_idx]['safe_center'])
                        
                        # 착륙 가능한 safe_center 필터링
                        valid_safe_centers = [
                            center for center in safe_centers
                            if is_landing_point_valid(center, obstacles_gdf)
                        ]

                        # 가장 가까운 착륙지점 선택
                        if valid_safe_centers:
                            final_landing_location = min(
                                valid_safe_centers,
                                key=lambda center: geodesic((uam_location.y, uam_location.x), (center.y, center.x)).meters
                            )
                            print_color(f"선정된 착륙지점: {final_landing_location}", color="green")
                        else:
                            final_landing_location = None
                            print_color("유효한 착륙지점이 없습니다.", color="red")
                            no_data += 1

            # 결과 저장
            save_final_landing_location(output_file, uam_location, final_landing_location, region_name)

        print(f'{region_name} no_data: ', no_data)

    # # 시각화
    # fig, ax = plt.subplots(figsize=(10, 10))
    # gpd.GeoDataFrame(geometry=[sector_polygon], crs="EPSG:4326").plot(ax=ax, facecolor='white', edgecolor='black', label='Sector')
    # obstacles_gdf.plot(ax=ax, color='red', marker='x', markersize=5, label='Obstacles')
    # plt.plot(uam_location.x, uam_location.y, 'g*', markersize=10, label='UAM Location')
    # plt.plot(final_landing_location.x, final_landing_location.y, 'b*', markersize=20, label='final_landing_location')
    # plt.legend()
    # plt.title("UAM Sector and Obstacles")
    # plt.xlabel("Longitude")
    # plt.ylabel("Latitude")
    # plt.grid()
    # plt.show()

# 메인 실행 부분
if __name__ == "__main__":
    main()
