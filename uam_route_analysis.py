import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiLineString, Point
from shapely import wkt
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import osmnx as ox
import filter
from tqdm import tqdm
import math

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

# GeoJSON 파일 불러오기
# river_file_path = 'data/geojson/kumho_river.geojson'    # 금호강
highway_file_path = 'data/geojson/export.geojson'       # 중앙고속도로

# # 시작점과 종료점
# start_point = (35.87467, 128.61038)  # 신천철로 end point
# end_point = (35.88881, 128.52540),  # 금호JC

# # 추출된 구간의 좌표
# river_coords = extract_segment_coordinates(river_file_path, start_point, end_point)

# 시작점과 종료점
start_point = (35.88881, 128.52540) # 금호JC
end_point = (36.28081, 128.58175)   # 대구경북통합신공항 예정지 부근

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

# 중심점(centroid)과 웨이포인트 사이의 거리를 계산하여 최소 거리를 반환하는 함수
def calculate_min_distance(centroid, waypoints):
    centroid_coords = (centroid[1], centroid[0])  # (위도, 경도) 형식으로 변환
    # 각 웨이포인트와의 거리 계산 후 최소 거리 반환
    return min(geodesic(centroid_coords, waypoint).km for waypoint in waypoints)

# Waypoints 사이의 거리가 1km 이상일 때만 유효한 웨이포인트로 선택
def filter_waypoints(waypoints, interval_km=1):
    filtered_waypoints = [waypoints[0]]  # 첫 번째 웨이포인트 추가
    last_added = waypoints[0]

    for waypoint in waypoints[1:]:
        if geodesic(last_added, waypoint).km >= interval_km:
            filtered_waypoints.append(waypoint)
            last_added = waypoint

    return filtered_waypoints

# 모든 CSV 파일을 로드하고, 필터링된 웨이포인트 기반으로 거리 계산을 줄인 함수
def process_all_csv_files(folder, csv_list, waypoints, buffer_distance=2.5):
    # 웨이포인트 필터링: 1km 이상 떨어진 웨이포인트만 포함
    filtered_waypoints = filter_waypoints(waypoints)
    
    all_filtered_polygons = []
    
    # 전체 파일의 진행률 확인
    for file_name in tqdm(csv_list, desc="Processing CSV Files"):
        file_path = os.path.join(folder, file_name)
        data = pd.read_csv(file_path)
        
        # 각 폴리곤의 중심점과 필터링된 웨이포인트 사이의 거리를 계산하고, buffer_distance 이내의 폴리곤만 필터링
        data['Distance_to_UAM_route'] = data['Centroid'].apply(eval).apply(lambda centroid: calculate_min_distance(centroid, filtered_waypoints))
        
        # 필터링된 데이터를 얻기 위한 진행률
        filtered_data = data[data['Distance_to_UAM_route'] <= buffer_distance]
        
        # tqdm을 사용하여 각 행별 진행률을 표시
        filtered_polygons = []
        for _, row in tqdm(filtered_data.iterrows(), desc=f"Processing polygons in {file_name}", total=len(filtered_data)):
            filtered_polygons.append(wkt.loads(row['Polygon']))
        
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

# 팔공산 국립공원의 경계 데이터를 가져오는 함수
def get_palgongsan_boundary():
    # 'boundary'가 'national_park'인 팔공산 국립공원의 경계 데이터 가져오기
    place_name = "Palgongsan National Park, South Korea"
    tags = {"boundary": "national_park"}
    palgongsan_boundary = ox.geometries_from_place(place_name, tags)
    
    # 경계 데이터에서 multipolygon 형태의 데이터만 필터링
    palgongsan_boundary = palgongsan_boundary[palgongsan_boundary.geometry.type == 'Polygon']
    
    return palgongsan_boundary

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

    # 팔공산 국립공원의 경계 데이터 가져오기
    palgongsan_boundary = get_palgongsan_boundary()
    
    # 팔공산 국립공원 경계 시각화 (연한 녹색)
    palgongsan_boundary.plot(ax=ax, color='lightgreen', edgecolor='green', alpha=0.5, linewidth=2, label='Palgongsan National Park')

    # 필터링된 폴리곤 시각화
    for poly in filtered_polygons:
        gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color='plum')

    # 웨이포인트 시각화 (오렌지색)
    waypoint_x = [point[1] for point in waypoints]
    waypoint_y = [point[0] for point in waypoints]
    ax.scatter(waypoint_x, waypoint_y, color='orange', edgecolor='orange' , label='Waypoints', s=50)

    selected_uam_points = [uam_route_points[0], uam_route_points[3], uam_route_points[-1]]
    uam_x = [point[1] for point in selected_uam_points]
    uam_y = [point[0] for point in selected_uam_points]
    ax.scatter(uam_x, uam_y, color='blue', label='UAM Route Points', s=100)

    # 범례 생성
    legend_patches = [
        Patch(color='plum', label='Landing Able Sites'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Waypoints'),  # 원형 범례
        Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='UAM Route Points')  # 원형 범례
    ]
    ax.legend(handles=legend_patches)

    # 축 및 제목 설정
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    # 결과 시각화 표시
    plt.show()

    return fig

def save_polygons_to_csv(polygons, output_file):
    # EPSG:4326 좌표계를 사용한 GeoSeries 생성
    polygons_gs = gpd.GeoSeries(polygons, crs='epsg:4326')
    
    # EPSG:3857 좌표계로 변환하여 면적 계산
    polygons_gs_3857 = polygons_gs.to_crs(epsg=3857)
    
    # 면적 계산
    areas = polygons_gs_3857.area
    
    # 중심점(centroid) 계산
    centroids = polygons_gs.representative_point()
    
    # 폴리곤을 WKT 형식으로 변환
    polygons_wkt = [polygon.wkt for polygon in polygons]
    
    # 중심점 좌표를 (lon, lat) 형식으로 변환
    centroids_coords = [(point.x, point.y) for point in centroids]
    
    # 데이터프레임으로 변환
    df = pd.DataFrame({
        'Polygon': polygons_wkt,
        'Area (m^2)': areas,
        'Centroid': centroids_coords
    })
    
    # CSV 파일로 저장
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Polygons saved to {output_file}")

# 경계 데이터 경로
boundary_folder_path = 'data/boundary'

# 모든 경계 데이터를 로드
boundary_gdf = load_all_boundary_data(boundary_folder_path)

# 웨이포인트 생성 (1km 간격)
waypoints_part1 = generate_waypoints(uam_route_points[0:4], interval_km=1)
waypoints_part2 = generate_waypoints([highway_coords[-1], uam_route_points[-1]], interval_km=1)

# 두 부분을 결합하여 최종 waypoints 리스트 생성
waypoints = waypoints_part1 + waypoints_part2

# 중앙고속도로 추가
waypoints.extend(highway_coords)

# 모든 CSV 파일을 처리 (웨이포인트를 기준으로 필터링)
folder_path = 'results/filtering/Database/not_center'
csv_files = [
    '달성군_final_filtered_polygons.csv',
    '달서구_final_filtered_polygons.csv',
    '군위군_final_filtered_polygons.csv',
    '중구_final_filtered_polygons.csv',
    '수성_final_filtered_polygons.csv',
    '서구_final_filtered_polygons.csv',
    '동구_final_filtered_polygons.csv',
    '북구_final_filtered_polygons.csv',
    '남구_final_filtered_polygons.csv',
    '칠곡_final_filtered_polygons.csv',
    '구미_final_filtered_polygons.csv'
]
filtered_polygons = process_all_csv_files(folder_path, csv_files, waypoints, buffer_distance=4)  # 반경을 4km로 설정

# 40m 간격으로 웨이포인트 생성 함수
def generate_40m_waypoints(route_points, interval_km=0.04):
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

# 웨이포인트 생성 (1km 간격)
waypoints = generate_40m_waypoints(uam_route_points, interval_km=0.04)

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
    point_angle = (math.degrees(math.atan2(dy, dx)) - heading) % 360

    return -angle / 2 <= point_angle <= angle / 2

# UAM 전방 반경 180도 내 후보지 개수 계산 함수
def count_candidates_within_sector(waypoints, filtered_polygons, radius_km=1.8, angle=180):
    candidate_counts = []
    
    for waypoint in tqdm(waypoints, desc="Counting candidates within sector"):
        waypoint_point = Point(waypoint[1], waypoint[0])  # (경도, 위도) 형식
        count = 0
        
        for poly in filtered_polygons:
            centroid = poly.centroid
            if is_within_sector(centroid, waypoint_point, radius_km, angle, 90):  # heading은 0으로 가정
                count += 1
        
        candidate_counts.append(count)
    
    return candidate_counts

# 필터링된 폴리곤을 기준으로 UAM 전방 반경 180도 내 후보지 개수를 계산
candidate_counts = count_candidates_within_sector(waypoints, filtered_polygons)
# print('candidate_counts')
# print(candidate_counts)
# 후보지 개수 평균 계산
average_candidates = np.mean(candidate_counts)
print(f"평균 후보지 개수: {average_candidates}")

# 전체 후보지 개수와 필터링된 후보지 개수 계산
total_candidates = sum([len(pd.read_csv(os.path.join(folder_path, file))) for file in csv_files])
filtered_candidates = len(filtered_polygons)
reduction_rate = (total_candidates - filtered_candidates) / total_candidates * 100

# 행정구역별 후보지 개수 계산 함수
def count_candidates_by_region(csv_list, folder_path):
    region_counts = {}
    
    for file_name in csv_list:
        file_path = os.path.join(folder_path, file_name)
        data = pd.read_csv(file_path)
        region_name = file_name.replace('_final_filtered_polygons.csv', '')
        region_counts[region_name] = len(data)
    
    return region_counts

# 행정구역별 후보지 개수 계산
region_candidate_counts = count_candidates_by_region(csv_files, folder_path)

# 결과를 CSV 파일로 저장
results_df = pd.DataFrame({
    'Waypoint Index': list(range(len(candidate_counts))),
    'Candidates Within Sector': candidate_counts
})
results_df.loc['Average'] = results_df['Candidates Within Sector'].mean()
results_df.to_csv('results/filtering/UAM/candidate_counts_180degree.csv', index=False, encoding='utf-8')

# 행정구역별 후보지 개수를 CSV 파일로 저장
# region_counts_df = pd.DataFrame(list(region_candidate_counts.items()), columns=['Region', 'Candidate Count'])
# region_counts_df.to_csv('results/filtering/UAM/region_candidate_counts.csv', index=False, encoding='utf-8')

# 후보지 감소율 저장
with open('results/filtering/UAM/summary_180degree.txt', 'w') as f:
    f.write(f"전체 후보지 개수: {total_candidates}\n")
    f.write(f"필터링된 후보지 개수: {filtered_candidates}\n")
    f.write(f"후보지 감소율: {reduction_rate:.2f}%\n")
    f.write(f"평균 후보지 개수 (UAM 전방 180도 반경 내): {average_candidates:.2f}\n")
    f.write("\n행정구역별 후보지 개수:\n")
    for region, count in region_candidate_counts.items():
        f.write(f"{region}: {count}\n")