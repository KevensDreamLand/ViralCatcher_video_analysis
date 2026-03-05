import argparse
import os
import glob
import sys

sys.stdout.reconfigure(encoding='utf-8')

VIDEO_EXT = ".mp4"

def bytes_to_str(n: int) -> str:
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def list_videos(video_dir: str):
    return sorted(glob.glob(os.path.join(video_dir, f"*{VIDEO_EXT}")))

def list_analysis_json(analysis_dir: str):
    return sorted(glob.glob(os.path.join(analysis_dir, "*.json")))

def main():
    parser = argparse.ArgumentParser(description="比對 analysis_json3 與 downloaded_shorts4，刪除多餘檔案")
    parser.add_argument("--video-dir", default="downloaded_shorts4", help="影片資料夾")
    parser.add_argument("--analysis-dir", default=os.path.join("outputs", "analysis_json3"), help="分析 JSON 資料夾")
    parser.add_argument("--show", type=int, default=30, help="預覽顯示筆數")
    parser.add_argument("--delete", action="store_true", help="實際刪除（未加則為乾跑）")
    args = parser.parse_args()

    vd, ad = args.video_dir, args.analysis_dir
    if not os.path.isdir(vd):
        print(f"[ERR] 影片資料夾不存在：{vd}")
        return
    if not os.path.isdir(ad):
        print(f"[ERR] 分析資料夾不存在：{ad}")
        return

    videos = list_videos(vd)
    analyses = list_analysis_json(ad)

    video_bases = {os.path.splitext(os.path.basename(p))[0] for p in videos}
    analysis_bases = {os.path.splitext(os.path.basename(p))[0] for p in analyses}

    # 影片多餘：有 mp4 沒有對應 json
    orphan_videos = [p for p in videos if os.path.splitext(os.path.basename(p))[0] not in analysis_bases]
    # 分析多餘：有 json 沒有對應 mp4
    orphan_jsons = [p for p in analyses if os.path.splitext(os.path.basename(p))[0] not in video_bases]

    print(f"[INFO] 影片數：{len(videos)}，分析 JSON 數：{len(analyses)}")
    print(f"[INFO] 影片多餘（將刪除）：{len(orphan_videos)}")
    print(f"[INFO] 分析多餘（將刪除）：{len(orphan_jsons)}")

    if orphan_videos:
        print("\n[PREVIEW] 影片多餘（前幾筆）：")
        for p in orphan_videos[:args.show]:
            print("  -", p)
        if len(orphan_videos) > args.show:
            print(f"  ... 其餘 {len(orphan_videos) - args.show} 檔省略")

    if orphan_jsons:
        print("\n[PREVIEW] 分析多餘（前幾筆）：")
        for p in orphan_jsons[:args.show]:
            print("  -", p)
        if len(orphan_jsons) > args.show:
            print(f"  ... 其餘 {len(orphan_jsons) - args.show} 檔省略")

    if not args.delete:
        print("\n[DRY-RUN] 未刪除任何檔案。若要刪除，請加入 --delete")
        return

    removed = 0
    freed = 0

    def safe_remove(path: str):
        nonlocal removed, freed
        try:
            if os.path.exists(path):
                sz = os.path.getsize(path)
                os.remove(path)
                removed += 1
                freed += sz
                print(f"[DEL] {path}")
        except Exception as e:
            print(f"[ERR] 刪除失敗：{path} -> {e}")

    for p in orphan_videos:
        safe_remove(p)
    for p in orphan_jsons:
        safe_remove(p)

    print(f"\n[DONE] 已刪除 {removed} 檔，釋放 {bytes_to_str(freed)}")

if __name__ == "__main__":
    main()