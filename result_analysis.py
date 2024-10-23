import osmnx as ox
import geopandas as gpd
import pandas as pd
import contextily as ctx
import matplotlib.pyplot as plt
import xyzservices.providers as xyz
import matplotlib.patheffects as pe  # 글자 테두리를 위한 패스 이펙트 추가
import pickle
from matplotlib.patches import Patch
from pyproj import Transformer

# 착륙 가능 지역 데이터를 불러오는 함수
def load_polygons_from_pickle(filepath):
    with open(filepath, 'rb') as f:
        polygons = pickle.load(f)
    return polygons

# # 필터링된 폴리곤 시각화 함수
# def visualize_filtered_polygons(boundary_gdf, filtered_polygons):
#     if not filtered_polygons:
#         print("No polygons to visualize.")
#         return None

#     # 시각화 준비
#     fig, ax = plt.subplots(figsize=(10, 10))

#     # 경계 데이터 시각화
#     boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

#     # 전체 필터링된 폴리곤 시각화 (경계 내부로 클리핑)
#     for poly in filtered_polygons:
#         clipped_poly = gpd.clip(gpd.GeoSeries([poly], crs='epsg:4326'), boundary_gdf)
#         clipped_poly.plot(ax=ax, color='green', alpha=0.6)

#     # # 전체 필터링된 폴리곤 시각화
#     # for poly in all_filtered_polygons:
#     #     gpd.GeoSeries([poly], crs='epsg:4326').plot(ax=ax, color='green', alpha=0.6)

#     # 범례 생성
#     legend_patches = [
#         Patch(color='green', alpha=0.5, label='Landing Able Sites'),
#     ]
#     ax.legend(handles=legend_patches)

#     # # 각 구 이름을 경계의 중심에 표시
#     # for name, gdf in gdfs:
#     #     if name == "Dalseong-gun":
#     #         # 좌측
#     #         ax.text(128.4458, 35.8792, "Dalseong-gun", fontsize=12, ha='center', va='center', color='black', 
#     #         path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가

#     #         # 하단
#     #         ax.text(128.4911, 35.7239, "Dalseong-gun", fontsize=12, ha='center', va='center', color='black', 
#     #         path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가
#     #     else:
#     #         centroid = gdf.geometry.centroid.iloc[0]  # 구 경계의 중심 좌표 계산
#     #         ax.text(centroid.x, centroid.y, name, fontsize=12, ha='center', va='center', color='black', 
#     #                 path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가

#     # 축 및 제목 설정
#     ax.set_xlabel('Longitude')
#     ax.set_ylabel('Latitude')
#     ax.set_title('Polygons with Filtered Landing Areas')

#     plt.show()

#     return fig

# 필터링된 폴리곤 시각화 함수 (경계 내부의 폴리곤만 시각화)
def visualize_filtered_polygons(boundary_gdf, filtered_polygons):
    if not filtered_polygons:
        print("No polygons to visualize.")
        return None

    # 경계와 필터링된 폴리곤의 CRS를 UTM 또는 적절한 투영 좌표계로 변환
    # EPSG:5179는 한국에서 자주 사용하는 UTM-K 좌표계입니다.
    projected_crs = 'EPSG:5179'
    
    boundary_gdf = boundary_gdf.to_crs(projected_crs)
    
    clipped_polygons = []

    for poly in filtered_polygons:
        gdf_poly = gpd.GeoSeries([poly], crs='epsg:4326')  # 필터링된 폴리곤이 EPSG:4326 기준
        gdf_poly = gdf_poly.to_crs(projected_crs)  # 투영 좌표계로 변환
        clipped_poly = gpd.clip(gdf_poly, boundary_gdf)
        if not clipped_poly.is_empty.any():
            clipped_polygons.append(clipped_poly)

    # 시각화 준비
    fig, ax = plt.subplots(figsize=(10, 10))

    # 경계 데이터 시각화
    boundary_gdf.plot(ax=ax, color='white', edgecolor='black')

    # 클리핑된 폴리곤 시각화
    for clipped_poly in clipped_polygons:
        clipped_poly.plot(ax=ax, color='green', alpha=0.6)

    # 범례 생성
    legend_patches = [
        Patch(color='green', alpha=0.5, label='Landing Able Sites'),
    ]
    ax.legend(handles=legend_patches)

    # 각 구 이름을 경계의 중심에 표시 (투영 좌표계에서 정확한 중심 계산)
    for name, gdf in gdfs:
        gdf = gdf.to_crs(projected_crs)  # 경계 데이터를 투영 좌표계로 변환
        if name == "Dalseong-gun":
            # EPSG:4326에서 EPSG:5179로 좌표 변환을 위한 변환기
            transformer = Transformer.from_crs('EPSG:4326', 'EPSG:5179', always_xy=True)

            # 하드코딩할 좌표 변환 (예시: Dalseong-gun의 좌표)
            dalseong_coords_1 = transformer.transform(128.4458, 35.8792)  # 좌측
            dalseong_coords_2 = transformer.transform(128.4911, 35.7239)  # 하단

            # 좌측
            ax.text(dalseong_coords_1[0], dalseong_coords_1[1], "Dalseong-gun", fontsize=12, ha='center', va='center', color='black',
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가

            # 하단
            ax.text(dalseong_coords_2[0], dalseong_coords_2[1], "Dalseong-gun", fontsize=12, ha='center', va='center', color='black',
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가
        else:
            centroid = gdf.geometry.centroid.iloc[0]  # 투영 좌표계에서 구 경계의 중심 좌표 계산
            ax.text(centroid.x, centroid.y, name, fontsize=12, ha='center', va='center', color='black',
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가

    # 축 및 제목 설정
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Polygons with Filtered Landing Areas Inside Boundaries')

    plt.show()

    return fig

# 대구광역시 각 구의 이름 목록
districts = ["Nam-gu, Daegu, South Korea", "Dalseo-gu, Daegu, South Korea", "Dong-gu, Daegu, South Korea",
             "Buk-gu, Daegu, South Korea", "Seo-gu, Daegu, South Korea", "Suseong-gu, Daegu, South Korea",
             "Jung-gu, Daegu, South Korea", "Dalseong-gun, Daegu, South Korea", "Gunwi-gun, Daegu, South Korea"]

# 각 구의 경계 데이터를 저장할 GeoDataFrame 리스트
gdfs = []

# 각 구의 경계 데이터를 OpenStreetMap에서 가져오기
for district in districts:
    gdf = ox.geocode_to_gdf(district)
    gdfs.append((district.split(',')[0], gdf))  # 구 이름과 경계 데이터를 함께 저장

# 경계 데이터만 추출하여 병합
gdf_combined = gpd.GeoDataFrame(pd.concat([gdf for _, gdf in gdfs], ignore_index=True))

# 지도 시각화
fig, ax = plt.subplots(figsize=(10, 10))
gdf_combined.boundary.plot(ax=ax, edgecolor='yellow', linewidth=2, linestyle='-.')

# 각 구 이름을 경계의 중심에 표시
for name, gdf in gdfs:
    if name == "Dalseong-gun":
        # 좌측
        ax.text(128.4458, 35.8792, "Dalseong-gun", fontsize=12, ha='center', va='center', color='black', 
        path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가

        # 하단
        ax.text(128.4911, 35.7239, "Dalseong-gun", fontsize=12, ha='center', va='center', color='black', 
        path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가
    else:
        centroid = gdf.geometry.centroid.iloc[0]  # 구 경계의 중심 좌표 계산
        ax.text(centroid.x, centroid.y, name, fontsize=12, ha='center', va='center', color='black', 
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])  # 글자 테두리 흰색 추가

# 배경 지도 추가 (ESRI 위성 타일)
ctx.add_basemap(ax, crs=gdf_combined.crs.to_string(), source=ctx.providers.Esri.WorldImagery, attribution=False)

plt.title("Daegu Metropolitan City District Boundaries")
# plt.show()

#################################

# 각 구의 착륙 가능 지역 파일 경로
files = {
    'Nam-gu': 'results/filtering/3차/남구_final_filtered_polygons.pkl',
    'Dalseo-gu': 'results/filtering/3차/달서구_final_filtered_polygons.pkl',
    'Dong-gu': 'results/filtering/3차/동구_final_filtered_polygons.pkl',
    'Buk-gu': 'results/filtering/3차/북구_final_filtered_polygons.pkl',
    'Seo-gu': 'results/filtering/3차/서구_final_filtered_polygons.pkl',
    'Suseong-gu': 'results/filtering/3차/수성_final_filtered_polygons.pkl',
    'Jung-gu': 'results/filtering/3차/중구_final_filtered_polygons.pkl',
    'Dalseong-gun': 'results/filtering/3차/달성군_final_filtered_polygons.pkl',
    'Gunwi-gun': 'results/filtering/3차/군위군_final_filtered_polygons.pkl',
}

# # 각 구에 대한 착륙 가능 지역 시각화
# for name, gdf in gdfs:
#     # 각 구의 착륙 가능 지역 파일 불러오기
#     filtered_polygons = load_polygons_from_pickle(files[name])

#     # 경계 데이터를 시각화하고, 착륙 가능 지역을 표시
#     visualize_filtered_polygons(gdf, filtered_polygons)

# 모든 착륙 가능 지역을 하나의 리스트로 통합
all_filtered_polygons = []
for name, file_path in files.items():
    # if name == 'Dong-gu':
    #     continue
    filtered_polygons = load_polygons_from_pickle(file_path)
    all_filtered_polygons.extend(filtered_polygons)  # 모든 착륙 가능 지역을 하나로 합침

# 모든 구의 경계 데이터를 병합
boundary_gdf = gpd.GeoDataFrame(pd.concat([gdf for _, gdf in gdfs], ignore_index=True))

# 전체 착륙 가능 지역을 시각화
visualize_filtered_polygons(boundary_gdf, all_filtered_polygons)
