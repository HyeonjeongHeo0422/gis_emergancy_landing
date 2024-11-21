import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load clustering results CSV
file_path = 'results/clustering/region_cluster_analysis.csv'
results_df = pd.read_csv(file_path)

# Define region name mapping
region_name_mapping = ['Jung-gu', 'Dong-gu', 'Seo-gu', 'Nam-gu', 'Buk-gu', 
                       'Suseong-gu', 'Dalseo-gu', 'Dalseong-gun', 'Gunwi-gun']

# Convert area from m² to km²
results_df['Optimal_Cluster_Area_km2'] = results_df['Optimal_Cluster_Area'] / 1_000_000

# Assign region names in a repeated sequence
results_df['Region'] = np.repeat(region_name_mapping, 30)

# Group data by region
grouped_results = results_df.groupby('Region')

# Loop through each region to calculate statistics and generate plots
for region, group in grouped_results:
    # Calculate statistics
    distance_stats = group['Distance_to_UAM'].agg(['mean', 'min', 'max', 'std'])
    optimal_area_stats = group['Optimal_Cluster_Area_km2'].agg(['mean', 'min', 'max', 'std'])
    cluster_polygon_count_stats = group['Optimal_Cluster_Polygon_Count'].agg(['mean', 'min', 'max', 'std'])

    # print(f'[{region}]')

    # print("\nMin Distance to UAM Statistics (km)")
    # print(distance_stats)

    # print("\nSelected Cluster Area Statistics (km²)")
    # print(optimal_area_stats)

    # print("\nCluster Polygon Count Statistics")
    # print(cluster_polygon_count_stats)

    # print('-'*50)

distance_stats = results_df['Distance_to_UAM'].agg(['mean', 'min', 'max', 'std'])
optimal_area_stats = results_df['Optimal_Cluster_Area_km2'].agg(['mean', 'min', 'max', 'std'])
cluster_polygon_count_stats = results_df['Optimal_Cluster_Polygon_Count'].agg(['mean', 'min', 'max', 'std'])

print('Daegu')

print("\nMin Distance to UAM Statistics (km)")
print(distance_stats)

print("\nSelected Cluster Area Statistics (km²)")
print(optimal_area_stats)

print("\nCluster Polygon Count Statistics")
print(cluster_polygon_count_stats)

print('-'*50)

# for region, group in grouped_results:
#     print(f'[{region}] Max Distance to UAM: {group["Distance_to_UAM"].max()}')
# print('-'*50)

# Common style settings
label_fontsize = 20
tick_fontsize = 18
line_width = 2.5

# Define boxplot helper function
# def plot_box(data, column, ylabel, title, output_file):
# def plot_box(data, column, ylabel):
#     plt.figure(figsize=(14, 8))
#     data_to_plot = [data[data['Region'] == region][column] for region in region_name_mapping]
#     plt.boxplot(data_to_plot, labels=region_name_mapping,
#                 boxprops=dict(linewidth=line_width, color='black'),
#                 medianprops=dict(linewidth=line_width, color='red'),
#                 whiskerprops=dict(linewidth=line_width),
#                 capprops=dict(linewidth=line_width),
#                 flierprops=dict(marker='', linestyle='none'))  # Disable outlier markers
#     # plt.title(title, fontsize=label_fontsize)
#     plt.xlabel('Region', fontsize=label_fontsize, labelpad=20)
#     plt.ylabel(ylabel, fontsize=label_fontsize, labelpad=20)
#     plt.xticks(rotation=45, fontsize=tick_fontsize)
#     plt.yticks(fontsize=tick_fontsize)
#     plt.tight_layout()
#     # plt.savefig(output_file)
#     # plt.show()

def plot_box(data, column, ylabel):
    plt.figure(figsize=(14, 8))
    data_to_plot = [data[data['Region'] == region][column] for region in region_name_mapping]
    # Verify the data used for plotting
    # for region, values in zip(region_name_mapping, data_to_plot):
    #     print(f'[{region}] Max Value for {column}: {values.max() if not values.empty else "No Data"}')
    plt.boxplot(data_to_plot, labels=region_name_mapping,
                boxprops=dict(linewidth=2.5, color='black'),
                medianprops=dict(linewidth=2.5, color='red'),
                whiskerprops=dict(linewidth=2.5),
                capprops=dict(linewidth=2.5),
                flierprops=dict(marker='o', color='blue', alpha=0.5, markersize=10))  # Enable outlier markers
    plt.xlabel('Region', fontsize=20, labelpad=20)
    plt.ylabel(ylabel, fontsize=20, labelpad=20)
    plt.xticks(rotation=45, fontsize=18)
    plt.yticks(fontsize=18)
    plt.tight_layout()

# Box Plot: Distance to UAM
plot_box(
    results_df, 'Distance_to_UAM',
    ylabel='Distance to UAM (km)'
    # title='Distance to UAM by Region',
    # output_file='results/clustering/boxplot_distance_to_uam.png'
)

# Box Plot: Optimal Cluster Area (km²)
plot_box(
    results_df, 'Optimal_Cluster_Area_km2',
    ylabel='Optimal Cluster Area (km²)'
    # title='Optimal Cluster Area by Region',
    # output_file='results/clustering/boxplot_optimal_cluster_area.png'
)

# Box Plot: Optimal Cluster Polygon Count
plot_box(
    results_df, 'Optimal_Cluster_Polygon_Count',
    ylabel='Optimal Cluster Polygon Count'
    # title='Optimal Cluster Polygon Count by Region',
    # output_file='results/clustering/boxplot_optimal_cluster_polygon_count.png'
)

# plt.show()

# data_to_plot = [results_df[results_df['Region'] == region]['Distance_to_UAM'] for region in region_name_mapping]
# for region, data in zip(region_name_mapping, data_to_plot):
#     print(f'[{region}] Max Distance: {data.max() if not data.empty else "No Data"}')
