import cv2
import numpy as np
import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def analyze_motion_intensity(video_path, output_json_path, frame_interval=0.5):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    skip_frames = int(fps * frame_interval)

    ret, prev_frame = cap.read()
    if not ret:
        print("Failed to read video.")
        return

    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    frame_idx = 0
    motion_scores = []
    motion_values = []

    while True:
        for _ in range(skip_frames):
            cap.read()

        ret, curr_frame = cap.read()
        if not ret:
            break

        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray,
                                            None, 0.5, 3, 15, 3, 5, 1.2, 0)

        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        motion_score = np.mean(magnitude)

        motion_scores.append({
            "frame": frame_idx,
            "timestamp_sec": round(frame_idx / fps, 2),
            "motion_intensity": float(motion_score)
        })

        motion_values.append(motion_score)
        prev_gray = curr_gray
        frame_idx += skip_frames

    cap.release()

    # 統計資訊
    avg_motion = float(np.mean(motion_values)) if motion_values else 0.0
    std_motion = float(np.std(motion_values)) if motion_values else 0.0
    peak_threshold = avg_motion + std_motion
    peak_count = sum(1 for score in motion_values if score > peak_threshold)
    peak_ratio = peak_count / len(motion_values) if motion_values else 0.0
    std_mean_ratio = std_motion / avg_motion if avg_motion > 0 else 0.0

    summary = {
        "average_motion_intensity": avg_motion,  # 全片平均動態強度
        "std_to_mean_motion_ratio": std_mean_ratio,  # 動態強度標準差與平均值之比
        "high_motion_peak_ratio": peak_ratio  # 
    }

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    print(f"[INFO] 動態強度分析完成。")
    print(f"[INFO]  全片平均動態強度: {avg_motion:.2f}，動態強度標準差與平均值之比: {std_mean_ratio}，高於(平均+標準差)的高動態幀比例: {peak_ratio}")
    print(f"[INFO] 結果已儲存至：{output_json_path}")


if __name__ == "__main__":
    video_path = 'D:/Users/81150/Desktop/youtube_short_analysis/downloaded_shorts/Only $2! The best egg fried rice in Taiwan.mp4'
    output_json_path = 'D:/Users/81150/Desktop/youtube_short_analysis/outputs/analysis/motion_intensity/Only $2! The best egg fried rice in Taiwan.json'
    frame_interval = 0.5

    analyze_motion_intensity(video_path, output_json_path, frame_interval)

