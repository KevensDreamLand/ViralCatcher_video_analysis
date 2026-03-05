import os
import json
import re
import argparse
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

def clean_title_for_filename(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', title)
    return safe.strip()[:150]


def legacy_clean_title(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', '_', title)
    return safe.strip()[:150]


def build_expected(json_path: str):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    expected = set()
    for item in data:
        title = item.get('title') or ''
        if not title:
            continue
        expected.add(clean_title_for_filename(title) + '.mp4')
        expected.add(legacy_clean_title(title) + '.mp4')
    return expected, data


def prune(folder: str, json_file: str, dry_run: bool, log: bool):
    expected, data = build_expected(json_file)
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Download folder not found: {folder}")

    mp4_files = [f for f in os.listdir(folder) if f.lower().endswith('.mp4')]
    orphan = [f for f in mp4_files if f not in expected]
    kept = len(mp4_files) - len(orphan)

    print(f"Total mp4: {len(mp4_files)} | In JSON: {kept} | Orphans: {len(orphan)}")
    if not orphan:
        print("No orphan files.")
        return

    log_entries = []
    for name in orphan:
        path = os.path.join(folder, name)
        if dry_run:
            print(f"[DRY] Would delete: {path}")
        else:
            try:
                os.remove(path)
                print(f"Deleted: {path}")
                log_entries.append(path)
            except Exception as e:
                print(f"Failed to delete {path}: {e}")

    if log and log_entries:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"prune_deleted_{ts}.txt"
        with open(log_file, 'w', encoding='utf-8') as lf:
            lf.write("\n".join(log_entries))
        print(f"Deletion log saved: {log_file}")


def parse_args():
    p = argparse.ArgumentParser(description="Prune videos not listed in JSON metadata.")
    p.add_argument('--folder', default='downloaded_shorts3', help='下載影片資料夾')
    p.add_argument('--json', default='shorts_data2.json', help='影片資訊 JSON 檔')
    p.add_argument('--dry-run', action='store_true', help='僅顯示將刪除的檔案，不實際刪除')
    p.add_argument('--no-log', action='store_true', help='不輸出刪除紀錄檔')
    return p.parse_args()


def main():
    args = parse_args()
    prune(
        folder=args.folder,
        json_file=args.json,
        dry_run=args.dry_run,
        log=not args.no_log
    )


if __name__ == '__main__':
    main()
