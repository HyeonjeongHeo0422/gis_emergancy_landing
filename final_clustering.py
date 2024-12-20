from library import *
from params import *

# 1. 데이터 로드 및 전처리
def load_and_preprocess_data(file_path):
    """
    CSV 파일에서 데이터를 로드하고, 폴리곤과 중심점을 전처리하는 함수.
    
    Parameters:
    - file_path (str): CSV 파일 경로.
    
    Returns:
    - pd.DataFrame: 전처리된 데이터프레임 (geometry 및 centroid 포함).
    """
    data = pd.read_csv(file_path)

    data['geometry'] = data['Polygon'].apply(safe_load_wkt)
    data = data[data['geometry'].notnull()]
    data['centroid'] = data['Centroid'].apply(lambda x: Point(eval(x)) if pd.notnull(x) else None)
    data['safe_center'] = data['Safe Center Point'].apply(lambda x: Point(eval(x)) if pd.notnull(x) else None)

    return data

def safe_load_wkt(wkt_str):
    """
    WKT 문자열을 안전하게 로드하는 함수. 오류가 발생할 경우 None을 반환.
    
    Parameters:
    - wkt_str (str): WKT 형식의 문자열.
    
    Returns:
    - shapely.geometry (or None): 유효한 경우 로드된 geometry 객체, 아니면 None.
    """
    try:
        return wkt_loads(wkt_str)
    except (shapely.errors.WKTReadingError, TypeError):
        return None

############################################################
# 2. 랜덤 포인트 및 섹터 생성
def random_point_in_polygon(polygon):
    """
    주어진 폴리곤 내부에서 랜덤한 포인트를 생성하는 함수.
    
    Parameters:
    - polygon (shapely.geometry.Polygon): 포인트를 생성할 폴리곤.
    
    Returns:
    - Point: 폴리곤 내부의 랜덤 포인트.
    """
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        random_point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(random_point):
            return random_point

def generate_sector(center, radius, angle, uam_heading):
    """
    중심점에서 주어진 반경과 각도로 섹터(부채꼴 형태)를 생성하는 함수.
    
    Parameters:
    - center (Point): 섹터의 중심점.
    - radius (float): 섹터의 반경 (도 단위).
    - angle (float): 섹터의 각도 (도 단위).
    - uam_heading (float): 섹터의 중심 방향 (도 단위, 북쪽을 0도로 간주).
    
    Returns:
    - list[Point]: 섹터를 구성하는 포인트들의 리스트.
    """
    points = [center]
    num_points = 100  # 부드러운 곡선을 위해 포인트 수 설정
    for i in range(num_points + 1):
        angle_rad = np.radians(uam_heading - angle / 2 + i * angle / num_points)
        x = center.x + radius * np.cos(angle_rad)
        y = center.y + radius * np.sin(angle_rad)
        points.append(Point(x, y))
    points.append(center)  # 부채꼴을 닫기 위해 중심점 추가
    return points

def is_within_sector(point, center, radius, angle, uam_heading):
    """
    주어진 포인트가 섹터 내부에 있는지 여부를 확인하는 함수.

    Parameters:
    - point (Point): 확인할 포인트.
    - center (Point): 섹터의 중심점.
    - radius (float): 섹터의 반경 (도 단위).
    - angle (float): 섹터의 각도 (도 단위).
    - uam_heading (float): 섹터의 중심 방향 (도 단위).

    Returns:
    - bool: 포인트가 섹터 내에 있으면 True, 아니면 False.
    """
    distance = center.distance(point)
    if distance > radius:
        return False

    dx = point.x - center.x
    dy = point.y - center.y
    point_angle = (math.degrees(math.atan2(dy, dx))) % 360

    return uam_heading-angle / 2 <= point_angle <= uam_heading+angle / 2

############################################################
# 3. 클러스터링
def perform_dbscan_clustering(filtered_data):
    """
    DBSCAN을 이용해 필터링된 폴리곤들의 꼭짓점을 클러스터링하는 함수.
    
    Parameters:
    - filtered_data (pd.DataFrame): 필터링된 폴리곤 데이터프레임.
    - eps (float): DBSCAN의 입실론 값. 
    - min_samples (int): 각 클러스터의 최소 샘플 수.
    
    Returns:
    - clusters (np.ndarray): 각 꼭짓점의 클러스터 레이블 배열.
    - vertices_array (np.ndarray): 각 꼭짓점의 좌표 배열.
    """
    # 필터링된 폴리곤의 꼭짓점 좌표 수집
    all_vertices = []
    for geom in filtered_data['geometry']:
        if geom is not None:
            coords = np.array(geom.exterior.coords)
            all_vertices.extend(coords)

    # 꼭짓점 좌표 배열 생성
    vertices_array = np.array(all_vertices)

    # 빈 배열인지 확인
    if vertices_array.size == 0:
        print_color("후보지가 없습니다.", color="yellow")
        return np.array([]), np.array([])

    # 데이터 형태 확인 및 변환
    if vertices_array.ndim == 1 or vertices_array.shape[1] != 2:
        print_color("Reshaping vertices_array to 2D format.", color="yellow")
        vertices_array = vertices_array.reshape(-1, 2)

    # DBSCAN 클러스터링 수행
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    clusters = dbscan.fit_predict(vertices_array)
    # print('clusters: ', clusters)

    return clusters, vertices_array

def find_polygons_in_multiple_clusters(filtered_data, clusters, vertices_array):
    """
    각 폴리곤이 여러 클러스터에 걸쳐 있는지 확인하는 함수.
    
    Parameters:
    - filtered_data (pd.DataFrame): 필터링된 폴리곤 데이터프레임.
    - clusters (np.ndarray): DBSCAN 클러스터 레이블 배열.
    - vertices_array (np.ndarray): 각 꼭짓점의 좌표 배열.
    
    Returns:
    - multiple_cluster_polygons (list): 여러 클러스터에 걸쳐 있는 폴리곤의 인덱스 리스트.
    """
    multiple_cluster_polygons = []

    for idx, geom in enumerate(filtered_data['geometry']):
        if geom is not None:
            # 폴리곤의 각 꼭짓점에 대한 클러스터 레이블 수집
            coords = np.array(geom.exterior.coords)
            cluster_labels = {clusters[i] for i, vertex in enumerate(vertices_array) if tuple(vertex) in coords}

            # 클러스터 레이블이 2개 이상이면 폴리곤이 여러 클러스터에 걸쳐 있음
            if len(cluster_labels) > 1:
                multiple_cluster_polygons.append(idx)
                # print(f"Polygon {idx} spans multiple clusters: {cluster_labels}")

    return multiple_cluster_polygons

def select_optimal_cluster(cluster_weights):
    """
    최적의 클러스터를 선택하는 함수. 가장 높은 가중치를 가진 클러스터를 선택하는 함수.
    
    Parameters:
    - cluster_weights (dict): 클러스터 ID와 가중치 값을 포함한 딕셔너리.
    
    Returns:
    - optimal_cluster_id (int): 최적의 클러스터 ID.
    - optimal_weight (float): 최적의 가중치 값.
    """
    if not cluster_weights:
        print("No cluster weights provided.")
        return None, None
    
    # 가중치가 가장 큰 클러스터 찾기
    optimal_cluster_id = max(cluster_weights, key=cluster_weights.get)
    optimal_weight = cluster_weights[optimal_cluster_id]
    
    # print(f"Optimal Cluster ID: {optimal_cluster_id}, Weight: {optimal_weight}")
    return optimal_cluster_id, optimal_weight

def print_cluster_coordinates(clusters, vertices_array):
    """
    각 클러스터에 속하는 폴리곤의 좌표를 출력하는 함수.
    
    Parameters:
    - clusters (np.ndarray): DBSCAN 클러스터 레이블 배열.
    - vertices_array (np.ndarray): 각 꼭짓점의 좌표 배열.
    """
    # 고유한 클러스터 레이블 가져오기
    unique_labels = set(clusters)
    
    # 각 클러스터에 속한 좌표를 출력
    for cluster_id in unique_labels:
        if cluster_id == -1:
            print(f"\nCluster {cluster_id} (Noise):")
        else:
            print(f"\nCluster {cluster_id}:")

        # 현재 클러스터에 속한 좌표 찾기
        cluster_points = vertices_array[clusters == cluster_id]
        
        # 좌표 출력
        for point in cluster_points:
            print(f"Vertex: ({point[0]}, {point[1]})")

def merge_clusters(filtered_data, clusters, vertices_array):
    """
    겹치는 폴리곤의 클러스터를 병합하는 함수.
    
    Parameters:
    - filtered_data (pd.DataFrame): 필터링된 폴리곤 데이터프레임.
    - clusters (np.ndarray): DBSCAN 클러스터 레이블 배열.
    - vertices_array (np.ndarray): 각 꼭짓점의 좌표 배열.
    
    Returns:
    - clusters (np.ndarray): 병합된 클러스터 레이블 배열.
    """
    cluster_mapping = {}  # 클러스터 병합 규칙을 저장하는 딕셔너리

    for idx, geom in enumerate(filtered_data['geometry']):
        if geom is not None:
            # 폴리곤의 각 꼭짓점에 대한 클러스터 레이블 수집
            coords = np.array(geom.exterior.coords)
            cluster_labels = [clusters[i] for i, vertex in enumerate(vertices_array) if tuple(vertex) in coords]

            # -1을 제거하고 유효한 클러스터 ID만 사용
            valid_cluster_labels = [label for label in cluster_labels if label != -1]

            # 가장 많이 등장한 클러스터 ID를 기준 클러스터로 설정
            if valid_cluster_labels:
                dominant_cluster = max(set(cluster_labels), key=cluster_labels.count)

                # 병합할 클러스터를 기준 클러스터로 매핑
                for cluster_id in set(cluster_labels):
                    if cluster_id != dominant_cluster:  # 기준 클러스터가 아닌 경우
                        cluster_mapping[cluster_id] = dominant_cluster

    # 클러스터 레이블 업데이트
    for old_cluster, new_cluster in cluster_mapping.items():
        clusters = np.where(clusters == old_cluster, new_cluster, clusters)

    return clusters

############################################################
# 가중치 계산 #

def assign_cluster_properties(filtered_data, clusters, vertices_array, uam_location):
    """
    각 클러스터별로 폴리곤 면적의 합, UAM 위치와의 최소 거리, 폴리곤 개수를 저장하는 함수.
    
    Parameters:
    - filtered_data (pd.DataFrame): 필터링된 폴리곤 데이터프레임.
    - clusters (np.ndarray): DBSCAN 클러스터 레이블 배열.
    - vertices_array (np.ndarray): 각 꼭짓점의 좌표 배열.
    - uam_location (Point): UAM 위치.
    
    Returns:
    - cluster_areas (defaultdict): 클러스터 ID별 면적 합계.
    - cluster_distances (defaultdict): 클러스터 ID별 UAM 위치와의 최소 거리.
    - cluster_counts (defaultdict): 클러스터 ID별 폴리곤 개수.
    """
    cluster_areas = defaultdict(float)        # 클러스터별 면적 합계
    cluster_distances = defaultdict(lambda: float('inf'))  # 클러스터별 최소 거리
    cluster_counts = defaultdict(int)         # 클러스터별 폴리곤 개수

    # UAM 위치를 위도, 경도 튜플로 변환
    uam_coords = (uam_location.y, uam_location.x)

    # 각 폴리곤의 면적과 거리를 클러스터별로 저장
    for polygon_idx, geom in enumerate(filtered_data['geometry']):
        if geom is not None:
            coords = np.array(geom.exterior.coords)
            cluster_labels = [clusters[i] for i, vertex in enumerate(vertices_array) if tuple(vertex) in coords]
            
            # 각 폴리곤이 속한 클러스터를 가장 많이 등장한 cluster_id로 설정
            if cluster_labels:
                cluster_id = max(set(cluster_labels), key=cluster_labels.count)
                
                # 노이즈 클러스터는 제외
                if cluster_id != -1:
                    area = filtered_data.iloc[polygon_idx]['Area (m^2)']
                    centroid = filtered_data.iloc[polygon_idx]['centroid']
                    safe_center = filtered_data.iloc[polygon_idx]['safe_center']
                    
                    # 클러스터별 면적 합계 갱신
                    cluster_areas[cluster_id] += area

                    # 현재 폴리곤의 중심점 좌표를 위도, 경도로 변환
                    safe_center_coords = (safe_center.y, safe_center.x)  # Point(y, x) -> (lat, lon)

                    # 현재 safe_center 중심점과 UAM 위치 간의 거리 계산
                    distance_to_uam = haversine(safe_center_coords, uam_coords)
                    
                    # 클러스터별 최소 거리 갱신
                    if distance_to_uam < cluster_distances[cluster_id]:
                        cluster_distances[cluster_id] = distance_to_uam
                    
                    # 클러스터별 폴리곤 개수 증가
                    cluster_counts[cluster_id] += 1

    return cluster_areas, cluster_distances, cluster_counts

def calculate_cluster_weights(cluster_areas, cluster_distances, cluster_counts):
    """
    클러스터별 가중치를 계산하는 함수.
    
    Parameters:
    - cluster_areas (defaultdict): 클러스터 ID별 면적 합계.
    - cluster_distances (defaultdict): 클러스터 ID별 UAM 위치와의 최소 거리.
    - cluster_counts (defaultdict): 클러스터 ID별 폴리곤 개수.
    
    Returns:
    - cluster_weights (dict): 클러스터 ID와 가중치 값을 포함한 딕셔너리.
    """
    cluster_weights = {}

    # 모든 클러스터의 면적 합, 최소 거리, 폴리곤 개수를 하나의 배열로 결합
    all_areas = np.array(list(cluster_areas.values()))
    all_distances = np.array(list(cluster_distances.values()))
    all_counts = np.array(list(cluster_counts.values()))

    # 정규화: 모든 클러스터의 값을 한 번에 정규화
    scaler_areas = MinMaxScaler()
    normalized_all_areas = scaler_areas.fit_transform(all_areas.reshape(-1, 1)).flatten()

    scaler_distances = MinMaxScaler()
    normalized_all_distances = scaler_distances.fit_transform(all_distances.reshape(-1, 1)).flatten()

    scaler_counts = MinMaxScaler()
    normalized_all_counts = scaler_counts.fit_transform(all_counts.reshape(-1, 1)).flatten()

    # 가중치 계산
    for cluster_id in cluster_areas.keys():
        normalized_area = normalized_all_areas[list(cluster_areas.keys()).index(cluster_id)]
        normalized_distance = normalized_all_distances[list(cluster_distances.keys()).index(cluster_id)]
        normalized_count = normalized_all_counts[list(cluster_counts.keys()).index(cluster_id)]

        # Cluster Weight Score
        weighted_score = (
            WEIGHT_DISTANCE * (1 - normalized_distance) +  # 거리는 작을수록 좋으므로 1에서 뺌
            WEIGHT_AREA * normalized_area +
            WEIGHT_CLUSTER_NUMBER * normalized_count
        )

        cluster_weights[cluster_id] = weighted_score

    return cluster_weights

############################################################
# 시각화
def visualize_clusters(filtered_data, sector_points, uam_location, clusters, vertices_array, optimal_cluster_id=None):
    """
    필터링된 폴리곤, 섹터, 최적 클러스터 중심에 하나의 큰 파란색 원을 추가한 클러스터링 결과 시각화 함수.
    
    Parameters:
    - filtered_data (pd.DataFrame): 필터링된 폴리곤 데이터프레임.
    - sector_points (list[Point]): 섹터를 구성하는 포인트 리스트.
    - uam_location (Point): UAM의 랜덤 위치.
    - clusters (np.ndarray): DBSCAN 클러스터 레이블 배열.
    - vertices_array (np.ndarray): 각 꼭짓점의 좌표 배열.
    - optimal_cluster_id (int, optional): 최적의 클러스터 ID.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))

    # 섹터 시각화
    sector_x = [p.x for p in sector_points]
    sector_y = [p.y for p in sector_points]
    ax.plot(sector_x, sector_y, color='black', linewidth=2, label='Sector')

    # 클러스터별 색상 생성
    unique_labels = set(clusters)
    colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
    label_to_color = {label: color for label, color in zip(unique_labels, colors)}

    # 최적의 클러스터 중심들의 평균 좌표를 계산
    optimal_cluster_centroids = []
    total_area = 0  # 최적 클러스터의 폴리곤 면적 합계

    for polygon_idx, geom in enumerate(filtered_data['geometry']):
        if geom is not None:
            coords = np.array(geom.exterior.coords)
            cluster_indices = [clusters[i] for i, vertex in enumerate(vertices_array) if tuple(vertex) in coords]
            cluster_label = max(set(cluster_indices), key=cluster_indices.count) if cluster_indices else -1
            edge_color = 'k' if cluster_label == -1 else label_to_color[cluster_label]
            gpd.GeoSeries([geom], crs='epsg:4326').plot(ax=ax, edgecolor=edge_color, facecolor='plum', linewidth=1)

            # # 폴리곤 번호 추가
            # centroid = filtered_data.iloc[polygon_idx]['centroid']
            # ax.text(centroid.x, centroid.y, str(polygon_idx), color="blue", fontsize=10, ha="center", va="center")

            # 최적의 클러스터 ID와 일치하는 폴리곤의 중심점 수집
            if cluster_label == optimal_cluster_id:
                centroid = filtered_data.iloc[polygon_idx]['centroid']
                optimal_cluster_centroids.append((centroid.x, centroid.y))
                total_area += filtered_data.iloc[polygon_idx]['Area (m^2)']  # 폴리곤 면적 합산

    # 최적 클러스터 내 중심들의 평균 좌표에 원 그리기
    if optimal_cluster_centroids:
        avg_x = np.mean([coord[0] for coord in optimal_cluster_centroids])
        avg_y = np.mean([coord[1] for coord in optimal_cluster_centroids])
        
        # 반지름은 총 면적에 비례하여 설정 (임의의 스케일링 적용)
        # radius = np.sqrt(total_area) * 0.000010  # 스케일링 팩터 0.0001 조정 가능
        # circle = Circle((avg_x, avg_y), radius=radius, color='blue', fill=False, linewidth=2)
        # circle = Circle((avg_x, avg_y), radius=0.005, color='blue', fill=False, linewidth=2)
        # ax.add_patch(circle)

    # UAM 위치를 빨간색 별표로 표시
    uam_location_marker = ax.scatter(uam_location.x, uam_location.y, color='red', marker='*', s=150, label='UAM Location')

    # 범례 설정
    legend_handles = [Patch(edgecolor=color, facecolor='none', linewidth=2, label=f"Cluster {label}") for label, color in label_to_color.items()]
    legend_handles.append(uam_location_marker)  # UAM Location 추가
    ax.legend(handles=legend_handles, bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    plt.show()

    return fig

############################################################
def print_color(text, color="white"):
    """
    터미널에 컬러 텍스트를 출력하는 함수.
    
    Parameters:
    - text (str): 출력할 텍스트.
    - color (str): 출력할 색상. (기본값: 'white')
                   사용할 수 있는 색상: black, red, green, yellow, blue, magenta, cyan, white.
    """
    colors = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m"
    }
    reset = "\033[0m"
    color_code = colors.get(color.lower(), colors["white"])  # 기본값: white
    print(f"{color_code}{text}{reset}")

############################################################
## main ##
def clustering(file_path, uam_heading):
    """
    클러스터링 작업의 첫 번째 단계: 데이터 로드 및 전처리.
    """
    print_color('Clustering...','yellow')

    # 1. 데이터 로드 및 전처리
    processed_data = load_and_preprocess_data(file_path)
    if processed_data.empty:
        print("Processed data is empty. Check your input file.")

    ### 임시 ###
    # 랜덤한 폴리곤 내에서 랜덤한 포인트 생성
    random_polygon = processed_data['geometry'].sample(1).values[0]
    uam_location = random_point_in_polygon(random_polygon)  # 랜덤 포인트 생성
    ############

    # 2. Sector
    # 섹터 생성
    radius_deg = SECTOR_RADIUS / 111  # 도 단위로 변환
    sector_points = generate_sector(uam_location, radius_deg, SECTOR_ANGLE, uam_heading)

    # 필터링된 데이터를 섹터 내 포인트만 남기기
    filtered_data = processed_data[processed_data['centroid'].apply(
        lambda c: is_within_sector(c, uam_location, radius_deg, SECTOR_ANGLE, uam_heading)
    )].copy()

    # 3. DBSCAN 클러스터링 수행 및 결과 출력
    clusters, vertices_array = perform_dbscan_clustering(filtered_data)

    if vertices_array.size != 0:
        # 같은 폴리곤이 여러 클러스터에 걸쳐 있는지 확인
        multiple_cluster_polygons = find_polygons_in_multiple_clusters(filtered_data, clusters, vertices_array)
        if multiple_cluster_polygons:          
            # 클러스터 병합
            clusters = merge_clusters(filtered_data, clusters, vertices_array)

        # 4. 각 폴리곤에 클러스터 ID 할당
        polygon_clusters = []
        for geom in filtered_data['geometry']:
            if geom is not None:
                coords = np.array(geom.exterior.coords)
                cluster_labels = [clusters[i] for i, vertex in enumerate(vertices_array) if tuple(vertex) in coords]
                # 가장 빈도가 높은 클러스터 ID 할당
                cluster_id = max(set(cluster_labels), key=cluster_labels.count) if cluster_labels else -1
                polygon_clusters.append(cluster_id)
            else:
                polygon_clusters.append(-1)

        filtered_data['cluster'] = polygon_clusters

        # 5. 클러스터별 가중치 계산
        # 클러스터별 면적, 거리, 클러스터 내 후보지 개수 저장
        cluster_areas, cluster_distances, cluster_counts = assign_cluster_properties(filtered_data, clusters, vertices_array, uam_location)

        # 클러스터별 가중치 계산
        cluster_weights = calculate_cluster_weights(cluster_areas, cluster_distances, cluster_counts)

        # 6. 최적의 클러스터 선택
        optimal_cluster_id, optimal_weight = select_optimal_cluster(cluster_weights)

        top_cluster_info = filtered_data[filtered_data['cluster'] == optimal_cluster_id]
        top_cluster_info = top_cluster_info[['geometry', 'safe_center']]    # 필요한 열만 선택

        print_color('Top Cluster Info','yellow')
        print(top_cluster_info)

        # UAM과 가장 가까운 safe_center 계산
        if not top_cluster_info.empty:
            top_cluster_info['distance_to_uam'] = top_cluster_info['safe_center'].apply(
                lambda x: haversine((uam_location.y, uam_location.x), (x.y, x.x))
            )
            closest_point = top_cluster_info.loc[top_cluster_info['distance_to_uam'].idxmin(), 'safe_center']
        else:
            closest_point = None

        print_color('Waypoint','yellow')
        print(closest_point)
        print_color('-'*30,'yellow')

        # 클러스터링 결과 시각화
        # visualize_clusters(filtered_data, sector_points, uam_location, clusters, vertices_array)
    
        return top_cluster_info, closest_point, uam_location