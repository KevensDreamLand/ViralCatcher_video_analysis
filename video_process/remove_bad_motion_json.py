import argparse
import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEEDLE = "Error: [Errno 2] No such file or directory"

def bytes_to_str(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def scan_json(dirpath: str, needle: str):
    files = glob.glob(os.path.join(dirpath, "*.json"))
    hits = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                if needle in f.read():
                    hits.append(fp)
        except Exception as e:
            print(f"[WARN] 無法讀取：{fp} -> {e}")
    return files, hits

def main():
    parser = argparse.ArgumentParser(description="刪除含 motion_intensity 路徑遺失錯誤的 JSON")
    parser.add_argument("--dir", default=os.path.join("outputs", "analysis_json"), help="JSON 資料夾")
    parser.add_argument("--delete", action="store_true", help="實際刪除（未加則為乾跑）")
    parser.add_argument("--show", type=int, default=30, help="預覽顯示筆數")
    args = parser.parse_args()

    dir_arg = args.dir
    dirpath = dir_arg if os.path.isabs(dir_arg) else os.path.join(BASE_DIR, dir_arg)

    if not os.path.isdir(dirpath):
        print(f"[ERR] 目錄不存在：{dirpath}")
        return

    all_files, hits = scan_json(dirpath, NEEDLE)
    print(f"[INFO] 總檔案數：{len(all_files)}")
    print(f"[INFO] 符合刪除條件：{len(hits)}")

    for fp in hits[:args.show]:
        print("  -", fp)
    if len(hits) > args.show:
        print(f"  ... 其餘 {len(hits) - args.show} 檔省略")

    if not args.delete:
        print("\n[DRY-RUN] 未刪除任何檔案。若要刪除，請加入 --delete")
        return

    removed = 0
    freed = 0
    for fp in hits:
        try:
            size = os.path.getsize(fp)
            os.remove(fp)
            removed += 1
            freed += size
            print(f"[DEL] {fp}")
        except Exception as e:
            print(f"[ERR] 刪除失敗：{fp} -> {e}")

    print(f"[DONE] 已刪除 {removed} 檔，釋放 {bytes_to_str(freed)}")

if __name__ == "__main__":
    main()