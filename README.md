# ViralCatcher: AI 短影音多維度特徵分析系統

本倉庫存放 **ViralCatcher** 畢業專題中的核心影像處理與數據分析模組。本系統旨在透過電腦視覺（Computer Vision）技術，自動化提取短影音中的視覺、情感與節奏特徵，並為後續的爆紅潛力預測模型提供量化數據。

## 🚀 核心模組說明

本專案包含以下關鍵技術實作：

### 1. 🎬 影像動態與節奏分析 (`intensity_detector.py`, `transiton_detector.py`)
* **動態強度 (Motion Intensity)**：採用 **Farneback Optical Flow (光流法)** 計算幀與幀之間的運動向量，量化影片的視覺張力與動態節奏。
* **轉場偵測 (Transition Detection)**：透過比較幀間的 **Color Histogram (色彩直方圖)** 差異，自動計算影片的轉場密度，評估剪輯節奏。

### 2. 😊 情緒與人臉辨識 (`face_emotion_detector.py`)
* **多模型整合**：結合 `InsightFace` 進行高精度人臉偵測，並利用 `DeepFace` 框架分析主角的情緒分布（如快樂、驚訝、中性等）。
* **人物聚類 (Face Clustering)**：使用 **Agglomerative Clustering (層次聚類)** 技術，在多人影片中精準鎖定並分析主要人物。

### 3. 🎨 色彩心理學特徵 (`color.py`)
* **主色調提取**：運用 **K-Means Clustering** 演算法從影像中提取主要色調。
* **視覺風格量化**：分析影片的 **Hue (色相)** 與 **Saturation (飽和度)**，並自動分類為冷色調、暖色調或中性調。

### 4. 📥 自動化數據收集 (`shorts_downloader.py`)
* **YouTube API 整合**：透過 YouTube Data API v3 根據關鍵字自動檢索短影音。
* **多線程下載**：整合 `yt-dlp` 進行高效能影片抓取，並具備過濾觀看數門檻與自動重複項排除功能。

## 🛠 技術棧 (Tech Stack)
- **Programming Language**: Python 3.10+
- **Computer Vision**: OpenCV, InsightFace, DeepFace, MTCNN
- **Data Science**: NumPy, Pandas, Scikit-learn (K-Means, Agglomerative Clustering)
- **Tools**: FFmpeg, YouTube Data API v3, yt-dlp

## 📈 應用價值
本模組能將非結構化的影片檔案轉化為結構化的數值特徵（Features），包含：
- **平均動態強度**、**轉場密度**
- **情緒比例分佈** (Happy/Sad/Surprise...)
- **色彩風格分佈** (Color Styles & Dominant Colors)

這些數據最終被餵入 **Random Forest (隨機森林)** 模型中，實現準確率達 92% 的爆紅潛力預測。

---
*本專案為國立中央大學資管系畢業專題之部分成果。*