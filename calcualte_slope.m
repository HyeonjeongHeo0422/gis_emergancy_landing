% 구 폴더 목록
guNames = {'남구', '달서구', '동구', '북구', '서구', '수성구', '중구'};
% guNames = {'북구'};
basePath = 'data'; % 데이터가 저장된 기본 경로

% Waitbar 생성
hWaitbar = waitbar(0, 'Processing...');

% 데이터 처리 및 시각화
for i = 1:length(guNames)
    % Waitbar 업데이트
    waitbar(i / length(guNames), hWaitbar, sprintf('Processing %s...', guName));

    guName = guNames{i};
    
    % Shape 파일 읽기
    elevationFile = fullfile(basePath, guName, 'N3P_F0020000.shp');
    contourFile = fullfile(basePath, guName, 'N3L_F0010000.shp');

    elevation = shaperead(elevationFile);
    contours = shaperead(contourFile);
    
    % 현재 좌표계를 EPSG:5179로 정의 (투영된 좌표계)
    currentCrs = projcrs(5179); 
    
    % Elevation 데이터 좌표 변환 수행
    for k = 1:length(elevation)
        [lat, lon] = projinv(currentCrs, elevation(k).X, elevation(k).Y); % 투영된 좌표계에서 지리적 좌표계로 변환
        elevation(k).X = lon;
        elevation(k).Y = lat;
    end
    
    % Contour 데이터 좌표 변환 수행
    for k = 1:length(contours)
        [lat, lon] = projinv(currentCrs, contours(k).X, contours(k).Y); % 투영된 좌표계에서 지리적 좌표계로 변환
        contours(k).X = lon;
        contours(k).Y = lat;
    end
    
    % 표고점 데이터와 등고선 데이터의 좌표 및 고도 정보 결합
    latElev = [elevation.Y];
    lonElev = [elevation.X];
    elevValues = [elevation.NUME]; % 'NUME' 필드가 표고 값
    
    latContours = [];
    lonContours = [];
    contourValues = [];
    
    for k = 1:length(contours)
        latContours = [latContours, contours(k).Y];
        lonContours = [lonContours, contours(k).X];
        contourValues = [contourValues, repmat(contours(k).CONT, 1, length(contours(k).X))];
    end
   
    % 모든 좌표와 고도 정보 결합
    allLat = [latElev, latContours];
    allLon = [lonElev, lonContours];
    allElev = [elevValues, contourValues];
    
    % 그리드의 범위 설정
    latMin = min(allLat);
    latMax = max(allLat);
    lonMin = min(allLon);
    lonMax = max(allLon);
    
    % 지구의 반지름 (m)
    earthRadius = 6371000;
    
    % 위도와 경도 범위를 미터 단위로 변환
    latRange = latMax - latMin;
    lonRange = lonMax - lonMin;
    
    % 위도와 경도의 차이를 미터로 변환
    latDist = (pi / 180) * earthRadius * latRange;
    lonDist = (pi / 180) * earthRadius * lonRange * cosd((latMin + latMax) / 2);
    
    % 그리드 크기 설정 (10m)
    gridSize = 10;
    
    % 그리드 점의 수 계산
    numLatPoints = ceil(latDist / gridSize);
    numLonPoints = ceil(lonDist / gridSize);
    
    % 그리드 해상도 설정
    latGrid = linspace(latMin, latMax, numLatPoints);
    lonGrid = linspace(lonMin, lonMax, numLonPoints);
    
    
    % NaN 및 Inf 값을 제거
    validIdx = ~isnan(allLat) & ~isnan(allLon) & ~isnan(allElev) & ...
               ~isinf(allLat) & ~isinf(allLon) & ~isinf(allElev);
    
    allLat = allLat(validIdx);
    allLon = allLon(validIdx);
    allElev = allElev(validIdx);
    
    % 알파 쉐이프를 사용하여 경계를 설정
    shp = alphaShape(allLon', allLat', 2); 
    
    % 고도 데이터를 그리드로 보간
    [lonMesh, latMesh] = meshgrid(lonGrid, latGrid);
    % elevGrid = griddata(allLon, allLat, allElev, lonMesh, latMesh, 'natural');
    elevGrid = griddata(allLon, allLat, allElev, lonMesh, latMesh, 'cubic');
    
    % 경계 외부 값을 NaN으로 설정하기 위해 경계를 구함
    x = reshape(allLon, [numel(allLon), 1]);
    y = reshape(allLat, [numel(allLat), 1]);
    k = boundary(x, y);
    
    % 경계 다각형을 만들어 경계 외부 값들을 NaN으로 설정
    inBoundary = inpolygon(lonMesh, latMesh, x(k), y(k));
    
    % 경계 근처의 값을 포함시키기 위해 dilate 연산 적용
    dilatedBoundary = imdilate(inBoundary, strel('disk', 2)); % 디스크 형태의 구조 요소 사용, 반경 2
    
    % dilatedBoundary 내의 경계 외부 값들을 NaN으로 설정
    elevGrid(~dilatedBoundary) = NaN;
      
    % 경사도 계산
    [dx, dy] = gradient(elevGrid);
    slope = sqrt(dx.^2 + dy.^2);
    
    % 경사도 11도 이하만 추출
    mask = slope <= 11;
    slopeMasked = slope .* mask;
    
    % 경사도 시각화 (11도 이하만)
    figure;
    h2 = imagesc(lonGrid, latGrid, slopeMasked);
    set(gca, 'YDir', 'normal');
    colorbar;
%     title('경사도 (11도 이하)', 'FontSize', 14);
    title([guName, ' 경사도 (11도 이하)'], 'FontSize', 14);
    xlabel('경도', 'FontSize', 14);
    ylabel('위도', 'FontSize', 14);
    
    % NaN 값을 투명하게 설정 (11도 이하가 아닌 값들을 NaN으로 설정)
    slopeMasked(~mask) = NaN;
    set(h2, 'AlphaData', ~isnan(slopeMasked));
    
    hold on;
    plot(x(k), y(k), 'k', 'LineWidth', 2);
    hold off;

    % 이미지 파일로 저장
    saveas(gcf, fullfile(basePath, guName, [guName, '_slope_under_11.png']));

    % 경사도 11도 이하인 지점의 좌표와 경사도 값 추출
    validLat = latMesh(mask);
    validLon = lonMesh(mask);
    validSlope = slope(mask);

    % 데이터 테이블로 저장
    T = table(validLat, validLon, validSlope, 'VariableNames', {'Latitude', 'Longitude', 'Slope'});
    writetable(T, fullfile(basePath, guName, [guName, '_slope_under_11.csv']));
end

% Waitbar 닫기
close(hWaitbar);

