import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union

# 데이터 로드 및 변환
elevation_points = gpd.read_file("data/수치지형도/북구/N3P_F0020000.shp", encoding='euckr')
elevation_contours = gpd.read_file("data/수치지형도/북구/N3L_F0010000.shp", encoding='euckr').explode()

# 데이터를 WGS 84 좌표계로 변환
elevation_points = elevation_points.to_crs(epsg=4326)
elevation_contours = elevation_contours.to_crs(epsg=4326)

# 시각화
fig, ax = plt.subplots(figsize=(10, 10))  # 그림 크기 조정
elevation_points.plot(ax=ax, column='NUME', cmap='terrain', legend=True)  # 'CONT' 열을 사용하여 색상 구분
plt.title('Elevation Points Visualization')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.grid(True)  # 그리드 추가

# 시각화
fig, ax = plt.subplots(figsize=(10, 10))  # 그림 크기 조정
elevation_contours.plot(ax=ax, column='CONT', cmap='terrain', legend=True)  # 'CONT' 열을 사용하여 색상 구분
plt.title('Elevation Contours Visualization')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.grid(True)  # 그리드 추가

# 모든 등고선을 합쳐 하나의 경계를 생성
unified_boundary = elevation_contours.unary_union

# 합쳐진 경계의 외곽선 추출
boundary = unified_boundary.boundary

# 시각화
fig, ax = plt.subplots(figsize=(10, 10))
gpd.GeoSeries(boundary).plot(ax=ax, color='blue', linewidth=1)  # 경계선만 표시
plt.title('Outer Boundary Visualization')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.grid(True)
# plt.show()


# 데이터 단순화 (각 지오메트리에 simplify 적용)
elevation_contours['geometry'] = elevation_contours['geometry'].apply(lambda x: x.simplify(0.001))

# 모든 등고선을 합쳐 하나의 경계를 생성
all_boundaries = unary_union(elevation_contours.geometry)

# 시각화
fig, ax = plt.subplots(figsize=(10, 10))
gpd.GeoSeries(all_boundaries).plot(ax=ax, color='blue', linewidth=1)
plt.title('Unified Outer Boundary Visualization')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.grid(True)
plt.show()
