import numpy as np
import math
import time

# 고도, 시야각, 이미지 너비, 이미지 높이를 이용해 실제 거리 계산하는 함수
def calculate_real_distances(altitude, fov_degrees, image_width, image_height):
    fov_radians = math.radians(fov_degrees)
    half_fov_radians = fov_radians / 2
    half_distance = altitude * math.tan(half_fov_radians)
    real_width_per_pixel = 2 * half_distance / image_width
    real_image_width = image_width * real_width_per_pixel
    real_image_height = image_height * real_width_per_pixel
    return real_width_per_pixel, real_image_width, real_image_height

# GPS 좌표와 실제 거리 좌표를 변환하는 함수 (UAM 헤딩 반영)
def pixel_to_gps_coordinates(x, y, real_width_per_pixel, center_lat, center_lon, image_width, image_height, heading_degrees):
    # 이미지의 중앙을 기준으로 상대적 위치를 구합니다.
    center_x = image_width / 2
    center_y = image_height / 2
    
    # 픽셀 좌표를 실제 거리로 변환합니다.
    real_x = (x - center_x) * real_width_per_pixel
    real_y = (center_y - y) * real_width_per_pixel  

    # 헤딩 각도를 라디안으로 변환하고 회전 변환을 적용합니다. (변경된 부분)
    heading_radians = math.radians(heading_degrees)
    rotated_x = real_x * math.cos(heading_radians) - real_y * math.sin(heading_radians)
    rotated_y = real_x * math.sin(heading_radians) + real_y * math.cos(heading_radians)
    
    # 위도와 경도의 변화량을 계산합니다.
    lat_per_meter = 1 / 111320  # 1도 위도는 약 111,320미터
    lon_per_meter = 1 / (111320 * math.cos(math.radians(center_lat)))  
    
    delta_lat = rotated_y * lat_per_meter
    delta_lon = rotated_x * lon_per_meter
    
    new_lat = center_lat + delta_lat
    new_lon = center_lon + delta_lon

    return new_lat, new_lon

# 테스트 데이터
altitude = 175
fov = 45
image_width = 300
image_height = 168
heading = 30  # UAM의 헤딩 각도 (예시)

# GPS 중심 좌표
center_lat = 35.8905477
center_lon = 128.6121117

start_time = time.time()

# 실제 거리 계산
real_width_per_pixel, real_image_width, real_image_height = calculate_real_distances(altitude, fov, image_width, image_height)

# 픽셀 좌표를 GPS 좌표로 변환
pixel_coordinates = [(100, 100), (150, 150), (200, 200)]
gps_coordinates = [pixel_to_gps_coordinates(x, y, real_width_per_pixel, center_lat, center_lon, image_width, image_height, heading) for x, y in pixel_coordinates]

end_time = time.time()
print('loading time: ')
print(end_time-start_time)

# 결과 출력
print("픽셀 좌표를 GPS 좌표로 변환한 결과:")
for pixel, gps in zip(pixel_coordinates, gps_coordinates):
    print(f"픽셀 좌표 {pixel} -> GPS 좌표 {gps}")
