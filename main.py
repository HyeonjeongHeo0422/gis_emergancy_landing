import filter
import geopandas as gpd
from geopy.geocoders import Nominatim

def main():
    # 데이터 파일 경로 설정 #
    # 구 이름을 변수로 정의
    region_name = '북구'

    # 제외할 영역 파일 경로들
    exclusion_files = [
        f"data/road_shp/{region_name}/(B021)연속수치지도(대구광역시 {region_name})_N3A_A0010000/N3A_A0010000.shp",    # 도로
        f"data/road_shp/{region_name}/(B021)연속수치지도(대구광역시 {region_name})_N3A_A0160024/N3A_A0160024.shp",    # 도로
        f"data/building_shp/{region_name}/N3A_B0010000/N3A_B0010000.shp",     # 건물
        f"data/대구 강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0010001/N3A_E0010001.shp",     # 강하천
        f"data/대구 강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0032111/N3A_E0032111.shp",     # 강하천
        f"data/대구 강하천/{region_name} 강하천/(B021)연속수치지도(대구광역시 {region_name})_N3A_E0052114/N3A_E0052114.shp",     # 강하천
    ]  

    # 임상도 파일 경로
    forest_file_map = {
        '남구': 'TB_FGDI_FS_IM4000_27200',
        '북구': 'TB_FGDI_FS_IM5000_27230',
        '동구': 'TB_FGDI_FS_IM5000_27140',
        '서구': 'TB_FGDI_FS_IM5000_27170',
        '수성': 'TB_FGDI_FS_IM5000_27260',
        '중구': 'TB_FGDI_FS_IM5000_27110',
        '달서구': 'TB_FGDI_FS_IM5000_27290',
        '군위': 'TB_FGDI_FS_IM5000_47720'
    }
    # 해당 구 이름에 맞는 파일명 선택
    if region_name in forest_file_map:
        file_name = forest_file_map[region_name]
        forest_file = f"data/임상도/{region_name}/{file_name}.shp"
    else:
        raise ValueError(f"Invalid region name: {region_name}")

    soil_file = "data/산림입지토양도/27.shp"                        # 산림입지토양도 파일 경로
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

    # 결과 분석 (시각화)
    # 1차 필터링 결과 시각화
    # fig = filter.visualize_filtered_polygons(boundary_gdf, first_filtered_polygons)

    # 시각화 결과를 파일로 저장
    # filter.save_visualization(fig, f'results/filtering/1차/{region_name}_first_filtered_result.png')


    # 2. 면적 필터링 (2차 필터링)
    try:
        second_filtered_polygons = filter.load_polygons_from_pickle(f'results/filtering/2차/{region_name}_first_filtered_polygons.pkl')
    except FileNotFoundError:
        # 저장된 파일이 없으면 필터링 진행
        RADIUS = 20     # m
        second_filtered_polygons, _ = filter.second_filtering(first_filtered_polygons, RADIUS)
        
        # 필터링된 데이터를 저장
        filter.save_polygons_to_pickle(second_filtered_polygons, f'results/filtering/2차/{region_name}_first_filtered_polygons.pkl')
    
    # 결과 분석 (면적 계산)
    second_filtered_area = gpd.GeoSeries(second_filtered_polygons, crs='epsg:4326').to_crs(epsg=3857).area.sum()
    print(f"2차 필터링 후 착륙 가능한 영역 면적: {int(second_filtered_area)} m^2")
    print(f"2차 필터링/전체 면적 비율: {second_filtered_area/boundary_area*100:.2f} %")
    print(f"2차 필터링/1차 필터링 면적 비율: {second_filtered_area/first_filtered_area*100:.2f} %")

    num_polygons = len(second_filtered_polygons)
    print(f"2차 필터링 폴리곤 개수: {num_polygons}")
    print('----------------------------')

    # 결과 분석 (시각화)
    # 2차 필터링 결과 시각화
    # fig2 = filter.visualize_filtered_polygons(boundary_gdf, second_filtered_polygons)

    # 시각화 결과를 파일로 저장
    # filter.save_visualization(fig2, f'results/filtering/2차/{region_name}_second_filtered_result.png')


    # 3. 경사도 필터링 (3차 필터링)
    elevation_points = gpd.read_file(f"data/수치지형도/{region_name}/N3P_F0020000.shp", encoding='euckr')
    elevation_contours = gpd.read_file(f"data/수치지형도/{region_name}/N3L_F0010000.shp", encoding='euckr').explode()
    
    polygons_with_elevation = filter.add_elevation_to_polygons(second_filtered_polygons, elevation_points, elevation_contours)

    # 안전 경사도 필터링
    final_filtered_polygons = filter.extract_safe_slopes(polygons_with_elevation)

    # 결과 분석 (면적 계산)
    final_filtered_area = gpd.GeoSeries(final_filtered_polygons, crs='epsg:4326').to_crs(epsg=3857).area.sum()
    print(f"3차 필터링 후 착륙 가능한 영역 면적: {int(final_filtered_area)} m^2")
    print(f"3차 필터링/전체 면적 비율: {final_filtered_area/boundary_area*100:.2f} %")
    print(f"3차 필터링/1차 필터링 면적 비율: {final_filtered_area/first_filtered_area*100:.2f} %")
    print(f"3차 필터링/2차 필터링 면적 비율: {final_filtered_area/second_filtered_area*100:.2f} %")

    num_polygons = len(final_filtered_polygons)
    print(f"3차 필터링 폴리곤 개수: {num_polygons}")
    print('----------------------------')

    # 결과 분석 (시각화)
    # # 3차 필터링 결과 시각화
    # fig3 = filter.visualize_filtered_polygons(boundary_gdf, final_filtered_polygons)

    # # 시각화 결과를 파일로 저장
    # filter.save_visualization(fig3, f'results/filtering/3차/{region_name}_final_filtered_result.png')

    # Geopy를 위한 지오코더 객체 생성
    geolocator = Nominatim(user_agent="your_app_name")

    # # 3차 필터링 후 폴리곤의 대표 지점을 역 지오코딩
    # for polygon in final_filtered_polygons:
    #     representative_point = polygon.representative_point()
    #     location = geolocator.reverse((representative_point.y, representative_point.x), language='ko')
    #     print(f"Representative Point: {representative_point}, Address: {location.address}")

    #     address_components = location.raw.get('address', {})
    #     print(address_components)

    # 3차 필터링 후 폴리곤의 대표 지점을 역 지오코딩
    for polygon in final_filtered_polygons:
        representative_point = polygon.representative_point()
        
        # 역 지오코딩 수행
        location = geolocator.reverse((representative_point.y, representative_point.x), language='ko')

        if location and location.raw:
            address_components = location.raw.get('address', {})
            # amenity 정보가 있는지 확인
            amenity = address_components.get('amenity', None)

            # amenity가 있는 경우 우선적으로 출력
            if amenity:
                print(f"Representative Point: {representative_point}")
                print(f"Amenity: {amenity}")
            # else:
            #     print(f"Representative Point: {representative_point}")
            #     print(f"Address: {location.address}")
            # print("-----------------------")

if __name__ == "__main__":
    main()
