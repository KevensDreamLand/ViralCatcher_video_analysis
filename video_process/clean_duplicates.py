import argparse
import glob
import hashlib
import os
from typing import List, Set, Dict
import sys
sys.stdout.reconfigure(encoding='utf-8')

VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".m4v")

def list_videos(folder: str) -> List[str]:
    files = []
    for ext in VIDEO_EXTS:
        files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    return sorted(files)

def file_signature(path: str, chunk_size: int = 512 * 1024) -> str | None:
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
        return f"{size}:{h.hexdigest()}"
    except Exception as e:
        print(f"[WARN] 無法建立簽名: {path}，錯誤：{e}")
        return None

def build_reference_signatures(folders: List[str]) -> Set[str]:
    sigs: Set[str] = set()
    total_files = 0
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        for p in list_videos(folder):
            sig = file_signature(p)
            if sig:
                sigs.add(sig)
                total_files += 1
    print(f"[INFO] 參考資料夾簽名建立完成：{len(sigs)} / 檔案數 {total_files}")
    return sigs

def bytes_to_str(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def dedupe_target(target_folder: str, reference_sigs: Set[str], delete: bool = False):
    files = list_videos(target_folder)
    if not files:
        print(f"[INFO] {target_folder} 沒有找到影片")
        return

    seen_in_target: Dict[str, str] = {}  # sig -> kept path
    dup_external: List[str] = []         # 與參考資料夾重複
    dup_internal: List[tuple[str, str]] = []  # (keep, remove)

    for p in files:
        sig = file_signature(p)
        if not sig:
            continue

        if sig in reference_sigs:
            dup_external.append(p)
            continue

        if sig in seen_in_target:
            keep = seen_in_target[sig]
            dup_internal.append((keep, p))
        else:
            seen_in_target[sig] = p

    # Summary
    total_bytes_ext = sum((os.path.getsize(p) for p in dup_external if os.path.exists(p)), start=0)
    total_bytes_int = sum((os.path.getsize(p) for _, p in dup_internal if os.path.exists(p)), start=0)
    print(f"[INFO] 檢測完成：")
    print(f"       與參考資料夾重複：{len(dup_external)} 檔，約 {bytes_to_str(total_bytes_ext)}")
    print(f"       目標資料夾內部重複（將刪除重複者，保留一份）：{len(dup_internal)} 檔，約 {bytes_to_str(total_bytes_int)}")

    if not delete:
        # 乾跑模式
        if dup_external:
            print("\n[DRY-RUN] 將刪除（與參考重複）：")
            for p in dup_external[:30]:
                print("  -", p)
            if len(dup_external) > 30:
                print(f"  ... 其餘 {len(dup_external) - 30} 檔省略")

        if dup_internal:
            print("\n[DRY-RUN] 將刪除（內部重複，保留另一份）：")
            for keep, rm in dup_internal[:30]:
                print("  - 刪除:", rm)
                print("    保留:", keep)
            if len(dup_internal) > 30:
                print(f"  ... 其餘 {len(dup_internal) - 30} 檔省略")

        print("\n[DRY-RUN] 未實際刪除。若要執行刪除，請加入 --delete")
        return

    # 實際刪除
    removed = 0
    def safe_remove(path: str):
        nonlocal removed
        try:
            os.remove(path)
            removed += 1
            print(f"[DEL] {path}")
        except Exception as e:
            print(f"[ERR] 刪除失敗：{path}，錯誤：{e}")

    for p in dup_external:
        if os.path.exists(p):
            safe_remove(p)

    for _, p in dup_internal:
        if os.path.exists(p):
            safe_remove(p)

    print(f"[DONE] 已刪除 {removed} 個重複檔案。")

def main():
    parser = argparse.ArgumentParser(description="刪除 downloaded_shorts4 的重複影片")
    parser.add_argument("--target", default="downloaded_shorts4", help="要清理的資料夾")
    parser.add_argument("--refs", nargs="*", default=["downloaded_shorts2", "downloaded_shorts3"], help="參考資料夾（與其重複則刪除）")
    parser.add_argument("--delete", action="store_true", help="實際刪除檔案（未加此參數則為乾跑）")
    args = parser.parse_args()

    target = args.target
    refs = [p for p in args.refs if os.path.isdir(p)]

    if not os.path.isdir(target):
        print(f"[ERR] 目標資料夾不存在：{target}")
        return

    print(f"[INFO] 目標：{target}")
    print(f"[INFO] 參考：{refs if refs else '(無)'}")

    reference_sigs = build_reference_signatures(refs) if refs else set()
    dedupe_target(target, reference_sigs, delete=args.delete)

if __name__ == "__main__":
    main()