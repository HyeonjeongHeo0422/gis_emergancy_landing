# library.py
import pandas as pd
from shapely import wkt
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Polygon, Point
import shapely.errors
import random
import numpy as np
import math
from matplotlib.patches import Patch, Circle
import geopandas as gpd
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from collections import defaultdict
from sklearn.preprocessing import MinMaxScaler
from haversine import haversine
from geopy.distance import geodesic
