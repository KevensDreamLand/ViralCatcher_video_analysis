from googleapiclient.discovery import build
import os
import json
import subprocess
import sys
import re
import glob
sys.stdout.reconfigure(encoding='utf-8')

# === YouTube API Configuration ===
API_KEY =''
# 'AIzaSyDWIUGYph1DkyQ-07U1ts5G6Avn1IYts3A'
# 'AIzaSyCVK9BjVDKd9hBhxAS7hXrZwZMuCKqZbZ4'
#  'AIzaSyC8yLFNQdGOGanyTp09IHrJAdEA8Z1neaU' # 請替換為您的 YouTube API 金鑰
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# === Search Parameters ===
SEARCH_QUERIES = [
    # 中文關鍵字（可依需求啟用）
    #'台灣美食', '美食開箱', '台灣小吃', '夜市小吃', '美食', '高雄美食', '台南美食', '台北小吃', '台北美食',
    #'美食介紹', '小吃介紹',
    #'台中美食', '隱藏美食', '網美餐廳',
    #'吃吃喝喝', '美食Vlog', '美食推薦',
    #'老街小吃','美食探店','屏東美食','我是智明','平價美食',
    #'台南必吃','台北必吃','高雄必吃','台中必吃','夜市必吃','必吃美食','新竹美食','宜蘭美食','彰化美食','南投美食','花蓮美食','台東美食','屏東美食','苗栗美食','基隆美食','桃園美食','新北美食','澎湖美食',
    #'路邊美食', '路邊攤美食', '路邊小吃', '路邊美食推薦', '路邊美食開箱', '路邊美食介紹', '路邊美食Vlog',
    #'銅板美食', '銅板小吃', '銅板美食推薦', '銅板美食開箱', '銅板美食介紹', '銅板美食Vlog',
    #'平價美食', '平價小吃', '平價美食推薦', '平價美食開箱', '平價美食介紹', '平價美食Vlog',
    #'夜市美食','夜市美食推薦','夜市美食開箱','夜市美食介紹','夜市美食Vlog','台灣小吃','小吃推薦','桃園必吃',
    #'花蓮必吃','澎湖必吃','台東必吃','屏東必吃','苗栗必吃','基隆必吃','新北必吃','新竹必吃','宜蘭必吃','彰化必吃','南投必吃',
    #'景點美食','宜蘭小吃推薦','南投隱藏美食','澎湖小吃','花蓮小吃','台東小吃','苗栗小吃','基隆小吃','甜點推薦','早餐推薦',
    #'早餐必吃', '午餐必吃', '晚餐必吃', '宵夜必吃', '台灣美食推薦', '台灣小吃推薦', '台灣夜市美食', '台灣隱藏美食',
    #'台灣平價美食', '台灣路邊美食', '台灣銅板美食', '台灣景點美食',
    #'澎湖海鮮', '澎湖美食', '澎湖小吃', '澎湖隱藏美食', '澎湖平價美食', '澎湖路邊美食', '澎湖銅板美食',
    #'吃到飽推薦', '吃到飽美食', '吃到飽餐廳', '吃到飽自助餐', '吃到飽火鍋', '吃到飽燒烤', '吃到飽海鮮',

    # 美食介紹英文關鍵字
    #'delicious food', 'tasty food', 'street food', 'mouthwatering food', 'food vlog', 'flavorful dish', 'aromatic cuisine', 'spicy food', 'sweet dessert', 'creamy dessert','authentic cuisine',
   # 'local specialty', 'must-try food',
    #'gourmet food', 'homemade food', 'traditional food', 'comfort food',
    #'fusion cuisine',
    '#shorts food', '#foodshorts', '#streetfood', '#foodie', '#foodvlog', '#asmr'
]

# 目標影片數與觀看數門檻設定
TARGET_COUNT = 500
MIN_VIEWS_PRIMARY = 500000   # 初始門檻
MIN_VIEWS_FALLBACK = 50000   # 不足時降低門檻

# 回補關鍵字（當不足 500 時才使用）
FALLBACK_QUERIES = [
     'night market food', 'restaurant food', 'food street', 'food short', 'chef cooking', '#shorts food'
]
MAX_RESULTS = 50
DOWNLOAD_FOLDER = 'downloaded_shorts4'
JSON_OUTPUT_FILE = 'shorts_data3.json'

# 參考資料夾（避免重複下載）
REFERENCE_FOLDERS = ['downloaded_shorts2', 'downloaded_shorts3']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _abs(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)

def load_archive_ids(archive_path: str) -> set[str]:
    ids = set()
    ap = _abs(archive_path)
    if os.path.exists(ap):
        try:
            with open(ap, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # yt-dlp 存的是 "youtube <id>" 或 "<id>"，都處理
                    parts = line.split()
                    vid = parts[-1] if parts else ''
                    if re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
                        ids.add(vid)
        except Exception:
            pass
    return ids

def collect_reference_ids() -> set[str]:
    ref_ids = set()
    # 從本專案的 shorts_data*.json 收集 ID
    for j in glob.glob(os.path.join(BASE_DIR, 'shorts_data*.json')):
        try:
            with open(j, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    vid = item.get('id')
                    if isinstance(vid, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
                        ref_ids.add(vid)
        except Exception:
            continue
    # 從參考資料夾檔名擷取 (VIDEO_ID)
    id_pat = re.compile(r'\(([A-Za-z0-9_-]{11})\)')
    for folder in REFERENCE_FOLDERS:
        abs_folder = _abs(folder)
        if not os.path.isdir(abs_folder):
            continue
        for p in glob.glob(os.path.join(abs_folder, '*.mp4')):
            m = id_pat.search(os.path.basename(p))
            if m:
                ref_ids.add(m.group(1))
    return ref_ids

# === Initialize YouTube API Client ===
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)

# === Search Shorts ===
def search_short_videos(query, max_results):
    request = youtube.search().list(
        q=query,
        part='id,snippet',
        type='video',
        videoDuration='short',  # 確保只搜尋短影片
        order='viewCount',  # 按觀看數排序
        maxResults=max_results
    )
    response = request.execute()
    return response.get('items', [])

# === Get Video Details ===
def get_video_details(video_ids):
    request = youtube.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    )
    response = request.execute()
    return response.get('items', [])

# === Filter Real Shorts (<= 60 sec or has #shorts tag) ===
def filter_shorts(videos):
    def parse_duration(duration_str):
        import re
        match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0  # 若格式不符直接回傳0秒
        minutes = int(match.group(1)) if match.group(1) else 0
        seconds = int(match.group(2)) if match.group(2) else 0
        return minutes * 60 + seconds

    filtered = []
    for video in videos:
        try:
            title = video['snippet']['title'].lower()
            description = video['snippet']['description'].lower()
            duration = parse_duration(video['contentDetails']['duration'])
            # 只保留3分鐘(180秒)以內的影片
            if duration <= 180 and (duration <= 60 or '#shorts' in title or '#shorts' in description):
                filtered.append(video)
        except Exception as e:
            print(f"Skip video {video.get('id', '')} due to error: {e}")
            continue
    return filtered

# === Filter by Popularity (Views) ===
def filter_by_popularity(videos, min_views=200000):
    return [video for video in videos if int(video['statistics'].get('viewCount', 0)) >= min_views]

def windows_safe_title(title: str) -> str:
    s = title.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    s = s.replace("|", " - ")
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', ' ', s)  # 移除 Windows 非法字元
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.rstrip(' .')
    return s[:150] or "untitled"

def unique_file_title(download_folder: str, base_title: str, video_id: str) -> str:
    # 以 mp4 為目標輸出，避免重名
    path = os.path.join(download_folder, f"{base_title}.mp4")
    if not os.path.exists(path):
        return base_title
    alt = f"{base_title} ({video_id})"
    path2 = os.path.join(download_folder, f"{alt}.mp4")
    if not os.path.exists(path2):
        return alt
    i = 2
    while True:
        cand = f"{base_title} ({video_id}) ({i})"
        if not os.path.exists(os.path.join(download_folder, f"{cand}.mp4")):
            return cand
        i += 1

# (舊) clean_title_for_filename 可移除，或改為導向新函式
def clean_title_for_filename(video_title: str) -> str:
    return windows_safe_title(video_title)

# === Save to JSON File ===
def save_to_json(video_details, file_name, file_title_overrides=None):
    # 先讀取舊資料，若檔案損壞或為空則視為空資料
    if os.path.exists(file_name):
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except Exception:
            old_data = []
    else:
        old_data = []

    existing_ids = set(item['id'] for item in old_data if 'id' in item)
    file_title_overrides = file_title_overrides or {}

    new_data = []
    for video in video_details:
        video_id = video['id']
        if video_id in existing_ids:
            continue
        original_title = video['snippet']['title']
        # 下載檔名用的 title（與 JSON 的 title 完全一致）
        file_title = file_title_overrides.get(video_id, windows_safe_title(original_title))
        url = f"https://www.youtube.com/watch?v={video_id}"
        item = {
            'id': video_id,
            'title': file_title,            # 與檔名一致
            'original_title': original_title,  # 保留原始標題
            'url': url,
            'views': int(video['statistics'].get('viewCount', 0)),
            'likes': int(video['statistics'].get('likeCount', 0)),
            'comments': int(video['statistics'].get('commentCount', 0)),
            'description': video['snippet']['description']
        }
        new_data.append(item)

    all_data = old_data + new_data

    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
    print(f"Video details saved to {file_name}，本次新增 {len(new_data)} 筆。")

# === Download using yt-dlp ===
def download_with_ytdlp(video_url, download_folder, file_title=None):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    if file_title:
        output_template = f"{download_folder}/{file_title}.%(ext)s"
        file_path = os.path.join(download_folder, f"{file_title}.mp4")
    else:
        output_template = f"{download_folder}/%(title)s.%(ext)s"
        file_path = None

    if file_path and os.path.exists(file_path):
        print(f"Already downloaded, skip: {file_path}")
        return True

    format_try_list = [
        'bv+ba/best',
        'best',
        'bv[ext=mp4]+ba[ext=m4a]/best[ext=mp4]/best'
    ]
    for fmt in format_try_list:
        command = [
            'yt-dlp',
            '-f', fmt,
            '--merge-output-format', 'mp4',
            '-o', output_template,
            '--no-playlist',
            video_url
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully downloaded: {video_url} (format={fmt})")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
            if "DRM" in error_msg or 'SABR' in error_msg:
                print(f"DRM/SABR protected, skip: {video_url}")
                return False
            if "Sign in to confirm" in error_msg or "cookies" in error_msg:
                print(f"Skip (need login): {video_url}")
                return False
            continue
    print(f"Failed all format attempts: {video_url}")
    return False

def extend_with_queries(known_ids: set, base_list: list, min_views: int, needed: int) -> list:
    new_videos = []
    for q in base_list:
        if len(new_videos) >= needed:
            break
        try:
            videos = search_short_videos(q, MAX_RESULTS)
            video_ids = [v['id']['videoId'] for v in videos]
            details = get_video_details(video_ids)
            shorts = filter_shorts(details)
            popular = filter_by_popularity(shorts, min_views)
            for vid in popular:
                vid_id = vid['id']
                if vid_id in known_ids:
                    continue
                known_ids.add(vid_id)
                new_videos.append(vid)
                if len(new_videos) >= needed:
                    break
        except Exception as e:
            print(f"Extend query '{q}' error: {e}")
            continue
    return new_videos

def count_downloaded_videos(download_folder: str) -> int:
    if not os.path.isdir(download_folder):
        return 0
    try:
        return sum(1 for f in os.listdir(download_folder) if f.lower().endswith(".mp4"))
    except Exception:
        return 0

# === Main Process ===
def main():
    # 讀取已儲存的 JSON（支援續跑）
    existing_ids = set()
    if os.path.exists(JSON_OUTPUT_FILE):
        try:
            with open(JSON_OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    if 'id' in item:
                        existing_ids.add(item['id'])
        except Exception:
            pass

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    file_count = count_downloaded_videos(DOWNLOAD_FOLDER)
    print(f"Resume: {file_count} videos in folder; {len(existing_ids)} JSON records.")

    # 以資料夾內影片數計算還需要補幾部
    needed = max(0, TARGET_COUNT - file_count)
    if needed == 0:
        print("Target already reached based on files in folder. Nothing to download.")
        return

    # 建立「參考已下載」ID：只用於跳過重複，不作停止條件
    reference_ids = collect_reference_ids()
    known_ids = set(existing_ids) | set(reference_ids)

    collected = []

    # 初始搜尋迴圈
    for query in SEARCH_QUERIES:
        if len(collected) >= needed:
            break
        print(f"Searching YouTube Shorts for query: {query}...")
        videos = search_short_videos(query, MAX_RESULTS)
        video_ids = [v['id']['videoId'] for v in videos]
        details = get_video_details(video_ids)
        shorts = filter_shorts(details)
        popular = filter_by_popularity(shorts, MIN_VIEWS_PRIMARY)
        print(f"Query='{query}' -> {len(popular)} candidates (after filters)")
        for vid in popular:
            vid_id = vid['id']
            if vid_id in known_ids:
                continue
            collected.append(vid)
            known_ids.add(vid_id)
            if len(collected) >= needed:
                break

    # Fallback 降低觀看數
    if len(collected) < needed:
        remain = needed - len(collected)
        print(f"Need {remain} more -> fallback queries (min views {MIN_VIEWS_FALLBACK})")
        added = extend_with_queries(known_ids, FALLBACK_QUERIES, MIN_VIEWS_FALLBACK, remain)
        collected.extend(added)
        print(f"Fallback added {len(added)} videos. Collected now {len(collected)}/{needed}")

    # 最終不限觀看數
    if len(collected) < needed:
        remain = needed - len(collected)
        print(f"Still need {remain}. Broad search with no view threshold.")
        added = extend_with_queries(known_ids, FALLBACK_QUERIES, 0, remain)
        collected.extend(added)
        print(f"Broad added {len(added)}. Collected now {len(collected)}/{needed}")

    # 下載
    to_download = collected
    print(f"Downloading {len(to_download)} new videos (need {needed}).")

    for idx, video in enumerate(to_download, start=1):
        vid_id = video['id']
        vid_url = f"https://www.youtube.com/watch?v={vid_id}"
        original = video['snippet']['title']
        base_title = windows_safe_title(original)
        used_title = unique_file_title(DOWNLOAD_FOLDER, base_title, vid_id)
        print(f"[{idx}/{len(to_download)}] Downloading: {vid_url}")
        if download_with_ytdlp(vid_url, DOWNLOAD_FOLDER, used_title):
            save_to_json([video], JSON_OUTPUT_FILE, {vid_id: used_title})

    print(f"Done. Folder now has ~{count_downloaded_videos(DOWNLOAD_FOLDER)} videos (target {TARGET_COUNT}).")

if __name__ == '__main__':
    main()