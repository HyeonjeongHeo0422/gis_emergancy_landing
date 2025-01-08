# main.py
from final_clustering import clustering
# from final_find_obstacles import find_obstacles
from final_select_landing_site import select_landing_site

### 실시간으로 받는 데이터(임시) ###
import random       # for uam heading
uam_heading = random.uniform(0, 360)  # 0에서 360 사이의 임의의 실수 값
# uam_location
# frame
# uam_height
# uam_velocity
################################

if __name__ == "__main__":
    # 비상착륙지 데이터베이스 로딩
    file_path = 'results/filtering/UAM/uam_route_filtered_polygons_4km_with_center.csv'

    # 대표 클러스터 선정
    top_cluster_info, waypoint, uam_location = clustering(file_path, uam_heading)
    # top_cluster_info, waypoint = clustering(file_path, uam_heading, uam_location)

    # MOVE

    # 장애물 탐색
    # obstacles_info --> [moving_obstacles_info, static_obstacles_info]
    # obstacles_info = find_obstacles(frame, uam_height, uam_location, uam_velocity)
    
    # 최종 비상착륙지 선정
    # landing_coordinates -> (latitude, longitude)
    landing_coordinates = select_landing_site(uam_location, top_cluster_info)
    # landing_coordinates = select_landing_site(uam_location, top_cluster_info, obstacles_info)
    
