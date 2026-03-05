import cv2
import numpy as np
from sklearn.cluster import KMeans
from matplotlib.colors import rgb_to_hsv
from collections import Counter

def rgb_to_hex(rgb):
    return '#{:02X}{:02X}{:02X}'.format(*rgb)

def analyze_color(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Unable to open video file."}

    frame_rate = 5  # 每秒擷取五幀
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, int(fps / frame_rate))

    dominant_colors = []
    saturation_levels = []
    hue_values = []
    color_styles = []
    red_ratios = []
    green_ratios = []
    blue_ratios = []

    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    prev_frame = None
    scene_change_threshold = 50.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            # 主色調和飽和度分析
            def get_dominant_color(image, k=20):
                image = cv2.resize(image, (200, 200))
                image = image.reshape((-1, 3))
                kmeans = KMeans(n_clusters=k, random_state=42)
                kmeans.fit(image)
                colors = kmeans.cluster_centers_.astype(int)
                counts = np.bincount(kmeans.labels_)
                dominant = colors[np.argmax(counts)]
                return dominant  # [B, G, R]

            def get_saturation(image):
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                saturation = hsv[:, :, 1]
                return np.mean(saturation)

            dom_color = get_dominant_color(frame, k=20)
            sat = get_saturation(frame)

            rgb_color = [dom_color[2] / 255.0, dom_color[1] / 255.0, dom_color[0] / 255.0]
            hsv_color = rgb_to_hsv(np.array(rgb_color))
            hue = hsv_color[0] * 360

            if 180 <= hue <= 300:
                style = "Cool"
            elif 0 <= hue <= 60 or 300 <= hue <= 360:
                style = "Warm"
            else:
                style = "Neutral"

            total_pixels = frame.shape[0] * frame.shape[1]
            red_ratio = np.sum(frame[:, :, 2] > 128) / total_pixels
            green_ratio = np.sum(frame[:, :, 1] > 128) / total_pixels
            blue_ratio = np.sum(frame[:, :, 0] > 128) / total_pixels

            dominant_colors.append(dom_color.tolist())
            saturation_levels.append(float(sat))
            hue_values.append(float(hue))
            color_styles.append(style)
            red_ratios.append(float(red_ratio))
            green_ratios.append(float(green_ratio))
            blue_ratios.append(float(blue_ratio))

        frame_count += 1

    cap.release()

    # 統計結果
    avg_color = np.mean(dominant_colors, axis=0).tolist() if dominant_colors else [0, 0, 0]
    avg_saturation = float(np.mean(saturation_levels)) if saturation_levels else 0.0
    avg_hue = float(np.mean(hue_values)) if hue_values else 0.0
    style_counts = {
        "Cool": color_styles.count("Cool"),
        "Warm": color_styles.count("Warm"),
        "Neutral": color_styles.count("Neutral")
    }

    # 每幀摘要（四捨五入）
    frame_summaries = [
        {
            "dominant_color": [int(x) for x in dominant_colors[i]],
            "saturation": round(saturation_levels[i], 2),
            "hue": round(hue_values[i], 2),
            "style": color_styles[i]
        }
        for i in range(len(dominant_colors))
    ]

    # 主色分布統計（只保留前10名）
    hex_colors = [rgb_to_hex(c) for c in dominant_colors]
    color_counter = Counter(hex_colors)
    total = len(hex_colors)
    dominant_color_distribution = {
        color: round(count / total, 3)
        for color, count in color_counter.most_common(10)
    }
    return {
        "dominant_color_distribution": dominant_color_distribution
    }