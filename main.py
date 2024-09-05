import filter
import geopandas as gpd

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
    # 1. 착륙 제한 지역 필터링
    exclusion_data, boundary_gdf = filter.load_data(exclusion_files, forest_file, soil_file, boundary_file)
    first_filtered_polygons, boundary_gdf, _, first_filtered_sites = filter.preprocess_data(exclusion_data, boundary_gdf)

    # 면적 계산
    boundary_area = boundary_gdf.to_crs(epsg=3857).area.sum()  # 경계 면적 계산 (EPSG:3857 좌표계로 변환 후 면적 계산)
    print(f"필터링 전 전체 영역 면적: {boundary_area:.2f} m^2")
    first_filtered_area = gpd.GeoSeries([first_filtered_sites], crs='epsg:4326').to_crs(epsg=3857).area.sum()
    print(f"1차 필터링 후 착륙 가능한 영역 면적: {first_filtered_area:.2f} m^2")
    print(f"1차 필터링 면적 비율: {first_filtered_area/boundary_area*100:.2f} %")

    # 시각화
    # fig1, fig2 = filter.visualize_results(boundary_gdf, gpd.GeoDataFrame({'geometry': first_filtered_polygons}), landing_able_sites, exclusions_in_boundary)


if __name__ == "__main__":
    main()


    # # 2. 면적 필터링 (반지름 20m 원을 넣을 수 있는지 필터링)
    # radius = 20  # 반지름 설정
    # landing_candidates = filter.filter_landing_zones(polygons, radius)

    # # 3. 경사도 필터링
    # elevation_points = gpd.read_file("elevation_points.shp")
    # elevation_contours = gpd.read_file("elevation_contours.shp")
    
    # polygons_with_elevation = filter.add_elevation_to_polygons(landing_candidates['Polygon'], elevation_points, elevation_contours)

    # # 안전 경사도 필터링
    # safe_polygons = filter.extract_safe_slopes(polygons_with_elevation)

    # # 결과 시각화
    # filter.visualize_safe_polygons(boundary_gdf, safe_polygons)
