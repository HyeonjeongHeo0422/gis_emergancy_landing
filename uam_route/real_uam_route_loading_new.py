import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
from shapely import wkt
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import osmnx as ox
import filter
from scipy.spatial import KDTree

def to_point(coordinates):
    """
    위도, 경도 튜플을 입력 받아 Point 객체를 생성합니다.
    
    Parameters:
    - coordinates (tuple): (위도, 경도) 형식의 좌표 튜플
    
    Returns:
    - Point: shapely.geometry.Point 객체로 반환
    """
    # Point는 (경도, 위도) 순서로 생성
    return Point(coordinates[1], coordinates[0])

def get_segment_coords(region_name, tags, place_name, start_point, end_point, tolerance=1.0):
    """
    지정된 지역의 특정 구간 좌표를 추출

    Parameters:
    - region_name (str): 지역 이름 (예: "Daegu, South Korea")
    - place_name (str): 장소 이름 (예: "금호강")
    - start_point (Point): 시작 지점
    - end_point (Point): 끝 지점
    - tolerance (float): 시작점과 끝점을 찾기 위한 거리 허용 오차 

    Returns:
    - List[List[Tuple[float, float]]]: 시작점과 끝점 사이의 좌표 리스트 (구간이 여러 개일 경우 각각 리스트로 반환)
    """
  
    # 장소 데이터 가져오기
    place = ox.geometries_from_place(region_name, tags)
    
    # 지정된 이름으로 필터링
    place_data = place[place["name"] == place_name]
    segment_coords_list = []

    # 구간 좌표 추출
    for line in place_data.geometry.values:
        if line.geom_type == 'LineString':
            line_coords = list(line.coords)
            start_index = next((i for i, coord in enumerate(line_coords) if Point(coord).distance(start_point) < tolerance), None)
            end_index = next((i for i, coord in enumerate(line_coords) if Point(coord).distance(end_point) < tolerance), None)
            
            # 구간 좌표 저장
            if start_index is not None and end_index is not None:
                segment_coords = line_coords[start_index:end_index+1]
                segment_coords_list.append(segment_coords[0])
                
        elif line.geom_type == 'MultiLineString':
            for sub_line in line:
                line_coords = list(sub_line.coords)
                start_index = next((i for i, coord in enumerate(line_coords) if Point(coord).distance(start_point) < tolerance), None)
                end_index = next((i for i, coord in enumerate(line_coords) if Point(coord).distance(end_point) < tolerance), None)
                
                # 구간 좌표 저장
                if start_index is not None and end_index is not None:
                    segment_coords = line_coords[start_index:end_index+1]
                    segment_coords_list.append(segment_coords[0])
                    
    return segment_coords_list

def flatten_list(nested_list):
    """
    중첩된 리스트를 평탄화하여 단일 리스트로 변환하면서 (위도, 경도) 순으로 변환합니다.
    
    Parameters:
    - nested_list (list): 중첩 리스트
    
    Returns:
    - list: (위도, 경도) 순서로 변환된 단일 리스트
    """
    # 중첩 리스트 평탄화 및 (위도, 경도) 순서 변경
    return [(item[1], item[0]) for sublist in nested_list for item in sublist] if any(isinstance(i, list) for i in nested_list) else [(item[1], item[0]) for item in nested_list]

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
    
    waypoints.append(end)   # 구간의 끝 지점을 추가
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

# # 모든 CSV 파일을 로드하고, 웨이포인트 기반으로 필터링하는 함수
# def process_all_csv_files(folder, csv_list, waypoints, buffer_distance=2.5):
#     all_filtered_polygons = []

#     # KDTree를 생성하여 웨이포인트 좌표를 사용한 공간 검색
#     waypoint_tree = KDTree(waypoints)

#     for file_name in csv_list:
#         file_path = os.path.join(folder, file_name)
#         data = pd.read_csv(file_path)

#         # 각 폴리곤의 중심점과 가장 가까운 웨이포인트까지의 거리 계산
#         def is_within_buffer(centroid):
#             centroid_point = Point(eval(centroid))
#             distance, _ = waypoint_tree.query((centroid_point.x, centroid_point.y))
#             return distance <= buffer_distance

#         # 필터링: buffer_distance 이내의 폴리곤만 선택
#         filtered_data = data[data['Centroid'].apply(is_within_buffer)]

#         # WKT 형식으로 저장된 폴리곤 데이터를 shapely Polygon 객체로 변환
#         filtered_polygons = [wkt.loads(row['Polygon']) for _, row in filtered_data.iterrows()]
        
#         # 모든 구의 필터링된 폴리곤을 저장
#         all_filtered_polygons.extend(filtered_polygons)

#     return all_filtered_polygons

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
    ax.scatter(waypoint_x, waypoint_y, color='orange', edgecolor='orange' , label='Waypoints (1km intervals)', s=50)

    selected_uam_points = [uam_route_points[0], uam_route_points[3], uam_route_points[-1]]
    uam_x = [point[1] for point in selected_uam_points]
    uam_y = [point[0] for point in selected_uam_points]
    ax.scatter(uam_x, uam_y, color='blue', label='UAM Route Points', s=100)

    # 범례 생성
    legend_patches = [
        Patch(color='plum', label='Landing Able Sites'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Waypoints (1km intervals)'),  # 원형 범례
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

if __name__ == "__main__":
    # 출발지, 경유지, 도착지 정보
    dongdaegu_station = (35.8796, 128.6284)     # 동대구역
    sincheon_station = (35.87467, 128.61038)    # 신천철로 end point
    sincheon = ((35.904685, 128.592246))        # 신천 end point
    kumhoJC = (35.88881, 128.52540)             # 금호JC
    new_airport = (36.30309, 128.50657)   # 대구경북통합신공항 예정지

    # 추출 장소
    region_name = "Daegu, South Korea"
    river_tags = {"waterway": "river"}
    river_place_name = "금호강"
    highway_tags = {"highway": "motorway"}
    highway_place_name = "중앙고속도로"

    # 구간 좌표 추출
    start_point = to_point(sincheon_station)
    end_point = to_point(kumhoJC)
    river_segment_coords = get_segment_coords(region_name, river_tags, river_place_name, start_point, end_point)

    start_point = to_point(kumhoJC)
    end_point = to_point(new_airport)
    highway_segment_coords = get_segment_coords(region_name, highway_tags, highway_place_name, start_point, end_point)

    # # 결과 출력
    # print("추출된 구간 좌표:", river_segment_coords)
    # print("추출된 구간 좌표:", highway_segment_coords)

    # 좌표 리스트를 평탄화
    flat_river_segment_coords = flatten_list(river_segment_coords)
    flat_highway_segment_coords = flatten_list(highway_segment_coords)

    # uam_route_points 리스트에 각 위치를 (위도, 경도) 형식으로 추가
    uam_route_points = [
        dongdaegu_station,
        sincheon_station,
        sincheon,
        # *flat_river_segment_coords,
        kumhoJC,
        *flat_highway_segment_coords,
        new_airport
    ]

    # uam_route_points = [
    #     (35.8796, 128.6284),  # 동대구역 -> 
    #     (35.87467, 128.61038),  # 신천철로 end point
    #     (35.904685, 128.592246), # 금호강 end point
    #     (35.88881, 128.52540),  # 금호JC
    #     (35.94296, 128.53927),  # 중앙고속도로 waypoint
    #     (35.95123, 128.54948),  # 중앙고속도로 waypoint
    #     (36.00148, 128.55042),  # 중앙고속도로 waypoint
    #     (36.04799, 128.51721),  # 중앙고속도로 waypoint
    #     (36.05805, 128.53523),  # 중앙고속도로 waypoint
    #     (36.2080, 128.5610),    # 중앙고속도로 waypoint
    #     (36.22004, 128.55360),  # 중앙고속도로 waypoint
    #     (36.28081, 128.58175),   # 중앙고속도로 end point
    #     (36.30309, 128.50657)   # 대구경북통합신공항 예정지
    # ]

    # 결과 출력
    print("UAM Route Points:", uam_route_points)
    

# 경계 데이터 경로
boundary_folder_path = 'data/boundary'

# 모든 경계 데이터를 로드
boundary_gdf = load_all_boundary_data(boundary_folder_path)

# 웨이포인트 생성 (1km 간격)
waypoints = generate_waypoints(uam_route_points, interval_km=1)

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
    '남구_final_filtered_polygons.csv'
]
filtered_polygons = process_all_csv_files(folder_path, csv_files, waypoints, buffer_distance=5)  # 반경을 5km로 설정

# CSV로 저장
# save_polygons_to_csv(filtered_polygons, f'results/filtering/UAM/uam_route_filtered_polygons.csv')

# 필터링된 폴리곤을 시각화
fig = visualize_filtered_polygons(boundary_gdf, filtered_polygons, waypoints, uam_route_points)

# 시각화 결과를 파일로 저장
# filter.save_visualization(fig, f'results/filtering/UAM/uam_route_filtered_result.png')




