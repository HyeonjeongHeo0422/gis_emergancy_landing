import geopandas as gpd
import numpy as np
from scipy.interpolate import griddata
from shapely.geometry import Polygon, Point, MultiPolygon
import matplotlib.pyplot as plt

# 데이터 로드 및 변환
elevation_points = gpd.read_file("data/수치지형도/북구/N3P_F0020000.shp", encoding='euckr')
elevation_contours = gpd.read_file("data/수치지형도/북구/N3L_F0010000.shp", encoding='euckr').explode()

# 데이터를 WGS 84 좌표계로 변환
elevation_points = elevation_points.to_crs(epsg=4326)
elevation_contours = elevation_contours.to_crs(epsg=4326)

# LineString을 Polygon으로 변환
polygons = []
for geom in elevation_contours.geometry:
    if geom.is_ring:
        # LineString이 폐쇄되어 있으면 Polygon 생성
        polygons.append(Polygon(geom))

# 모든 Polygon을 하나의 MultiPolygon으로 결합
multi_polygon = MultiPolygon(polygons)

# 등고선으로부터 외곽선 추출
# boundary = elevation_contours.unary_union.convex_hull
# 등고선으로부터 외곽선 추출이 아니라 이미 생성된 multi_polygon을 사용
boundary = multi_polygon

# 멀티폴리곤 시각화
fig, ax = plt.subplots()
gpd.GeoSeries(boundary).plot(ax=ax, color='blue')
plt.show()

# 등고선 포인트 데이터 생성
contour_points = np.array([(x, y) for geom in elevation_contours.geometry for x, y in geom.coords])
contour_elevations = np.repeat(elevation_contours['CONT'], [len(geom.coords) for geom in elevation_contours.geometry])

# 그리드 생성
x_min, y_min, x_max, y_max = boundary.bounds
num_cells = 500
grid_x, grid_y = np.mgrid[x_min:x_max:num_cells*1j, y_min:y_max:num_cells*1j]

# 그리드 포인트가 경계 내에 있는지 검사
grid_points = np.vstack([grid_x.ravel(), grid_y.ravel()]).T
# polygon = Polygon(boundary)
# inside = np.array([polygon.contains(Point(x, y)) for x, y in grid_points]).reshape(grid_x.shape)
inside = np.array([boundary.contains(Point(x, y)) for x, y in grid_points]).reshape(grid_x.shape)

# # 보간 수행
# grid_z = griddata(contour_points, contour_elevations, (grid_x, grid_y), method='cubic')

# # 경계 밖은 NaN 처리
# grid_z[~inside] = np.nan

# # 시각화
# plt.figure(figsize=(10, 6))
# plt.imshow(grid_z, extent=(x_min, x_max, y_min, y_max), origin='lower', cmap='terrain')
# plt.colorbar(label='Elevation (m)')
# plt.title('Terrain Visualization with Actual Boundary')
# plt.show()

# 멀티폴리곤 시각화 주석 처리된 부분을 제거하고 실제 시각화 코드로 포함
fig, ax = plt.subplots()
gpd.GeoSeries(boundary).plot(ax=ax, color='blue')
plt.show()