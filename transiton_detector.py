import cv2
import numpy as np

def detect_transitions(video_path):
    cap = cv2.VideoCapture(video_path)
    prev_hist = None
    transition_count = 0
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        hist = cv2.calcHist([frame], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        if prev_hist is not None:
            score = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
            if score > 1.5:
                transition_count += 1
        prev_hist = hist
        frame_idx += 1
    cap.release()
    transition_density = transition_count / frame_idx if frame_idx > 0 else 0
    return {
        "transition_density": round(transition_density, 4)
    }