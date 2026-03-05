import argparse
import json
import os
import re
import sys
import glob
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YT_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')
ID_IN_PARENS_RE = re.compile(r'\(([A-Za-z0-9_-]{11})\)')  # 例如 檔名含有 (VIDEO_ID)
ID_IN_URL_RE = re.compile(r'(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})')

DEFAULT_FILES = ["shorts_data.json", "shorts_data2.json", "shorts_data3.json"]
TARGET_JSON_DEFAULT = "shorts_data3.json"
VIDEO_DIR_DEFAULT = "downloaded_shorts4"
ANALYSIS_DIR_DEFAULT = os.path.join("outputs", "analysis_json3")
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".m4v")

def _abs(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)

def load_items(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
            return [data]
    except Exception as e:
        print(f"[ERR] 讀取失敗：{path} -> {e}")
    return []

def extract_id(item: dict) -> str | None:
    v = item.get("id")
    if isinstance(v, str) and YT_ID_RE.fullmatch(v):
        return v
    if isinstance(v, dict):
        vid = v.get("videoId")
        if isinstance(vid, str) and YT_ID_RE.fullmatch(vid):
            return vid
    snip = item.get("snippet") or {}
    if isinstance(snip, dict):
        rid = snip.get("resourceId") or {}
        if isinstance(rid, dict):
            vid = rid.get("videoId")
            if isinstance(vid, str) and YT_ID_RE.fullmatch(vid):
                return vid
        title = snip.get("title")
        if isinstance(title, str):
            m = ID_IN_PARENS_RE.search(title) or ID_IN_URL_RE.search(title)
            if m:
                return m.group(1)
        desc = snip.get("description")
        if isinstance(desc, str):
            m = ID_IN_URL_RE.search(desc)
            if m:
                return m.group(1)
    for k in ("url", "webpage_url", "webpageUrl", "video_url"):
        u = item.get(k)
        if isinstance(u, str):
            m = ID_IN_URL_RE.search(u)
            if m:
                return m.group(1)
    for k in ("file_title", "filename", "name", "title"):
        t = item.get(k)
        if isinstance(t, str):
            m = ID_IN_PARENS_RE.search(t) or ID_IN_URL_RE.search(t)
            if m:
                return m.group(1)
    return None

def extract_title(item: dict) -> str:
    snip = item.get("snippet") or {}
    if isinstance(snip, dict):
        t = snip.get("title")
    else:
        t = None
    if not t:
        t = item.get("title") or item.get("file_title") or ""
    return str(t) if t is not None else ""

def analyze(files: list[str]):
    per_file_counts = {}
    per_file_ids = {}
    per_file_dupes = {}
    global_map = defaultdict(list)  # id -> [(file, title)]
    for f in files:
        path = _abs(f)
        items = load_items(path)
        per_file_counts[f] = len(items)
        id_seen = {}
        dup_in_file = defaultdict(list)
        for it in items:
            vid = extract_id(it)
            title = extract_title(it)
            if not vid:
                continue
            if vid in id_seen:
                dup_in_file[vid].append(title)
            else:
                id_seen[vid] = title
            global_map[vid].append((f, title))
        per_file_ids[f] = len(id_seen)
        per_file_dupes[f] = dup_in_file
    cross_dupes = {vid: lst for vid, lst in global_map.items() if len({f for f, _ in lst}) >= 2}
    return per_file_counts, per_file_ids, per_file_dupes, cross_dupes

def print_report(per_file_counts, per_file_ids, per_file_dupes, cross_dupes, top_n=30):
    print("=== 檔案統計 ===")
    for f in per_file_counts:
        print(f"- {f}: 條目 {per_file_counts[f]}，有效影片ID {per_file_ids[f]}，檔內重複 {len(per_file_dupes[f])}")
    print("\n=== 跨檔案重複（同影片出現在多個 JSON）===")
    print(f"總計 {len(cross_dupes)} 個影片 ID 重複")
    for i, (vid, occ) in enumerate(list(cross_dupes.items())[:top_n], start=1):
        files = ", ".join(sorted({f for f, _ in occ}))
        sample_title = next((t for _, t in occ if t), "")
        print(f"{i:>3}. {vid} | 於：{files} | 樣本標題：{sample_title}")
    print("\n=== 各檔內部重複（同一檔案中同影片出現多次）===")
    for f, dupmap in per_file_dupes.items():
        if not dupmap:
            continue
        print(f"- {f}: {len(dupmap)} 個重複影片 ID")
        for j, (vid, titles) in enumerate(list(dupmap.items())[:top_n], start=1):
            print(f"    {j:>3}. {vid} | 次數 {len(titles)+1}")

def collect_ids_from_files(files: list[str]) -> set[str]:
    ids = set()
    for f in files:
        for it in load_items(_abs(f)):
            vid = extract_id(it)
            if vid:
                ids.add(vid)
    return ids

def item_preferred_basename(item: dict) -> str | None:
    # 優先使用自有 file_title/filename/name/title（不含副檔名）
    for k in ("file_title", "filename", "name", "title"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            base = os.path.splitext(v)[0]
            return base
    # 退回 snippet.title
    snip = item.get("snippet") or {}
    if isinstance(snip, dict):
        t = snip.get("title")
        if isinstance(t, str) and t.strip():
            return os.path.splitext(t)[0]
    return None

def find_video_file(video_dir: str, vid: str, preferred_basename: str | None) -> str | None:
    vd = _abs(video_dir)
    # 1) 直接用 preferred_basename 匹配
    if preferred_basename:
        for ext in VIDEO_EXTS:
            p = os.path.join(vd, preferred_basename + ext)
            if os.path.isfile(p):
                return p
    # 2) 用 (VIDEO_ID) 搜尋
    pat = os.path.join(vd, f"*({vid})*")
    cands = []
    for ext in VIDEO_EXTS:
        cands.extend(glob.glob(pat + ext))
        # 某些檔案可能沒有括號，保守再比對含 id 的樣式
        cands.extend([p for p in glob.glob(os.path.join(vd, f"*{vid}*{ext}")) if os.path.isfile(p)])
    return cands[0] if cands else None

def analysis_json_path(analysis_dir: str, video_path_or_basename: str) -> str:
    ad = _abs(analysis_dir)
    base = os.path.basename(video_path_or_basename)
    base_no_ext = os.path.splitext(base)[0]
    return os.path.join(ad, base_no_ext + ".json")

def prune_target_json(earlier_files: list[str], target_json: str, video_dir: str, analysis_dir: str, do_delete: bool, show: int = 50):
    target_path = _abs(target_json)
    items = load_items(target_path)
    if not items:
        print(f"[INFO] 目標 JSON 無內容或讀取失敗：{target_path}")
        return

    earlier_ids = collect_ids_from_files(earlier_files)
    print(f"[INFO] 參考檔案總計 ID：{len(earlier_ids)}")

    to_keep = []
    to_remove = []  # (vid, title, preferred_base, video_path, analysis_path)
    seen_in_target = set()

    for it in items:
        vid = extract_id(it)
        title = extract_title(it)
        pref = item_preferred_basename(it)
        if not vid:
            to_keep.append(it)
            continue

        # 判定刪除條件：在參考檔（1/2）已存在，或在 3 自身重複（保留第一筆）
        if vid in earlier_ids or vid in seen_in_target:
            # 找對應檔案
            vpath = find_video_file(video_dir, vid, pref)
            apath = analysis_json_path(analysis_dir, vpath if vpath else (pref or f"({vid})"))
            to_remove.append((vid, title, pref, vpath, apath))
        else:
            seen_in_target.add(vid)
            to_keep.append(it)

    print(f"[INFO] 目標檔案：{target_json}")
    print(f"[INFO] 原始條目：{len(items)}")
    print(f"[INFO] 需刪除：{len(to_remove)}，保留：{len(to_keep)}")

    # 預覽
    for i, (vid, title, pref, vpath, apath) in enumerate(to_remove[:show], start=1):
        print(f"{i:>3}. {vid} | {title}")
        if vpath:
            print(f"     影片：{vpath}")
        else:
            print(f"     影片：<未找到>（嘗試以檔名 {pref or '('+vid+')'}）")
        print(f"     分析：{apath}")

    if not do_delete:
        print("\n[DRY-RUN] 未進行刪除或寫回 JSON。加入 --prune 後會：")
        print(" - 刪除 downloaded_shorts4 中對應影片（若找到）")
        print(" - 刪除 outputs/analysis_json3 中對應 JSON（若存在）")
        print(" - 回寫去重後的 shorts_data3.json（並建立 .bak 備份）")
        return

    # 刪除檔案
    removed_videos = 0
    removed_analyses = 0
    for _, _, _, vpath, apath in to_remove:
        if vpath and os.path.isfile(vpath):
            try:
                os.remove(vpath)
                removed_videos += 1
                print(f"[DEL] 影片：{vpath}")
            except Exception as e:
                print(f"[ERR] 刪除影片失敗：{vpath} -> {e}")
        if apath and os.path.isfile(apath):
            try:
                os.remove(apath)
                removed_analyses += 1
                print(f"[DEL] 分析：{apath}")
            except Exception as e:
                print(f"[ERR] 刪除分析失敗：{apath} -> {e}")

    # 備份並回寫 JSON
    bak_path = target_path + ".bak"
    try:
        if os.path.exists(target_path):
            with open(bak_path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(to_keep, f, ensure_ascii=False, indent=2)
        print(f"[DONE] 已寫回：{target_path}（備份：{bak_path}）")
    except Exception as e:
        print(f"[ERR] 寫回 JSON 失敗：{target_path} -> {e}")

    print(f"[DONE] 刪除影片 {removed_videos} 檔，刪除分析 {removed_analyses} 檔，JSON 移除 {len(to_remove)} 條。")

def main():
    parser = argparse.ArgumentParser(description="比對/清理 shorts_data*.json 重複影片")
    parser.add_argument("--files", nargs="*", default=DEFAULT_FILES, help="比對用的 JSON 清單（前兩個視為參考）")
    parser.add_argument("--top", type=int, default=30, help="報表輸出上限")
    parser.add_argument("--prune", action="store_true", help="實際刪除並回寫 shorts_data3.json")
    parser.add_argument("--target-json", default=TARGET_JSON_DEFAULT, help="要清理的 JSON（預設 shorts_data3.json）")
    parser.add_argument("--video-dir", default=VIDEO_DIR_DEFAULT, help="對應影片資料夾（預設 downloaded_shorts4）")
    parser.add_argument("--analysis-dir", default=ANALYSIS_DIR_DEFAULT, help="分析 JSON 資料夾（預設 outputs/analysis_json3）")
    parser.add_argument("--show", type=int, default=50, help="刪除清單預覽筆數")
    args = parser.parse_args()

    files = args.files
    per_file_counts, per_file_ids, per_file_dupes, cross_dupes = analyze(files)
    print_report(per_file_counts, per_file_ids, per_file_dupes, cross_dupes, top_n=args.top)

    # 清理 shorts_data3.json
    if len(files) >= 3:
        earlier = files[:2]
        prune_target_json(earlier_files=earlier,
                          target_json=args.target_json,
                          video_dir=args.video_dir,
                          analysis_dir=args.analysis_dir,
                          do_delete=args.prune,
                          show=args.show)
    else:
        print("[WARN] --files 至少需要 3 個（前兩個當作參考，第三個當作清理目標）")

if __name__ == "__main__":
    main()