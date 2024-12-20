from library import *
from final_clustering import print_color, generate_sector

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

######################################
def is_safe(center, obstacles_gdf):
    radius_m = 2.5

    # 착륙 반경 내의 원 생성
    landing_circle = center.buffer(radius_m / 111320)  # 미터를 위도/경도로 변환
    
    # 원 내부에 장애물이 있는지 확인
    for obstacle in obstacles_gdf.geometry:
        if landing_circle.contains(obstacle):
            return False
    return True

def save_final_landing_location(output_file, uam_location, final_landing_location):
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
            "UAM_Location_Lat": uam_location.y,
            "UAM_Location_Lon": uam_location.x,
            "Final_Landing_Location_Lat": final_landing_location.y,
            "Final_Landing_Location_Lon": final_landing_location.x,
        })
    else:
        data.append({
            "UAM_Location_Lat": uam_location.y,
            "UAM_Location_Lon": uam_location.x,
            "Final_Landing_Location_Lat": None,
            "Final_Landing_Location_Lon": None,
        })

    df = pd.DataFrame(data)
    df.to_csv(output_file, mode='a', index=False, header=not pd.io.common.file_exists(output_file))  # append 모드로 저장

############################################################
## main ##
def select_landing_site(uam_location, top_cluster_info):
    print_color('Final...','yellow')

    ### 임시 ###
    # 섹터 생성
    radius_km = 1.8
    radius_deg = radius_km / 111
    sector_angle = 360
    sector_points = generate_sector(uam_location, radius_deg, sector_angle, 0)
    sector_polygon = generate_sector_polygon(uam_location, radius_deg, sector_angle, 0)

    # 장애물 생성
    num_obstacles = 2600
    obstacles_gdf = generate_obstacles_in_polygon(sector_polygon, num_obstacles)
    ############

    safe_centers = top_cluster_info[['safe_center']]
    
    # 착륙 가능한 safe_center 필터링
    valid_safe_centers = [
        center for center in top_cluster_info['safe_center']
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
    print_color('='*30,'yellow')
    return final_landing_location
