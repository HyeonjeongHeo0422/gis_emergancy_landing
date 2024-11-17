import pandas as pd
import matplotlib.pyplot as plt

# 행정구역 리스트
region_names = ['중구', '동구', '서구', '남구', '북구', '수성', '달서구', '달성군', '군위군']

# 데이터 병합을 위한 빈 리스트
all_data = []

# 각 행정구역의 데이터를 로드하고 병합
for region_name in region_names:
    try:
        # 파일 경로 설정
        file_path = f'results/filtering/Database/{region_name}_final_filtered_polygons_with_center.csv'
        
        # 데이터 로드
        data = pd.read_csv(file_path)
        
        # 'Area (m^2)'를 'Area'로 사용
        if 'Area (m^2)' in data.columns:
            data.rename(columns={'Area (m^2)': 'Area'}, inplace=True)
        
        # 면적을 km²로 변환
        data['Area (km^2)'] = data['Area'] / 1e6
        
        # 행정구역 이름 추가
        data['Region'] = region_name
        
        # 병합 리스트에 추가
        all_data.append(data[['Area (km^2)', 'Region']])
    
    except FileNotFoundError:
        print(f"File not found for region: {region_name}")
    except Exception as e:
        print(f"An error occurred for region {region_name}: {e}")

# 모든 데이터를 하나의 데이터프레임으로 병합
combined_data = pd.concat(all_data, ignore_index=True)

# 한글 지역명을 영어로 변환
region_name_mapping = {
    '중구': 'Jung-gu',
    '동구': 'Dong-gu',
    '서구': 'Seo-gu',
    '남구': 'Nam-gu',
    '북구': 'Buk-gu',
    '수성': 'Suseong-gu',
    '달서구': 'Dalseo-gu',
    '달성군': 'Dalseong-gun',
    '군위군': 'Gunwi-gun'
}
combined_data['Region'] = combined_data['Region'].map(region_name_mapping)

# x축 순서를 지정하기 위해 'Region' 열을 Categorical로 변환
region_order = [region_name_mapping[region] for region in region_names]  # 영어 이름으로 순서 매핑
combined_data['Region'] = pd.Categorical(combined_data['Region'], categories=region_order, ordered=True)

# 박스플롯 생성
# plt.figure(figsize=(20, 14))
fig, ax = plt.subplots(figsize=(20, 14))
combined_data.boxplot(
    column='Area (km^2)', by='Region', grid=False,
    boxprops=dict(linewidth=2.5),
    whiskerprops=dict(linewidth=2.5),
    capprops=dict(linewidth=2.5),
    medianprops=dict(linewidth=2.5, color='red'),
    flierprops=dict(marker='')  # 이상치 비활성화
)

# y축 범위 설정 (예: 0부터 2 km²까지)
plt.ylim(0, 0.2)

# 플롯 구성
# plt.title('Area Distribution by Region', fontsize=20)
# plt.suptitle('')  # 기본 제목 제거
plt.ylabel('Area (km²)', fontsize=20, labelpad=20)
plt.xlabel('')  # X축 레이블 제거
ax.set_title('')  # title 속성 제거
plt.suptitle('')  # 기본 제목 제거
plt.xticks(rotation=45, fontsize=20)
plt.yticks(fontsize=20)
plt.tight_layout()

# 플롯 저장 및 표시
# plt.savefig('results/filtering/analysis/boxplot_area_all_regions.png')
# plt.show()

# 각 행정구역별 면적 평균 및 표준편차 출력
for region in region_order:
    region_data = combined_data[combined_data['Region'] == region]
    mean_area = region_data['Area (km^2)'].mean()
    std_area = region_data['Area (km^2)'].std()
    print(f"Region: {region}, Mean Area: {mean_area:.2f} km², Standard Deviation: {std_area:.2f} km²")




# # 박스플롯 생성
# fig, ax = plt.subplots(figsize=(20, 14))
# combined_data.boxplot(
#     column='Area (km^2)', by='Region', grid=False, ax=ax,
#     boxprops=dict(linewidth=2.5),
#     whiskerprops=dict(linewidth=2.5),
#     capprops=dict(linewidth=2.5),
#     medianprops=dict(linewidth=2.5, color='red'),
#     flierprops=dict(marker='')  # 이상치 비활성화
# )

# # y축 범위 설정 (예: 0부터 0.2 km²까지)
# ax.set_ylim(0, 0.2)

# # 플롯 구성
# ax.set_ylabel('Area (km²)', fontsize=20, labelpad=20)
# ax.set_xlabel('')  # X축 레이블 제거
# ax.set_title('')  # 제목 제거
# ax.tick_params(axis='x', rotation=45, labelsize=20)
# ax.tick_params(axis='y', labelsize=20)

# # 레이아웃 설정 및 저장
# fig.tight_layout()
# fig.savefig('results/filtering/analysis/boxplot_area_all_regions.png')
# plt.show()
