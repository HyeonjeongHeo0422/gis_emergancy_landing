import geopandas as gpd
from geopy.geocoders import Nominatim
import pandas as pd
from tqdm import tqdm

# 파일 경로 설정
output_file = "results/select_landing_location/region_final_landing_locations.csv"  
data = pd.read_csv(output_file)

# # Extract unique (latitude, longitude) pairs for final landing locations
# unique_coordinates = data[['Final_Landing_Location_Lat', 'Final_Landing_Location_Lon']].drop_duplicates()

# # Convert to (latitude, longitude) tuple format
# unique_coordinates_list = list(zip(unique_coordinates['Final_Landing_Location_Lat'], unique_coordinates['Final_Landing_Location_Lon']))

# Extract unique coordinates and corresponding region
unique_coordinates_with_region = data[['Final_Landing_Location_Lat', 'Final_Landing_Location_Lon', 'Region']].drop_duplicates()

# Convert to (latitude, longitude, region) tuple format
unique_coordinates_list = list(zip(
    unique_coordinates_with_region['Final_Landing_Location_Lat'], 
    unique_coordinates_with_region['Final_Landing_Location_Lon'],
    unique_coordinates_with_region['Region']
))

# Geopy를 위한 지오코더 객체 생성
geolocator = Nominatim(user_agent="your_app_name")

# 결과를 저장할 리스트
results = []

# 3차 필터링 후 폴리곤의 대표 지점을 역 지오코딩
# for point in unique_coordinates_list:
for point in tqdm(unique_coordinates_list, desc="Reverse Geocoding"):
    # 역 지오코딩 수행
    location = geolocator.reverse((point[0], point[1]), language='ko')  # `point[0]`은 latitude, `point[1]`은 longitude
    # region = data['Region']

    if location and location.raw:
        address_components = location.raw.get('address', {})
        # amenity 정보가 있는지 확인
        amenity = address_components.get('amenity', None)
        
        # 결과 저장
        results.append({
            'region': point[2],
            'point': f"({point[0]}, {point[1]})",
            'amenity': amenity if amenity else None
        })

# 결과를 데이터프레임으로 변환
results_df = pd.DataFrame(results)

# 결과를 엑셀 파일로 저장
results_df.to_excel("results/select_landing_location/region_landing_address.xlsx", index=False)

# 저장된 파일 확인
results_df.head()
