import glob
import json
import os
import subprocess
import hashlib

from color import analyze_color
from face_emotion_detector import analyze_face_emotion
from intensity_detector import analyze_motion_intensity
from transiton_detector import detect_transitions

# 設定影片資料夾與輸出資料夾
video_folder = "./downloaded_shorts4"
# 參考資料夾（若此處有相同影片則跳過）
reference_folders = ["./downloaded_shorts2", "./downloaded_shorts3"]
output_folder = "./outputs/analysis_json3"
os.makedirs(output_folder, exist_ok=True)

def is_av1(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().lower() == "av1"
    except Exception as e:
        print(f"檢查影片格式失敗: {video_path}，錯誤：{e}")
        return False

def convert_to_h264(input_path, output_path):
    cmd = [
        "ffmpeg", "-y", "-i", input_path, "-c:v", "libx264", "-c:a", "copy", output_path
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"已轉檔為 H.264：{output_path}")
        return True
    except Exception as e:
        print(f"轉檔失敗: {input_path}，錯誤：{e}")
        return False

def analyze_video(video_path):
    results = {}

    # 1. 色彩分析
    try:
        results['color'] = analyze_color(video_path)
    except Exception as e:
        results['color'] = f"Error: {e}"

    # 2. 臉部情緒分析
    try:
        results['face_emotion'] = analyze_face_emotion(video_path)
    except Exception as e:
        results['face_emotion'] = f"Error: {e}"

    # 3. 動態強度
    try:
        motion_json = f"outputs/motion_intensity/{os.path.basename(video_path)}.motion.json"
        os.makedirs("outputs/motion_intensity", exist_ok=True)
        analyze_motion_intensity(video_path, motion_json)
        with open(motion_json, encoding="utf-8") as f:
            results['motion_intensity'] = json.load(f)
    except Exception as e:
        results['motion_intensity'] = f"Error: {e}"

    # 4. 轉場分析
    try:
        results['transition'] = detect_transitions(video_path)
    except Exception as e:
        results['transition'] = f"Error: {e}"

    return results

def file_signature(path, chunk_size=512 * 1024):
    try:
        size = os.path.getsize(path)
        h = hashlib.md5()
        with open(path, "rb") as f:
            head = f.read(chunk_size)
            h.update(head)
            if size > chunk_size:
                f.seek(max(0, size - chunk_size))
                tail = f.read(chunk_size)
                h.update(tail)
        # 使用 (size + md5) 作為簽名
        return f"{size}:{h.hexdigest()}"
    except Exception as e:
        print(f"建立檔案簽名失敗: {path}，錯誤：{e}")
        return None

def build_reference_signatures(folders):
    sigs = set()
    for folder in folders:
        for p in glob.glob(os.path.join(folder, "*.mp4")):
            sig = file_signature(p)
            if sig:
                sigs.add(sig)
    print(f"已建立參考資料夾簽名數量：{len(sigs)}")
    return sigs

if __name__ == "__main__":
    # 建立參考資料夾的簽名集合
    reference_sigs = build_reference_signatures(reference_folders)
    seen_sigs = set()  # 同資料夾內避免重複

    video_files = glob.glob(os.path.join(video_folder, "*.mp4"))[:500]
    
    if not video_files:
        print(f"在 {video_folder} 資料夾中沒有找到任何 .mp4 檔案")
        exit()
    
    print(f"找到 {len(video_files)} 個影片檔案")
    
    for video in video_files:
        # 先做重複檢查
        sig = file_signature(video)
        if sig:
            if sig in reference_sigs:
                print(f"與參考資料夾重複，跳過：{video}")
                continue
            if sig in seen_sigs:
                print(f"同資料夾內重複，跳過：{video}")
                continue
            seen_sigs.add(sig)

        json_name = os.path.splitext(os.path.basename(video))[0] + ".json"
        json_path = os.path.join(output_folder, json_name)
        if os.path.exists(json_path):
            print(f"已分析過，跳過：{video}")
            continue

        # 檢查是否為 AV1，如果是就轉檔
        if is_av1(video):
            temp_h264_path = os.path.join(os.path.dirname(video), f"temp_h264_{os.path.basename(video)}")
            print(f"偵測到 AV1 格式，開始轉檔：{video}")
            if not convert_to_h264(video, temp_h264_path):
                print("轉檔失敗，跳過。")
                continue
            os.replace(temp_h264_path, video)  # 覆蓋原始檔案
            print(f"已覆蓋原始檔案：{video}")

        print(f"分析中: {video}")
        result = analyze_video(video)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"已完成影片分析，結果存於 {output_folder}")