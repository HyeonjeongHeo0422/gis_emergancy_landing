# result_analysis.py
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiLineString, Point, LineString
import matplotlib.pyplot as plt
from clustering_new import generate_sector, is_within_sector, load_and_preprocess_data, visualize_polygons_and_sector
# from clustering_new import *
from tqdm import tqdm
from geopy.distance import geodesic
import numpy as np
from shapely.ops import substring
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

def generate_waypoints_along_route(route_points, interval_m=40):
    # 경로 포인트를 LineString으로 변환
    route_line = LineString([(point[1], point[0]) for point in route_points])  # (경도, 위도) 순서

    # 좌표계를 EPSG:3857로 변환하여 거리 계산 단위를 미터로 변경
    projected_line = gpd.GeoSeries([route_line], crs='epsg:4326').to_crs(epsg=3857).iloc[0]
    total_length_m = projected_line.length  # 총 길이 (미터 단위)

    # 필요한 웨이포인트 수 계산
    num_waypoints = int(np.floor(total_length_m / interval_m))

    waypoints = []
    for i in range(num_waypoints + 1):
        # 현재 위치까지의 비율 계산
        fraction = (i * interval_m) / total_length_m
        if fraction > 1.0:
            fraction = 1.0
        # LineString에서 해당 위치의 점 추출
        point = projected_line.interpolate(fraction * projected_line.length)
        # 좌표를 EPSG:4326로 변환하여 저장
        lon, lat = gpd.GeoSeries([point], crs='epsg:3857').to_crs(epsg=4326).iloc[0].coords[0]
        waypoints.append((lat, lon))  # (위도, 경도) 순서
    return waypoints

# 각 웨이포인트 구간의 heading을 계산하는 함수
def calculate_heading(start, end):
    """
    두 웨이포인트 사이의 heading(방위각)을 계산합니다.
    북쪽을 90도로 기준으로 하여 결과를 반환합니다.
    """
    dx = end[1] - start[1]  # 경도 차이
    dy = end[0] - start[0]  # 위도 차이
    angle = math.degrees(math.atan2(dy, dx))  # 라디안에서 각도로 변환
    heading = angle % 360
    return heading

# 마지막 도착지로부터 1.8km 거리 계산 함수
def is_within_radius(current_point, destination_point, radius_km):
    """
    두 지점 사이의 거리가 특정 반경 내에 있는지 확인합니다.
    
    Parameters:
    - current_point: tuple, 현재 지점의 (위도, 경도)
    - destination_point: tuple, 기준점의 (위도, 경도)
    - radius_km: float, 반경 거리 (킬로미터)
    
    Returns:
    - bool, 반경 내에 있는지 여부
    """
    return geodesic(current_point, destination_point).km <= radius_km

# 필터링된 폴리곤 데이터를 로드
# file_path = 'results/filtering/UAM/uam_route_filtered_polygons_new.csv'
# file_path = 'results/filtering/UAM/uam_route_filtered_polygons_4km.csv'
file_path = 'results/filtering/UAM/uam_route_filtered_polygons_4km_with_center.csv'
processed_data = load_and_preprocess_data(file_path)

# 시작점과 종료점
start_point = (35.88881, 128.52540) # 금호JC
# end_point = (36.28081, 128.58175)   # 대구경북통합신공항 예정지 부근
end_point = (36.2539, 128.5676)   # 대구경북통합신공항 예정지 부근

# GeoJSON 파일 불러오기
highway_file_path = 'data/geojson/export.geojson'       # 중앙고속도로

# 추출된 구간의 좌표
highway_coords = extract_segment_coordinates(highway_file_path, start_point, end_point)

# UAM 경로의 웨이포인트 생성 (40m 간격)
uam_route_points = [
    (35.8796, 128.6284),  # 동대구역 -> 
    (35.87467, 128.61038),  # 신천철로 end point
    (35.904685, 128.592246), # 금호강 end point
    (35.88881, 128.52540),  # 금호JC
    *highway_coords,  # 중앙고속도로 웨이포인트
    (36.30309, 128.50657)   # 대구경북통합신공항 예정지
]

waypoints = generate_waypoints_along_route(uam_route_points, interval_m=40)

# 시각화할 반경, 각도, 헤딩 설정
radius_km = 1.8
radius_deg = radius_km / 111
sector_angle = 180   # sector range: [heading-90, heading+90]

# 마지막 도착지 좌표
final_destination = waypoints[-1]

# 수정된 웨이포인트 필터링
filtered_waypoints = [
    wp for wp in waypoints if not is_within_radius(wp, final_destination, radius_km)
]
print('the number of waypoints: ', len(filtered_waypoints))

# 데이터 저장을 위한 리스트 초기화
waypoint_data = []

# 각 웨이포인트에 대한 섹터 내 후보지 시각화 및 데이터 저장
for i in range(len(filtered_waypoints) - 1):
    # 현재 웨이포인트와 다음 웨이포인트 간의 heading을 계산
    current_waypoint = waypoints[i]
    next_waypoint = waypoints[i + 1]
    heading = calculate_heading(current_waypoint, next_waypoint)
    
    # 현재 웨이포인트 위치 설정
    uam_location = Point(current_waypoint[1], current_waypoint[0])  # (경도, 위도)
    sector_points = generate_sector(uam_location, radius_deg, sector_angle, heading)

    # 섹터 내 후보지 필터링
    filtered_data = processed_data[processed_data['centroid'].apply(
        lambda c: is_within_sector(c, uam_location, radius_deg, sector_angle, heading)
    )]

    # # 'Area (m^2)'를 'Area'로 사용
    # if 'Area (m^2)' in filtered_data.columns:
    #     # filtered_data.rename(columns={'Area (m^2)': 'Area'}, inplace=True)
    #     filtered_data.rename(columns={'Area (m^2)': 'Area'})

    # 'Area (m^2)'를 'Area'로 변경 (필요시)
    if 'Area (m^2)' in filtered_data.columns:
        filtered_data = filtered_data.rename(columns={'Area (m^2)': 'Area'})

    # 면적을 km²로 변환
    filtered_data['Area (km^2)'] = filtered_data['Area'] / 1e6

    candidate_count = len(filtered_data)
    # print('filtered_data: ', filtered_data)
    # print('candidate_count: ', candidate_count)

    max_area = filtered_data['Area (km^2)'].max() if not filtered_data.empty else 0

    # 데이터 저장
    waypoint_data.append({
        'waypoint_lat': current_waypoint[0],
        'waypoint_lon': current_waypoint[1],
        'heading': heading,
        'candidate_count': candidate_count,
        'max_area': max_area
    })
    
    # 필요에 따라 시각화
    # visualize_polygons_and_sector(filtered_data, sector_points, uam_location)

# # 후보지 평균 개수 계산
# average_candidates = np.mean([entry['candidate_count'] for entry in waypoint_data])
# average_max_area = df['max_area'].mean()
# print(f"평균 후보지 개수: {average_candidates:.2f}")
# print(f"평균 최대 면적 (km²): {average_max_area:.2f}")

# # 평균 후보지 개수를 각 데이터에 추가
# for entry in waypoint_data:
#     entry['average_candidate_count'] = average_candidates

# 데이터프레임으로 변환하여 CSV 파일로 저장
df = pd.DataFrame(waypoint_data)
# df.to_csv('results/filtering/UAM/waypoint_analysis_new_IC.csv', index=False, encoding='utf-8')
# print("waypoint_analysis.csv 파일로 저장 완료")


# 결과 분석 #

# 후보지 평균 개수 계산
average_candidates = df['candidate_count'].mean()

# 최대 면적의 평균 계산
average_max_area = df['max_area'].mean()

# 결과 출력
print(f"평균 후보지 개수: {average_candidates:.2f}")
print(f"평균 최대 면적 (km²): {average_max_area:.2f}")

fig, ax1 = plt.subplots(figsize=(12, 6))

# 첫 번째 Y축: 후보지 개수
ax1.plot(
    df.index, 
    df['candidate_count'], 
    linestyle='-', 
    linewidth=2, 
    color='black', 
    label='Candidate Count'
)
ax1.set_xlabel('Waypoint Index', fontsize=20)
ax1.set_ylabel('Candidate Count', fontsize=20, color='black')
ax1.tick_params(axis='y', labelsize=20, colors='black')
ax1.tick_params(axis='x', labelsize=20)
ax1.grid(alpha=0.5)

# 두 번째 Y축: 최대 면적
ax2 = ax1.twinx()
ax2.plot(
    df.index, 
    df['max_area'], 
    linestyle='--', 
    linewidth=2, 
    color='blue', 
    label='Max Area (km²)'
)
ax2.set_ylabel('Max Area (km²)', fontsize=20, color='black')
ax2.tick_params(axis='y', labelsize=20, colors='black')

# 범례 추가
# fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9), fontsize=20)
fig.legend(
    loc="upper center",  # 범례 위치를 상단 가운데로 설정
    bbox_to_anchor=(0.5, 0.95),  # 가운데 정렬을 위해 x=0.5로 설정, y=1.1로 약간 위로 이동
    fontsize=20
    # ncol=2  # 범례를 두 열로 나열
)

# 그래프 제목
# plt.title('Candidate Count and Maximum Area for Each Waypoint', fontsize=20)

plt.tight_layout()
# plt.show()

