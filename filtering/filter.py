import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from tqdm import tqdm
import time
from scipy.spatial import Delaunay
from scipy.ndimage import gaussian_gradient_magnitude
import matplotlib.colors as mcolors
from haversine import haversine, Unit
from scipy.spatial import KDTree
import os
import pickle

#####################################################################
# 1. 데이터 필터링
# 데이터 로드(임상도, 산림입지토양도까지 고려)
def load_data(exclusion_files, forest_file, soil_file, boundary_file):
    print('Data Load START!')

    """
    :param exclusion_files: 제외할 영역 파일 목록
    :param forest_file: 임상도 파일 경로
    :param soil_file: 산림입지토양도 파일 경로
    :param boundary_file: 경계 파일 경로
    :return: exclusion_data, boundary_gdf
    """
    # 착륙 불가능 지역 데이터를 모두 하나의 GeoDataFrame으로 합치기
    exclusion_data_list = [gpd.read_file(file) for file in exclusion_files]
    
    # 임상도 데이터 추가
    forest_data = gpd.read_file(forest_file)
    # forest_data.set_crs(epsg=5179, inplace=True)  # 초기 좌표계 설정 (좌표계: UTM-K(EPSG: 5179))
    # forest_data['AGCLS_CD'] = forest_data['AGCLS_CD'].astype(int)  # AGCLS_CD 컬럼을 정수형으로 변환
    
    # None 값을 제외하고 정수형으로 변환
    forest_data['AGCLS_CD'] = forest_data['AGCLS_CD'].dropna().astype(int)

    forest_exclusion_data = forest_data[~forest_data['AGCLS_CD'].isin([0, 1])]
    
    # 산림입지토양도 데이터 추가
    soil_data = gpd.read_file(soil_file)
    soil_exclusion_data = soil_data[soil_data['SLTP_CD'].isin(['03', '04', '12', '19', '91', '95', '97'])]
    
    # 모든 데이터를 동일한 좌표계로 변환 후 결합
    all_exclusion_data = exclusion_data_list + [forest_exclusion_data, soil_exclusion_data]
    all_exclusion_data = [data.to_crs(epsg=4326) for data in all_exclusion_data]
    exclusion_data = gpd.GeoDataFrame(pd.concat(all_exclusion_data, ignore_index=True))

    # 남구 경계 데이터 생성
    # boundary_data = pd.read_csv(boundary_file)
    # boundary_coords = boundary_data[['Longitude', 'Latitude']].values
    # boundary_polygon = Polygon(boundary_coords)
    # boundary_gdf = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[boundary_polygon])
    
    boundary_gdf = load_boundary_data(boundary_file)

    print('Data Load Complete!!')
    return exclusion_data, boundary_gdf

def load_boundary_data(boundary_file):
    """
    주어진 boundary_file에서 경계 데이터를 로드하여 boundary_gdf로 변환합니다.
    
    :param boundary_file: 경계 파일 경로 (CSV 형식)
    :return: boundary_gdf (GeoDataFrame)
    """
    # boundary_file에서 데이터 읽기
    boundary_data = pd.read_csv(boundary_file)
    
    # 위도와 경도 좌표로부터 폴리곤 생성
    boundary_coords = boundary_data[['Longitude', 'Latitude']].values
    boundary_polygon = Polygon(boundary_coords)
    
    # GeoDataFrame으로 변환
    boundary_gdf = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[boundary_polygon])
    
    return boundary_gdf

# 데이터 전처리
def first_filtering(exclusion_data, boundary_gdf):
    """
    :param exclusion_data: 제외할 영역 데이터
    :param boundary_gdf: 경계 데이터
    :return: polygons, boundary_gdf, exclusions_in_boundary, landing_able_sites
    """    
    # 남구 경계 내에서 착륙 불가능 지역을 클리핑
    exclusions_in_boundary = gpd.overlay(exclusion_data, boundary_gdf, how='intersection')
    
    # 착륙 불가능 지역을 차감
    boundary_geom = boundary_gdf.geometry[0]
    exclusions_union = unary_union(exclusions_in_boundary.geometry)
    landing_able_sites = boundary_geom.difference(exclusions_union)
    
    # 각 폴리곤 추출
    polygons = []
    if landing_able_sites.geom_type == 'Polygon':
        polygons.append(landing_able_sites)
    elif landing_able_sites.geom_type == 'MultiPolygon':
        for geom in landing_able_sites.geoms:
            polygons.append(geom)
    
    # return polygons, boundary_gdf, exclusions_in_boundary, landing_able_sites
    return polygons

#####################################################################
# 2. 면적 필터링
# 폴리곤 내부에 점들을 생성하는 함수
def generate_candidate_points(polygon, num_points=3):
    # print('generate_candidate_points ...ing')
    minx, miny, maxx, maxy = polygon.bounds
    candidate_centers = []

    # polygon 내부의 한 점 (representative_point)
    rep_point = polygon.representative_point()
    candidate_centers.append(rep_point)

    for _ in range(num_points):
        # while True:
        for _ in range(10):  # 최대 10번 시도
            p = Point(np.random.uniform(minx, maxx), np.random.uniform(miny, maxy))
            if polygon.contains(p):
                candidate_centers.append(p)
                break

    return candidate_centers

def can_place_circle(polygon, radius):
    # print('can_place_circle ...ing')
    """
    :param polygon: 폴리곤 (EPSG:4326 좌표계)
    :param radius: 원의 반지름 (단위: 미터)
    :return: (bool, Point) 원이 들어갈 수 있는지 여부와 중심점
    """

    if polygon.is_empty or not polygon.is_valid:
        return False, None

    # 좌표계를 EPSG:3857로 변환
    # EPSG:3857은 일반적으로 미터(meter) 단위를 사용하는 투영 좌표계
    polygon_3857 = gpd.GeoSeries([polygon], crs='EPSG:4326').to_crs(epsg=3857).iloc[0]

    # candidate_centers 생성 (좌표계 변환 후)
    candidate_centers = generate_candidate_points(polygon_3857, num_points=3)

    best_center = None
    for center in candidate_centers:
        if polygon_3857.contains(center):
            # 반지름이 radius인 원을 생성하여 폴리곤 내부에 완전히 포함되는지 확인
            buffer = center.buffer(radius)
            if polygon_3857.contains(buffer):
                # 원이 폴리곤 내부에 완전히 포함되면 그 중심을 best_center로 설정
                best_center = center
                break  # 적합한 중심점을 찾았으므로 종료

    return best_center is not None, best_center if best_center else None

# 2차 필터링 함수
def second_filtering(polygons, radius):
    """
    :param polygons: 폴리곤 리스트
    :param radius: 원의 반지름 (미터 단위)
    :return: 필터링된 폴리곤 리스트와 데이터프레임
    """
    print('filter_landing_zones START!!')

    # 진행률 표시를 위한 tqdm 사용
    fit_results = [can_place_circle(polygon, radius) for polygon in tqdm(polygons, desc='Processing polygons')]

    # 원이 들어갈 수 있는 폴리곤만 필터링
    filtered_polygons = [polygon for polygon, result in zip(polygons, fit_results) if result[0]]
    centers = [result[1] for result in fit_results if result[0]]

    # 필터링된 결과로 데이터프레임 생성
    polygons_df = pd.DataFrame({
        'Polygon': filtered_polygons,
        'Center Point': centers
    })

    return filtered_polygons, polygons_df

# 후보지 선정
def filter_landing_zones(polygons, radius):
    print('filter_landing_zones START!!')
    """
    :param polygons: 폴리곤 리스트
    :param radius: 원의 반지름
    :return: 후보지 데이터프레임
    """
    # tqdm을 사용하여 진행률 표시
    fit_results = [can_place_circle(polygon, radius) for polygon in tqdm(polygons, desc='Processing polygons')]
    can_fit = [result[0] for result in fit_results]
    centers = [result[1] for result in fit_results]

    # 데이터프레임 생성
    polygons_df = pd.DataFrame({
        'Polygon': polygons,
        'Can Fit Circle': can_fit,
        'Center Point': centers
    })
    
    return polygons_df

#####################################################################
# 3. 경사도 필터링
# 경사도 비율을 퍼센트로 변환
def slope_to_percent(slope):
    return slope * 100

# 경사도 비율을 도(degree)로 변환
def slope_to_degrees(slope):
    return np.degrees(np.arctan(slope))

def find_nearest_elevation_point(poly_center, elevation_points):
    """
    폴리곤 중심에 가장 가까운 2개의 고도 점 찾기
    :param poly_center: 폴리곤의 중심 좌표 (Point)
    :param elevation_points: 고도 점 데이터 (GeoDataFrame)
    :return: 가장 가까운 고도점 2개 (GeoDataFrame)
    """
    if elevation_points.empty:
        print("Elevation points dataset is empty.")
        return None

    # 고도점들의 (위도, 경도) 좌표 추출
    coords = elevation_points.geometry.apply(lambda geom: (geom.y, geom.x)).tolist()

    # KDTree를 사용하여 폴리곤 중심점과 가장 가까운 고도점 찾기
    tree = KDTree(coords)
    poly_coord = (poly_center.y, poly_center.x)  # haversine은 (위도, 경도) 순서

    # 가장 가까운 2개의 이웃 점 찾기
    num_points=2
    distances, indices = tree.query(poly_coord, k=num_points)
    
    # 가장 가까운 점 2개를 추출
    nearest_points = elevation_points.iloc[indices]

    # # 디버깅: 가장 가까운 점들과 그 거리 출력
    # for i, idx in enumerate(indices):
    #     haversine_distance = haversine(poly_coord, coords[idx], unit=Unit.METERS)
    #     print(f"Nearest Point {i+1} Index: {idx}")
    #     print(f"Nearest Point {i+1} Distance (meters): {haversine_distance}")
    #     print(f"Nearest Point {i+1} Coordinates: {coords[idx]}")

    return nearest_points


def calculate_slopes_within_polygon(points, polygon, elevation_points):
    """
    고도 점 데이터를 이용해 폴리곤 내 이웃한 점들 사이의 경사도를 계산
    :param points: 고도 점 데이터 (GeoDataFrame)
    :param polygon: 현재 폴리곤
    :param elevation_points: 전체 고도 점 데이터 (GeoDataFrame)
    :return: 각 점 쌍 사이의 경사도 리스트
    """
    if len(points) < 2:
        # 폴리곤 중심에서 가까운 고도 점을 찾아 추가
        poly_center = polygon.centroid
        nearest_points = find_nearest_elevation_point(poly_center, elevation_points)
        points = pd.concat([nearest_points], ignore_index=True)

    coords = np.array([p.coords[0] for p in points.geometry])
    elevations = points['NUME'].values

    slopes = []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            # 위도와 경도를 거리 단위로 변환
            dx = haversine_distance(coords[i], coords[j])  # TODO: using haversine library 
            dz = abs(elevations[i] - elevations[j])
            slope = dz / dx if dx != 0 else 0
            slope_percent = slope_to_percent(slope)
            slopes.append(slope_percent)

    return slopes

def haversine_distance(coord1, coord2):
    """
    두 좌표 사이의 거리를 계산합니다 (단위: 미터).
    :param coord1: 첫 번째 좌표 (경도, 위도)
    :param coord2: 두 번째 좌표 (경도, 위도)
    :return: 두 좌표 사이의 거리 (미터)
    """
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371000  # 지구 반지름 (미터)
    
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    
    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c

# 고도 데이터를 폴리곤과 결합하여 면적, 평균 고도, 최대 고도 정보를 추가
def add_elevation_to_polygons(polygons, elevation_points, elevation_contours, target_crs='EPSG:5179'):
    """
    각 폴리곤에 고도 데이터를 추가하고 면적, 평균 고도, 최대 고도 정보를 계산합니다.
    :param polygons: 폴리곤 리스트
    :param elevation_points: 고도 점 데이터 (GeoDataFrame)
    :param elevation_contours: 등고선 데이터 (GeoDataFrame)
    :param target_crs: 면적 계산을 위한 투영 좌표계 (기본값: 'EPSG:5179')
    :return: 각 폴리곤의 면적, 고도 및 경사도를 포함하는 DataFrame
    """
    polygon_data = []

    for poly in polygons:
        if elevation_points.crs != 'EPSG:4326':
            elevation_points = elevation_points.to_crs('EPSG:4326')
        if elevation_contours.crs != 'EPSG:4326':
            elevation_contours = elevation_contours.to_crs('EPSG:4326')

        # 폴리곤 내의 고도 점 데이터
        points_within = elevation_points[elevation_points.geometry.within(poly)]
        contours_within = elevation_contours[elevation_contours.geometry.within(poly)]
        
        # if points_within.empty and contours_within.empty:
        #     print('empty')
        #     continue

        if points_within.empty:
            continue

        # 고도 점 데이터에서 고도 추출
        point_elevations = points_within['NUME'].values if not points_within.empty else []
        contour_elevations = contours_within['CONT'].values if not contours_within.empty else []

        # 고도 데이터 결합
        elevations = np.concatenate([point_elevations, contour_elevations])

        if len(elevations) < 2:
            continue

        # 좌표계를 변환하여 면적 계산
        poly_projected = gpd.GeoSeries([poly], crs='EPSG:4326').to_crs(target_crs)
        area = poly_projected.area.values[0]  # m^2 단위의 면적 계산

        # 평균 고도 및 최대 고도 계산
        mean_elevation = np.mean(elevations) if elevations.size > 0 else np.nan
        max_elevation = np.max(elevations) if elevations.size > 0 else np.nan

        # 각 폴리곤의 경사도 계산
        # slopes = calculate_slopes_within_polygon(points_within)
        slopes = calculate_slopes_within_polygon(points_within, poly, elevation_points)

        polygon_data.append({
            'Polygon': poly,
            'Area (m^2)': area,
            'Mean Elevation': mean_elevation,
            'Max Elevation': max_elevation,
            'Slopes': slopes
        })

    return pd.DataFrame(polygon_data)

# 안전 경사도를 지닌 폴리곤만 추출하는 함수
def extract_safe_slopes(polygons_with_elevation, safe_threshold=10):
    """
    안전 경사도를 지닌 폴리곤만 추출합니다.
    :param polygons_with_elevation: 경사도가 추가된 폴리곤 데이터프레임
    :param safe_threshold: 안전 경사도의 임계값 (기본값: 10%)
    :return: 안전 경사도를 지닌 폴리곤 리스트
    """
    safe_polygons = polygons_with_elevation[
        polygons_with_elevation['Slopes'].apply(lambda slopes: np.mean(slopes) <= safe_threshold)
    ]['Polygon'].tolist()

    return safe_polygons

#####################################################################

# 결과 저장 및 시각화
# 결과 저장
def save_results(landing_candidates, filepath):
    """
    :param landing_candidates_df: 후보지 데이터프레임
    :param filepath: 저장할 파일 경로
    """
    # 'Can Fit Circle'이 True인 값만 필터링
    landing_candidates_df = landing_candidates[landing_candidates['Can Fit Circle']]
    landing_candidates_df[['Polygon']].to_csv(filepath, index=False)

# filtered_polygons를 pickle 파일로 저장
def save_polygons_to_pickle(polygons, filepath):
    directory = os.path.dirname(filepath)
    
    # 디렉터리가 없으면 생성
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(filepath, 'wb') as f:
        pickle.dump(polygons, f)
    print(f"Polygons saved to {filepath}")

# 저장된 pickle 파일 불러오기
def load_polygons_from_pickle(filepath):
    with open(filepath, 'rb') as f:
        polygons = pickle.load(f)
    return polygons


# # 시각화 결과 저장
# def save_visualization(fig, filepath):
#     """
#     :param fig: 시각화 결과가 포함된 matplotlib.figure.Figure 객체
#     :param filepath: 저장할 파일 경로
#     """
#     fig.savefig(filepath)

# 시각화 결과 저장
def save_visualization(fig, filepath):
    """
    :param fig: 시각화 결과가 포함된 matplotlib.figure.Figure 객체
    :param filepath: 저장할 파일 경로
    """
    # 디렉터리 존재 여부 확인 및 생성
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # 시각화 결과를 지정된 경로에 저장
    try:
        fig.savefig(filepath, bbox_inches='tight')
        print(f"Visualization saved at {filepath}")
    except Exception as e:
        print(f"Failed to save the visualization: {e}")

# 결과 시각화
# 1차 필터링 결과 시각화
def visualize_filtered_polygons(boundary_gdf, filtered_polygons):
    """
    1차 필터링된 폴리곤을 시각화
    :param boundary_gdf: 경계 데이터
    :param filtered_polygons: 1차 필터링된 폴리곤 리스트 (shapely.geometry.Polygon 또는 MultiPolygon 객체)
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

    # 수동으로 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.5, label='Landing Able Sites'),
        Patch(facecolor='white', edgecolor='green', alpha=0.5, label='No landing Area')
    ]
    ax.legend(handles=legend_patches)

    # 축 및 제목 설정
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Polygons with First Filtered Polygons')

    # 결과 시각화 표시
    plt.show()

    return fig

# 결과 시각화
def visualize_results(boundary_gdf, landing_candidates, landing_able_sites, exclusions_in_boundary):
    """
    :param boundary_gdf: 경계 데이터
    :param landing_candidates: 후보지 데이터프레임
    :param landing_able_sites: 착륙 가능한 영역
    :param exclusions_in_boundary: 제외 영역
    :return: fig1, fig2
    """
    fig1, ax1 = plt.subplots(1, 1, figsize=(10, 10))
    boundary_gdf.plot(ax=ax1, color='white', edgecolor='black')

    # 각 폴리곤에서 반지름이 20m인 원 시각화
    for i, row in landing_candidates.iterrows():
        if row['Can Fit Circle']:
            # 폴리곤 시각화
            gpd.GeoSeries([row['Polygon']], crs='epsg:4326').plot(ax=ax1, color='green', alpha=0.5)

    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')

    # 수동으로 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.5, label='Landing Able Sites'),
        Patch(facecolor='white', edgecolor='green', alpha=0.5, label='No landing Area')
    ]
    ax1.legend(handles=legend_patches)

    fig2, ax2 = plt.subplots(1, 1, figsize=(10, 10))
    boundary_gdf.plot(ax=ax2, color='white', edgecolor='black')
    gpd.GeoSeries(landing_able_sites).plot(ax=ax2, color='green', alpha=0.5, label='Landing Able Sites')
    exclusions_in_boundary.plot(ax=ax2, color='white', alpha=0.5, label='No landing Area')

    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Latitude')

    # 수동으로 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.5, label='Landing Able Sites'),
        Patch(facecolor='white', edgecolor='green', alpha=0.5, label='No landing Area')
    ]
    ax2.legend(handles=legend_patches)

    plt.show()

    return fig1, fig2

def visualize_slope(boundary_gdf, polygons_with_elevation):
    """
    각 폴리곤의 경사도를 시각화합니다.
    :param boundary_gdf: 경계 데이터
    :param polygons_with_elevation: 경사도가 추가된 폴리곤 데이터프레임
    :return: fig
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

    # 경사도를 색상으로 구분하여 시각화
    max_slope = max(max(slopes) for slopes in polygons_with_elevation['Slopes'] if slopes)
    polygons_with_elevation['Color'] = polygons_with_elevation['Slopes'].apply(
        lambda slopes: plt.cm.viridis(np.mean(slopes) / max_slope) if slopes else (0, 0, 0, 0)
    )

    for _, row in polygons_with_elevation.iterrows():
        poly = row['Polygon']
        color = row['Color']
        gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color=color, alpha=0.6)

    # 범례 추가
    norm = mcolors.Normalize(vmin=0, vmax=max_slope)
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label('Slope(%)')

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Polygons with Slope')

    plt.show()

    return fig

# 안전 경사도와 위험 경사도 구분 및 시각화
def visualize_slope_with_risk(boundary_gdf, polygons_with_elevation, safe_threshold=10):
    """
    각 폴리곤의 경사도를 안전(10% 이하)과 위험(10% 초과)으로 구분하여 시각화합니다.
    :param boundary_gdf: 경계 데이터
    :param polygons_with_elevation: 경사도가 추가된 폴리곤 데이터프레임
    :param safe_threshold: 안전 경사도의 임계값 (기본값: 10%)
    :return: fig
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

    # 경사도를 안전과 위험으로 구분하여 시각화
    for _, row in polygons_with_elevation.iterrows():
        poly = row['Polygon']
        slopes = row['Slopes']
        if not slopes:
            continue
        
        mean_slope = np.mean(slopes)
        if mean_slope <= safe_threshold:
            color = 'green'  # 안전 경사도
        else:
            color = 'red'  # 위험 경사도

        gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color=color, alpha=0.6)

    # 수동으로 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.6, label='Safe Slope (<= 10%)'),
        Patch(color='red', alpha=0.6, label='Risky Slope (> 10%)')
    ]
    ax.legend(handles=legend_patches)

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Polygons with Safe and Risky Slopes')

    plt.show()

    return fig

# 안전 경사도를 가진 폴리곤만 시각화하는 함수
def visualize_safe_polygons(boundary_gdf, safe_polygons):
    """
    안전 경사도를 가진 폴리곤만 시각화합니다.
    :param boundary_gdf: 경계 데이터
    :param safe_polygons: 안전 경사도를 지닌 폴리곤 리스트
    :return: fig
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

    # 안전한 경사도를 가진 폴리곤 시각화 (녹색)
    for poly in safe_polygons:
        gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color='green', alpha=0.6)

    # 수동으로 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.6, label='Safe Slope (<= 10%)')
    ]
    ax.legend(handles=legend_patches)

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Polygons with Safe Slopes')

    plt.show()

    return fig

# 고도 점 데이터 시각화 함수
def visualize_elevation_points_within_polygons(polygons_with_elevation, elevation_points, boundary_gdf):
    """
    폴리곤 내부의 고도 점들을 고도 수치에 따라 시각화합니다.
    :param polygons_with_elevation: 고도 및 경사도 정보가 포함된 폴리곤 데이터프레임
    :param elevation_points: 고도 점 데이터 (GeoDataFrame)
    :param boundary_gdf: 경계 데이터 (GeoDataFrame)
    """
    fig, ax = plt.subplots(1, 1, figsize=(8, 12))
    
    # 경계 데이터 시각화
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black') 

    # 폴리곤 시각화 
    for _, row in polygons_with_elevation.iterrows():
        poly = row['Polygon']
        gpd.GeoSeries([poly]).plot(ax=ax, color='green', alpha=0.4, edgecolor='none')

    # 고도 값에 따라 색상 맵을 생성
    max_elevation = 150
    min_elevation = 0
    norm = mcolors.Normalize(vmin=min_elevation, vmax=max_elevation)
    cmap = plt.cm.viridis

    # 폴리곤 내부의 고도 점 시각화
    for _, row in polygons_with_elevation.iterrows():
        poly = row['Polygon']
        points_within = elevation_points[elevation_points.geometry.within(poly)]
        
        if not points_within.empty:
            # 고도에 따라 색상을 설정하여 점을 플롯
            sc = ax.scatter(
                points_within.geometry.x, 
                points_within.geometry.y, 
                c=points_within['NUME'], 
                cmap=cmap, 
                norm=norm,
                s=5
            )

    # Colorbar를 수동으로 추가
    cbar = plt.colorbar(sc, ax=ax, orientation="vertical")
    cbar.set_label('Elevation')
    
    ax.set_title('Elevation Points within Selected Polygons by Elevation')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    plt.show()


#####################################################################
# 디버깅 코드
def print_polygons_and_slopes(polygons_with_elevation):
    """
    각 폴리곤의 ID와 경사도를 출력합니다.
    :param polygons_with_elevation: 경사도가 추가된 폴리곤 데이터프레임
    """
    for idx, row in polygons_with_elevation.iterrows():
        poly_id = idx  # 인덱스를 폴리곤 ID로 사용
        slopes = row['Slopes']
        print(f"Polygon ID: {poly_id}, Slopes: {slopes}")
