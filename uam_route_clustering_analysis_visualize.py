import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Calculate scale ratio between ax1 and ax2
def match_zero_position(ax1, ax2):
    ax1_ylim = ax1.get_ylim()
    ax2_ylim = ax2.get_ylim()
    ax2_start = (ax2_ylim[1] - ax2_ylim[0]) * (0 - ax1_ylim[0]) / (ax1_ylim[1] - ax1_ylim[0]) + ax2_ylim[0]
    return ax2_start
    
# Load clustering results CSV
file_path = 'results/clustering/uam_waypoint_cluster_analysis_new.csv'
results_df = pd.read_csv(file_path)

# Add Waypoint Index as a column if it's not present
if 'Waypoint_Index' not in results_df.columns:
    results_df['Waypoint_Index'] = results_df.index

# Convert area from m² to km²
results_df['Optimal_Cluster_Area_km2'] = results_df['Optimal_Cluster_Area'] / 1_000_000

# Calculate and print statistics
cluster_count_stats = results_df['Cluster_Count'].agg(['mean', 'min', 'max'])
optimal_area_stats = results_df['Optimal_Cluster_Area_km2'].agg(['mean', 'min', 'max'])
distance_stats = results_df['Distance_to_UAM'].agg(['mean', 'min', 'max'])

print("\nCluster Count Statistics")
print(cluster_count_stats)

print("\nSelected Cluster Area Statistics (km²)")
print(optimal_area_stats)

print("\nMin Distance to UAM Statistics (km)")
print(distance_stats)

# 시각화: 클러스터 개수, 대표 클러스터 면적, 대표 클러스터와의 거리
fig, ax1 = plt.subplots(figsize=(12, 6))

# Left y-axis (Cluster Count, Max Area)
ax1.plot(
    results_df['Waypoint_Index'],
    results_df['Cluster_Count'],
    linestyle='-',
    linewidth=2,
    color='orange',
    label='Cluster Count'
)

ax1.plot(
    results_df['Waypoint_Index'],
    results_df['Optimal_Cluster_Area_km2'],
    linestyle='-',
    linewidth=2,
    color='blue',
    label='Selected Cluster Area (km²)'
)

ax1.set_xlabel('Waypoint Index', fontsize=20)
ax1.set_ylabel('Cluster Count / Selected Cluster Area (km²)', fontsize=20)
ax1.tick_params(axis='y', labelsize=20)
ax1.tick_params(axis='x', labelsize=20)
ax1.grid(alpha=0.5)

# Right y-axis (Min Distance to UAM)
ax2 = ax1.twinx()
ax2.plot(
    results_df['Waypoint_Index'],
    results_df['Distance_to_UAM'],
    linestyle='-',
    linewidth=2,
    color='green',
    label='Min Distance (km)'
)
ax2.set_ylabel('Min Distance (km)', fontsize=20)
ax2.tick_params(axis='y', labelsize=20)

# Align zero positions and ensure max value is 4.0
ax1_min, ax1_max = ax1.get_ylim()
ax2_min, ax2_max = ax2.get_ylim()

# Calculate scaling factor to align zero positions
scaling_factor = ax1_min / ax2_min
aligned_ax2_min = ax2_min * scaling_factor
aligned_ax2_max = ax2_max * scaling_factor

# Adjust the range to maintain the alignment with 4.0 as the maximum
desired_ax2_max = 4.0
adjustment_ratio = desired_ax2_max / aligned_ax2_max
adjusted_ax2_min = aligned_ax2_min * adjustment_ratio

# Set the new range for ax2
ax2.set_ylim(adjusted_ax2_min, desired_ax2_max)

# Add legends
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right', fontsize=20)

# Final adjustments
plt.xlim(0, len(results_df) - 1)  # x축 범위를 0에서 데이터 개수로 설정
plt.tight_layout()
plt.show()
