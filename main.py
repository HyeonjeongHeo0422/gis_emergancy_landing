import filter
import geopandas as gpd
from geopy.geocoders import Nominatim
import pandas as pd

# def save_polygons_to_csv(polygons, output_file):
#     # EPSG:4326 좌표계를 사용한 GeoSeries 생성
#     polygons_gs = gpd.GeoSeries(polygons, crs='epsg:4326')
    
#     # EPSG:3857 좌표계로 변환하여 면적 계산
#     polygons_gs_3857 = polygons_gs.to_crs(epsg=3857)
    
#     # 면적 계산
#     areas = polygons_gs_3857.area
    
#     # 중심점(centroid) 계산
#     centroids = polygons_gs.representative_point()
    
#     # 폴리곤을 WKT 형식으로 변환
#     polygons_wkt = [polygon.wkt for polygon in polygons]
    
#     # 중심점 좌표를 (lon, lat) 형식으로 변환
#     centroids_coords = [(point.x, point.y) for point in centroids]
    
#     # 데이터프레임으로 변환
#     df = pd.DataFrame({
#         'Polygon': polygons_wkt,
#         'Area (m^2)': areas,
#         'Centroid': centroids_coords
#     })
    
#     # CSV 파일로 저장
#     df.to_csv(output_file, index=False, encoding='utf-8')
#     print(f"Polygons saved to {output_file}")

def save_polygons_to_csv(polygons, centers, output_file):
    print('polygons')
    print(polygons)
    print('-'*10)
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

    # centers의 좌표를 EPSG:3857로 변환
    # 변환 전 centers 좌표를 확인
    print("Original centers :", centers)

    centers_gs = gpd.GeoSeries(centers, crs='epsg:3857').to_crs(epsg=4326)
    # centers_gs_3857 = centers_gs.to_crs(epsg=3857)
    print('-'*10)

    # 변환 후 centers 좌표 확인
    print("Transformed centers (EPSG:3857):", centers_gs)

    center_points_coords = [(point.x, point.y) if point else (None, None) for point in centers_gs]
    
    # center_points_coords = [(point.x, point.y) if point else (None, None) for point in centers]
    
    # 데이터프레임으로 변환
    df = pd.DataFrame({
        'Polygon': polygons_wkt,
        'Area (m^2)': areas,
        'Centroid': centroids_coords,
        'Safe Center Point': center_points_coords
    })
    
    # CSV 파일로 저장
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Polygons saved to {output_file}")


def main():
    # 데이터 파일 경로 설정 #
    # 구 이름을 변수로 정의
    # region_names = ['중구', '동구', '서구', '남구', '북구', '수성', '달서구', '달성군', '군위군']
    region_names = ['칠곡', '구미']
    for region_name in region_names:
        # if region_name!='중구':
        #     continue
        print('region_name: ', region_name)

        # 제외할 영역 파일 경로들
        if (region_name=='칠곡') or (region_name=='구미'):
            # 제외할 영역 파일 경로들
            exclusion_files = [
                f"data/road_shp/{region_name}/N3A_A0010000.shp",        # 도로
                f"data/road_shp/{region_name}/N3A_A0160024.shp",        # 도로
                f"data/building_shp/{region_name}/N3A_B0010000.shp",    # 건물
                f"data/강하천/{region_name}/N3A_E0010001.shp",            # 강하천
                f"data/강하천/{region_name}/N3A_E0032111.shp",            # 강하천
                f"data/강하천/{region_name}/N3A_E0052114.shp",            # 강하천
            ]
        else:
            exclusion_files = [
                f"data/road_shp/{region_name}/(B021)연속수치지도(대구광역시 {region_name})_N3A_A0010000/N3A_A0010000.shp",    # 도로
                f"data/road_shp/{region_name}/(B021)연속수치지도(대구광역시 {region_name})_N3A_A0160024/N3A_A0160024.shp",    # 도로
                f"data/building_shp/{region_name}/N3A_B0010000/N3A_B0010000.shp",     # 건물
                f"data/강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0010001/N3A_E0010001.shp",     # 강하천
                f"data/강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0032111/N3A_E0032111.shp",     # 강하천
                f"data/강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0052114/N3A_E0052114.shp",     # 강하천
            ]  

        # 임상도 파일 경로
        forest_file_map = {
            '남구': 'TB_FGDI_FS_IM5000_27200',
            '북구': 'TB_FGDI_FS_IM5000_27230',
            '동구': 'TB_FGDI_FS_IM5000_27140',
            '서구': 'TB_FGDI_FS_IM5000_27170',
            '수성': 'TB_FGDI_FS_IM5000_27260',
            '중구': 'TB_FGDI_FS_IM5000_27110',
            '달서구': 'TB_FGDI_FS_IM5000_27290',
            '달성군': 'TB_FGDI_FS_IM5000_27710',
            '군위군': 'TB_FGDI_FS_IM5000_47720',
            '칠곡': 'TB_FGDI_FS_IM5000_47850',
            '구미': 'TB_FGDI_FS_IM5000_47190'
        }
        # 해당 구 이름에 맞는 파일명 선택
        if region_name in forest_file_map:
            file_name = forest_file_map[region_name]
            forest_file = f"data/임상도/{region_name}/{file_name}.shp"
        else:
            raise ValueError(f"Invalid region name: {region_name}")

        # 산림입지토양도 파일 경로
        if (region_name=='칠곡') or (region_name=='구미'):
            soil_file_map = {
                '칠곡': 'TB_FGDI_FS_IJ5000_PG_47850',
                '구미': 'TB_FGDI_FS_IJ5000_PG_47190'
            }
            # 해당 구 이름에 맞는 파일명 선택
            if region_name in soil_file_map:
                file_name = soil_file_map[region_name]
                soil_file = f"data/산림입지토양도/{region_name}/{file_name}.shp"
            else:
                raise ValueError(f"Invalid region name: {region_name}")
        else:
            soil_file = "data/산림입지토양도/27.shp"                        
        
        boundary_file = f'data/boundary/{region_name}_boundary.csv'  # 경계 파일 경로


        # 필터링 #
        # 1. 착륙 제한 지역 필터링 (1차 필터링)
        # 데이터가 이미 저장되어 있다면, 로드
        try:
            first_filtered_polygons = filter.load_polygons_from_pickle(f'results/filtering/1차/{region_name}_first_filtered_polygons.pkl')
            boundary_gdf = filter.load_boundary_data(boundary_file)
        except FileNotFoundError:
            # 저장된 파일이 없으면 필터링 진행
            exclusion_data, boundary_gdf = filter.load_data(exclusion_files, forest_file, soil_file, boundary_file)
            first_filtered_polygons= filter.first_filtering(exclusion_data, boundary_gdf)
            
            # 필터링된 데이터를 저장
            filter.save_polygons_to_pickle(first_filtered_polygons, f'results/filtering/1차/{region_name}_first_filtered_polygons.pkl')

        # 결과 분석 (면적 및 폴리곤 개수 계산)
        boundary_area = boundary_gdf.to_crs(epsg=3857).area.sum()  # 경계 면적 계산 (EPSG:3857 좌표계로 변환 후 면적 계산)
        print(f"필터링 전 전체 영역 면적: {int(boundary_area)} m^2")
        
        first_filtered_area = gpd.GeoSeries(first_filtered_polygons, crs='epsg:4326').to_crs(epsg=3857).area.sum()
        print(f"1차 필터링 후 착륙 가능한 영역 면적: {int(first_filtered_area)} m^2")
        print(f"1차 필터링 면적 비율: {first_filtered_area/boundary_area*100:.2f} %")
        
        num_polygons = len(first_filtered_polygons)
        print(f"1차 필터링 폴리곤 개수: {num_polygons}")
        print('----------------------------')

        # # 결과 분석 (시각화)
        # # 1차 필터링 결과 시각화
        # fig = filter.visualize_filtered_polygons(boundary_gdf, first_filtered_polygons)

        # # 시각화 결과를 파일로 저장
        # filter.save_visualization(fig, f'results/filtering/1차/{region_name}_first_filtered_result.png')


        # 2. 면적 필터링 (2차 필터링)
        try:
            second_filtered_polygons = filter.load_polygons_from_pickle(f'results/filtering/2차/{region_name}_second_filtered_polygons.pkl')
            centers = [None] * len(second_filtered_polygons)
        except FileNotFoundError:
            # 저장된 파일이 없으면 필터링 진행
            # RADIUS = 20     # m
            UAM_SIZE = 10
            RADIUS = 2.5*UAM_SIZE/2     # m
            # second_filtered_polygons, _ = filter.second_filtering(first_filtered_polygons, RADIUS)
            second_filtered_polygons, centers = filter.second_filtering(first_filtered_polygons, RADIUS)
            
            # 필터링된 데이터를 저장
            filter.save_polygons_to_pickle(second_filtered_polygons, f'results/filtering/2차/{region_name}_second_filtered_polygons.pkl')
        
        # 결과 분석 (면적 계산)
        second_filtered_area = gpd.GeoSeries(second_filtered_polygons, crs='epsg:4326').to_crs(epsg=3857).area.sum()
        print(f"2차 필터링 후 착륙 가능한 영역 면적: {int(second_filtered_area)} m^2")
        print(f"2차 필터링/전체 면적 비율: {second_filtered_area/boundary_area*100:.2f} %")
        print(f"2차 필터링/1차 필터링 면적 비율: {second_filtered_area/first_filtered_area*100:.2f} %")

        num_polygons = len(second_filtered_polygons)
        print(f"2차 필터링 폴리곤 개수: {num_polygons}")
        print('----------------------------')

        # # 결과 분석 (시각화)
        # # 2차 필터링 결과 시각화
        # fig2 = filter.visualize_filtered_polygons(boundary_gdf, second_filtered_polygons)

        # # 시각화 결과를 파일로 저장
        # filter.save_visualization(fig2, f'results/filtering/2차/{region_name}_second_filtered_result.png')


        # 3. 경사도 필터링 (3차 필터링)
        try:
            final_filtered_polygons = filter.load_polygons_from_pickle(f'results/filtering/3차/{region_name}_final_filtered_polygons.pkl')
        except FileNotFoundError:
            # 저장된 파일이 없으면 필터링 진행
            elevation_points = gpd.read_file(f"data/수치지형도/{region_name}/N3P_F0020000.shp", encoding='euckr')
            elevation_contours = gpd.read_file(f"data/수치지형도/{region_name}/N3L_F0010000.shp", encoding='euckr').explode()
            
            polygons_with_elevation = filter.add_elevation_to_polygons(second_filtered_polygons, elevation_points, elevation_contours)

            # 안전 경사도 필터링
            final_filtered_polygons = filter.extract_safe_slopes(polygons_with_elevation)
            
            # 필터링된 데이터를 저장
            filter.save_polygons_to_pickle(final_filtered_polygons, f'results/filtering/3차/{region_name}_final_filtered_polygons.pkl')

        # CSV로 저장
        # save_polygons_to_csv(final_filtered_polygons, f'results/filtering/Database/{region_name}_final_filtered_polygons.csv')
        save_polygons_to_csv(second_filtered_polygons, centers, f'results/filtering/Database/{region_name}_final_filtered_polygons_with_center.csv')

        # # 저장된 파일이 없으면 필터링 진행
        # elevation_points = gpd.read_file(f"data/수치지형도/{region_name}/N3P_F0020000.shp", encoding='euckr')
        # elevation_contours = gpd.read_file(f"data/수치지형도/{region_name}/N3L_F0010000.shp", encoding='euckr').explode()
        
        # polygons_with_elevation = filter.add_elevation_to_polygons(second_filtered_polygons, elevation_points, elevation_contours)

        # # 안전 경사도 필터링
        # final_filtered_polygons = filter.extract_safe_slopes(polygons_with_elevation)



        # 결과 분석 (면적 계산)
        final_filtered_area = gpd.GeoSeries(final_filtered_polygons, crs='epsg:4326').to_crs(epsg=3857).area.sum()
        final_filtered_area_km2 = final_filtered_area / 1_000_000  # m² -> km² 변환
        print(f"3차 필터링 후 착륙 가능한 영역 면적: {int(final_filtered_area)} km^2")
        print(f"3차 필터링/전체 면적 비율: {final_filtered_area/boundary_area*100:.2f} %")
        print(f"3차 필터링/1차 필터링 면적 비율: {final_filtered_area/first_filtered_area*100:.2f} %")
        print(f"3차 필터링/2차 필터링 면적 비율: {final_filtered_area/second_filtered_area*100:.2f} %")

        num_polygons = len(final_filtered_polygons)
        print(f"3차 필터링 폴리곤 개수: {num_polygons}")
        print('='*10)

        # # 결과 분석 (시각화)
        # # 3차 필터링 결과 시각화
        # fig3 = filter.visualize_filtered_polygons(boundary_gdf, final_filtered_polygons)

        # # 시각화 결과를 파일로 저장
        # filter.save_visualization(fig3, f'results/filtering/3차/{region_name}_final_filtered_result.png')

        ####################

        # # 건물이 차지하는 면적 # 
        # # 건물 파일 경로
        # building_file = f"data/building_shp/{region_name}/N3A_B0010000/N3A_B0010000.shp"

        # # 경계 파일 경로
        # boundary_file = f'data/boundary/{region_name}_boundary.csv'

        # # 경계 데이터 불러오기
        # boundary_gdf = filter.load_boundary_data(boundary_file)

        # # 건물 데이터 불러오기
        # buildings_gdf = gpd.read_file(building_file)
        
        # # EPSG 3857로 변환 (면적 계산을 위해)
        # buildings_gdf_3857 = buildings_gdf.to_crs(epsg=3857)
        # boundary_gdf_3857 = boundary_gdf.to_crs(epsg=3857)

        # # 건물이 차지하는 면적 계산
        # building_area = buildings_gdf_3857.area.sum()
        # boundary_area = boundary_gdf_3857.area.sum()

        # # 결과 출력
        # print(f"필터링 전 전체 영역 면적: {int(boundary_area)} m²")
        # print(f"건물이 차지하는 면적: {int(building_area)} m²")
        # print(f"건물 면적 비율: {building_area/boundary_area*100:.2f} %")

        # ####################

        # # 건물이 차지하는 면적 # 

        # # 강하천 파일 경로 (필요한 파일 경로 추가)
        # river_files = [
        #     f"data/대구 강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0010001/N3A_E0010001.shp",
        #     f"data/대구 강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0032111/N3A_E0032111.shp",
        #     f"data/대구 강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0052114/N3A_E0052114.shp"
        # ]

        # # 강하천 데이터 불러오기 (복수 파일을 하나의 GeoDataFrame으로 병합)
        # river_gdfs = [gpd.read_file(file) for file in river_files]
        # rivers_gdf = gpd.GeoDataFrame(pd.concat(river_gdfs, ignore_index=True))

        # # EPSG 3857로 변환 (면적 계산을 위해)
        # rivers_gdf_3857 = rivers_gdf.to_crs(epsg=3857)
        # boundary_gdf_3857 = boundary_gdf.to_crs(epsg=3857)

        # # 건물과 강하천이 차지하는 면적 계산
        # river_area = rivers_gdf_3857.area.sum()
        # boundary_area = boundary_gdf_3857.area.sum()

        # # 결과 출력
        # print(f"강하천 면적 비율: {river_area/boundary_area*100:.2f} %")

        # ####################
        # # 임상도 데이터 불러오기
        # if region_name in forest_file_map:
        #     file_name = forest_file_map[region_name]
        #     forest_file = f"data/임상도/{region_name}/{file_name}.shp"

        # # 임상도 데이터 불러오기
        # # forest_file = f"data/임상도/{region_name}/forest_file.shp"  # 임상도 파일 경로 설정
        # forest_data = gpd.read_file(forest_file)
        
        # # None 값을 제외하고 AGCLS_CD 컬럼을 정수형으로 변환
        # forest_data['AGCLS_CD'] = forest_data['AGCLS_CD'].dropna().astype(int)

        # # 제외할 AGCLS_CD 값이 0 또는 1인 데이터 필터링
        # forest_exclusion_data = forest_data[~forest_data['AGCLS_CD'].isin([0, 1])]

        # # EPSG 3857로 변환 (면적 계산을 위해)
        # forest_data_3857 = forest_data.to_crs(epsg=3857)
        # forest_exclusion_data_3857 = forest_exclusion_data.to_crs(epsg=3857)
        # boundary_gdf_3857 = boundary_gdf.to_crs(epsg=3857)

        # # 전체 임상도 면적 및 제외한 임상도 면적 계산
        # total_forest_area = forest_data_3857.area.sum()
        # excluded_forest_area = forest_exclusion_data_3857.area.sum()

        # # 전체 경계 면적 계산
        # boundary_area = boundary_gdf_3857.area.sum()

        # # 결과 출력
        # print(f"산림 영역이 전체 면적에서 차지하는 비율: {excluded_forest_area/boundary_area*100:.2f} %")

        ####################

        # # Geopy를 위한 지오코더 객체 생성
        # geolocator = Nominatim(user_agent="your_app_name")

        # # # 3차 필터링 후 폴리곤의 대표 지점을 역 지오코딩 (DELETE ?)
        # # for polygon in final_filtered_polygons:
        # #     representative_point = polygon.representative_point()
        # #     location = geolocator.reverse((representative_point.y, representative_point.x), language='ko')
        # #     print(f"Representative Point: {representative_point}, Address: {location.address}")

        # #     address_components = location.raw.get('address', {})
        # #     print(address_components)

        # # 3차 필터링 후 폴리곤의 대표 지점을 역 지오코딩
        # for polygon in final_filtered_polygons:
        #     representative_point = polygon.representative_point()
            
        #     # 역 지오코딩 수행
        #     location = geolocator.reverse((representative_point.y, representative_point.x), language='ko')

        #     if location and location.raw:
        #         address_components = location.raw.get('address', {})
        #         # amenity 정보가 있는지 확인
        #         amenity = address_components.get('amenity', None)

        #         # amenity가 있는 경우 우선적으로 출력
        #         if amenity:
        #             print(f"Representative Point: {representative_point}")
        #             print(f"Amenity: {amenity}")

if __name__ == "__main__":
    main()
