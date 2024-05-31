import numpy as np
import geopandas as gpd
# from shapely.geometry import MultiLineString, LineString
from scipy.interpolate import griddata
from haversine import haversine, Unit
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from folium import plugins
import contextily as ctx

# 데이터 로드
## 주의: 데이터가 한글로 되어 있기 때문에 encoding='euckr' 없으면 column 글자 깨짐
elevation_points = gpd.read_file("data/수치지형도/북구/N3P_F0020000.shp", encoding='euckr')
elevation_contours = gpd.read_file("data/수치지형도/북구/N3L_F0010000.shp", encoding='euckr')
elevation_contours = elevation_contours.explode()

# 데이터를 WGS 84 좌표계로 변환
elevation_points = elevation_points.to_crs(epsg=4326)
elevation_contours = elevation_contours.to_crs(epsg=4326)

# print(elevation_points)
# print(elevation_contours)

# 등고선에서 고도 정보 추출 및 포인트로 변환
contour_points = elevation_contours.geometry.apply(lambda x: np.array(x.coords))
contour_elevations = np.repeat(elevation_contours['CONT'], contour_points.apply(len))
contour_points = np.concatenate(contour_points.values)

# 표고점 데이터와 등고선 데이터 결합
all_points = np.vstack([contour_points, np.array(list(zip(elevation_points.geometry.x, elevation_points.geometry.y)))])
all_elevations = np.concatenate([contour_elevations, elevation_points['NUME'].values])

# 각 방향의 실제 거리 계산
x_min, y_min, x_max, y_max = elevation_points.total_bounds
distance_x = haversine((y_min, x_min), (y_min, x_max), unit=Unit.METERS)
distance_y = haversine((y_min, x_min), (y_max, x_min), unit=Unit.METERS)

# 10m 간격으로 셀 수 계산
num_x_cells = int(distance_x / 10)
num_y_cells = int(distance_y / 10)

# 그리드 생성
## method 종류: 'nearest', 'linear', 'cubic'
## method='linear'는 선형 보간 방식을 사용한다는 것을 의미.
## 이 방법은 주변 점들 사이의 선형적인 관계를 기반으로 중간 값을 추정. 이는 비교적 부드러운 고도 표면을 생성
grid_x, grid_y = np.mgrid[x_min:x_max:num_x_cells*1j, y_min:y_max:num_y_cells*1j]
# grid_z = griddata(all_points, all_elevations, (grid_x, grid_y), method='nearest')
grid_z = griddata(all_points, all_elevations, (grid_x, grid_y), method='linear')
# grid_z = griddata(all_points, all_elevations, (grid_x, grid_y), method='cubic')

# 경사도 계산
x, y = np.gradient(grid_z, axis=(0, 1), edge_order=1)
slope = np.sqrt(x**2 + y**2)
slope_degrees = np.arctan(slope) * (180 / np.pi)
slope_percent = np.tan(np.radians(slope_degrees)) * 100  # 경사도 백분율

# 경사도 데이터와 해당 좌표를 하나의 배열로 저장
coordinates_and_slope = np.zeros(slope_percent.shape, dtype=[('latitude', float), ('longitude', float), ('slope_percent', float)])

# 배열 크기에 따른 반복문 조정
for i in range(slope_percent.shape[0]):  # y축 크기
    for j in range(slope_percent.shape[1]):  # x축 크기
        lat = y_min + (i + 0.5) * (y_max - y_min) / slope_percent.shape[0]
        lon = x_min + (j + 0.5) * (x_max - x_min) / slope_percent.shape[1]
        coordinates_and_slope[i, j] = (lat, lon, slope_percent[i, j])

# # 경사도 데이터와 위도, 경도 범위를 함께 저장
# np.savez('/content/slope_data.npz', slope_percent=slope_percent, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max)

# # # 시각화
# extent = [x_min, x_max, y_min, y_max]
# # plt.figure(figsize=(10, 6))
# # plt.title('Terrain Slope Visualization')
# # plt.imshow(slope_percent, extent=extent, cmap='terrain', interpolation='none')
# # plt.xlabel('Longitude')
# # plt.ylabel('Latitude')
# # plt.colorbar(label='Slope (%)')
# # plt.show()

# # slope_percent에서 20 이하인 값만 강조
# low_slope_mask = slope_percent <= 20
# highlighted_slope = np.ma.masked_where(~low_slope_mask, slope_percent)  # 조건을 만족하지 않는 곳을 마스킹

# # 20% 이하만 강조하여 표시
# plt.figure(figsize=(10, 6))
# plt.title('Terrain Safe Slope Visualization')
# plt.imshow(highlighted_slope, extent=extent, cmap='summer', interpolation='none')  # 투명도를 조정하여 위에 겹쳐서 표시
# plt.xlabel('Longitude')
# plt.ylabel('Latitude')
# plt.colorbar(label='Slope (%)')
# plt.show()


# print('folium 지도 생성 ..ing')
# # folium 지도 생성
# center_lat = (y_min + y_max) / 2
# center_lon = (x_min + x_max) / 2
# m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# # 경사도 20% 이하인 부분만 GeoJson으로 추가
# for i in range(coordinates_and_slope.shape[0]):
#     for j in range(coordinates_and_slope.shape[1]):
#         lat = coordinates_and_slope['latitude'][i, j]
#         lon = coordinates_and_slope['longitude'][i, j]
#         slope = coordinates_and_slope['slope_percent'][i, j]
#         if slope <= 20:
#             folium.Circle(
#                 location=[lat, lon],
#                 radius=5,
#                 color='green',
#                 fill=True,
#                 fill_color='green'
#             ).add_to(m)

# print("지도를 HTML 파일로 저장 ..ing")
# # 지도를 HTML 파일로 저장
# m.save('slope_map.html')

# print("end")


# # 경사도 데이터와 해당 좌표를 하나의 배열로 저장
# coordinates_and_slope = []
# lat_grid = []
# lon_grid = []
# for i in range(slope_percent.shape[0]):  # y축 크기
#     lat_row = []
#     lon_row = []
#     for j in range(slope_percent.shape[1]):  # x축 크기
#         lat = y_min + (i + 0.5) * (y_max - y_min) / slope_percent.shape[0]
#         lon = x_min + (j + 0.5) * (x_max - x_min) / slope_percent.shape[1]
#         lat_row.append(lat)
#         lon_row.append(lon)
#         coordinates_and_slope.append((lat, lon, slope_percent[i, j]))
#     lat_grid.append(lat_row)
#     lon_grid.append(lon_row)

# lat_grid = np.array(lat_grid)
# lon_grid = np.array(lon_grid)

# 지도 시각화
fig, ax = plt.subplots(figsize=(10, 10))
# elevation_contours.plot(ax=ax, color='blue', alpha=0.5)
# elevation_points.plot(ax=ax, color='blue', markersize=5)

# # 경사도 데이터를 색상으로 표현하여 전체 데이터를 표시
# sc = ax.scatter(lon_grid, lat_grid, c=slope_percent, cmap='terrain', s=1, alpha=0.6)

# # 컬러바 추가
# cbar = plt.colorbar(sc, ax=ax, label='Slope (%)')

# 경사도 데이터를 imshow로 시각화
extent = [x_min, x_max, y_min, y_max]
im = ax.imshow(slope_percent, extent=extent, origin='lower', cmap='terrain')

# 컬러바 추가
cbar = plt.colorbar(im, ax=ax, label='Slope (%)')

# 배경 타일 추가
# ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik)

plt.title('Terrain Slope Visualization')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.show()