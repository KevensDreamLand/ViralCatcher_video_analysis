import os
import cv2
import numpy as np
from deepface import DeepFace
from mtcnn1 import MTCNN
import insightface
from insightface.utils.face_align import norm_crop
from sklearn.cluster import AgglomerativeClustering
import collections

# 可選：減少 TensorFlow/DeepFace 日誌輸出
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

class FaceClusterer:
    def __init__(self, distance_threshold=0.7):
        self.distance_threshold = distance_threshold

    def cluster_embeddings(self, embeddings):
        embeddings = np.array(embeddings)
        model = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.distance_threshold,
            metric='cosine',
            linkage='average'
        )
        labels = model.fit_predict(embeddings)
        return labels

class InsightFaceDetector:
    def __init__(self, det_size=(512, 512), gpu=True):  # 降 det_size 提升速度
        self.app = insightface.app.FaceAnalysis(name="buffalo_l")
        ctx_id = 0 if gpu else -1
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)

    def detect_faces(self, img):
        faces = self.app.get(img)
        return faces

    def align_face(self, img, landmarks):
        aligned_face = norm_crop(img, landmarks)
        return aligned_face

    def extract_faces_from_frame(self, img, min_confidence=0.7):
        faces_data = []
        faces = self.detect_faces(img)
        for face in faces:
            if face.det_score < min_confidence:
                continue
            aligned_face = self.align_face(img, face.kps)
            faces_data.append({
                "bbox": face.bbox.tolist(),
                "keypoints": face.kps.tolist(),
                "aligned_face": aligned_face,
                "embedding": face.embedding.tolist(),
                "det_score": face.det_score
            })
        return faces_data

def extract_frames(video_path, target_fps=1.0):
    """
    以 target_fps 抽幀（預設 1fps），避免讀取每一幀。
    """
    cap = cv2.VideoCapture(video_path)
    real_fps = cap.get(cv2.CAP_PROP_FPS)
    if not real_fps or real_fps <= 0:
        real_fps = 30.0

    frame_interval = max(1, int(round(real_fps / max(0.1, target_fps))))

    frames = []
    frame_idx = 0
    # 讀一幀、跳過 frame_interval-1 幀（用 grab 較快）
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append((frame_idx, frame))
        # 跳過中間幀以節省時間
        for _ in range(frame_interval - 1):
            if not cap.grab():
                break
        frame_idx += frame_interval
    cap.release()
    return frames, real_fps

def _infer_emotion_fast(img):
    """
    直接對齊後的人臉跑 DeepFace 情緒，跳過偵測步驟。
    """
    try:
        res = DeepFace.analyze(
            img,
            actions=['emotion'],
            enforce_detection=False,         # 已對齊人臉，不強制偵測
            detector_backend='skip',         # 跳過 face detector（大幅加速）
            prog_bar=False
        )
        # DeepFace 可能回傳 list 或 dict
        if isinstance(res, list) and res:
            return res[0].get('dominant_emotion', 'unknown')
        if isinstance(res, dict):
            return res.get('dominant_emotion', 'unknown')
        return 'unknown'
    except Exception:
        return 'unknown'

def analyze_face_emotion(video_path, target_fps=1.0, interval_sec=5, emotion_stride=3, det_size=(512, 512), gpu=True):
    """
    加速版情緒分析：
    - target_fps: 幀抽樣率（預設 1 fps）
    - emotion_stride: 每 N 幀才跑一次 DeepFace（預設 3）
    - det_size: InsightFace 偵測解析度（預設 512x512）
    """
    # 1. 抽幀（少幀）
    frames, video_fps = extract_frames(video_path, target_fps=target_fps)
    detector = InsightFaceDetector(det_size=det_size, gpu=gpu)
    all_embeddings = []
    frame_results = []

    # 2. 偵測臉與抽特徵（快）
    for frame_idx, frame in frames:
        faces_data = detector.extract_faces_from_frame(frame, min_confidence=0.7)
        frame_result = {
            "frame": frame_idx,
            "timestamp_sec": round(frame_idx / max(1e-6, video_fps), 2),
            "faces": []
        }
        for face_data in faces_data:
            all_embeddings.append(face_data["embedding"])
            frame_result["faces"].append({
                "bbox": face_data["bbox"],
                "keypoints": face_data["keypoints"],
                "det_score": face_data["det_score"],
                "aligned_face": face_data["aligned_face"],
                "embedding": face_data["embedding"],
                "emotion": None
            })
        frame_results.append(frame_result)

    # 3. 聚類找主角（對大量幀已抽稀）
    clusterer = FaceClusterer()
    if all_embeddings:
        labels = clusterer.cluster_embeddings(all_embeddings)
        counter = collections.Counter(labels)
        dominant_label = counter.most_common(1)[0][0]
        label_idx = 0
        for fr in frame_results:
            for face in fr["faces"]:
                face["cluster_label"] = int(labels[label_idx])
                face["is_main_person"] = (labels[label_idx] == dominant_label)
                label_idx += 1

    # 4. 主角臉做情緒分析（每 emotion_stride 幀跑一次，其他沿用上次）
    last_emotion = None
    frame_counter = 0
    for fr in frame_results:
        main_faces = [f for f in fr["faces"] if f.get("is_main_person")]
        if not main_faces:
            continue
        # 只取第一張主角臉（多臉時也能加速）
        face = main_faces[0]
        if frame_counter % max(1, emotion_stride) == 0 or last_emotion is None:
            face["emotion"] = _infer_emotion_fast(face["aligned_face"])
            last_emotion = face["emotion"]
        else:
            face["emotion"] = last_emotion
        frame_counter += 1

    # 5. 統計全片情緒百分比
    emotion_counts = {}
    total_faces = 0
    for fr in frame_results:
        for face in fr["faces"]:
            if face.get("is_main_person"):
                emo = face.get("emotion")
                if emo:
                    emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
                    total_faces += 1
    emotion_percentages = {
        emotion: (count / total_faces) * 100 for emotion, count in emotion_counts.items()
    } if total_faces > 0 else {}

    # 6. 每 interval_sec 秒的情緒變化（用抽稀後的幀）
    interval_results = []
    if frame_results:
        max_time = max(fr["timestamp_sec"] for fr in frame_results)
        intervals = np.arange(0, max_time + interval_sec, interval_sec)
        for i in range(len(intervals) - 1):
            start, end = intervals[i], intervals[i + 1]
            emotions_in_interval = []
            for fr in frame_results:
                if start <= fr["timestamp_sec"] < end:
                    for face in fr["faces"]:
                        if face.get("is_main_person"):
                            emotions_in_interval.append(face.get("emotion"))
            total = len(emotions_in_interval)
            if total > 0:
                counter = collections.Counter(emotions_in_interval)
                interval_percent = {
                    emotion: round(count / total * 100, 2)
                    for emotion, count in counter.items()
                }
            else:
                interval_percent = {}
            interval_results.append({
                "start_sec": round(start, 2),
                "end_sec": round(end, 2),
                "emotion_percentages": interval_percent
            })

    return {
        "emotion_percentages": emotion_percentages,
        "emotion_fluctuation": interval_results
    }
