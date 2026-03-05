import argparse, json, re, sys
from pathlib import Path
from difflib import SequenceMatcher
import sys
sys.stdout.reconfigure(encoding='utf-8')

ILLEGAL = '<>:"/\\|?*'

def strip_wrapping_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s

def windows_safe_base(title: str) -> str:
    t = strip_wrapping_quotes(title)
    t = t.replace("|", " - ")
    trans = {ord(c): " " for c in ILLEGAL if c != "|"}
    t = t.translate(trans)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.rstrip(" .")
    return t or "untitled"

def normalize_for_compare(s: str) -> str:
    s = strip_wrapping_quotes(s)
    s = s.lower()
    s = s.replace("|", " ")
    s = s.replace("_", " ")
    s = re.sub(r"\.[a-z0-9]+$", "", s)  # drop extension
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s)  # 保留英文與中日韓
    s = re.sub(r"\s+", " ", s).strip()
    return s

def load_titles(shorts_path: Path) -> list[str]:
    data = json.loads(shorts_path.read_text(encoding="utf-8"))
    titles = []
    for it in data:
        if isinstance(it, dict) and it.get("title"):
            titles.append(it["title"])
    return titles

def best_match(name_key: str, title_keys: list[str]) -> int:
    best_i, best_score = -1, -1.0
    for i, tk in enumerate(title_keys):
        score = SequenceMatcher(None, name_key, tk).ratio()
        if score > best_score:
            best_score, best_i = score, i
    return best_i, best_score

def unique_name(target_dir: Path, base: str, used: set[str]) -> str:
    name = f"{base}.json"
    if name.lower() not in used:
        return name
    # 加序號避免衝突
    n = 2
    while True:
        cand = f"{base} ({n}).json"
        if cand.lower() not in used:
            return cand
        n += 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shorts", default=r"d:\Users\81150\Desktop\新增資料夾\shorts_data2.json")
    ap.add_argument("--analysis", default=r"d:\Users\81150\Desktop\新增資料夾\outputs\analysis_json2")
    ap.add_argument("--threshold", type=float, default=0.99, help="最低相似度才進行更名（0~1）")
    ap.add_argument("--commit", action="store_true", help="實際更名（預設只顯示計畫）")
    args = ap.parse_args()

    shorts_path = Path(args.shorts)
    analysis_dir = Path(args.analysis)
    if not shorts_path.exists():
        print(f"找不到 shorts_data2.json: {shorts_path}", file=sys.stderr); sys.exit(1)
    if not analysis_dir.is_dir():
        print(f"找不到資料夾: {analysis_dir}", file=sys.stderr); sys.exit(1)

    titles = load_titles(shorts_path)
    if not titles:
        print("shorts_data2.json 沒讀到任何 title", file=sys.stderr); sys.exit(1)

    title_keys = [normalize_for_compare(t) for t in titles]
    used = set(p.name.lower() for p in analysis_dir.glob("*.json"))

    plan = []
    low_matches = []

    files = list(analysis_dir.glob("*.json"))
    for f in files:
        stem = f.stem
        key = normalize_for_compare(stem)
        idx, score = best_match(key, title_keys)
        if idx == -1:
            low_matches.append((f.name, None))
            continue
        title = titles[idx]
        base = windows_safe_base(title)
        new_name = f"{base}.json"
        # 衝突處理
        if new_name.lower() in used and f.name.lower() != new_name.lower():
            new_name = unique_name(analysis_dir, base, used)
        if score < args.threshold:
            low_matches.append((f.name, round(score, 4)))
            continue
        if f.name != new_name:
            plan.append((f, f.with_name(new_name)))
            used.add(new_name.lower())

    print(f"分析檔案數: {len(files)}")
    print(f"可更名數: {len(plan)}  (threshold={args.threshold})")
    if low_matches:
        print(f"低相似度/無匹配: {len(low_matches)}")
        for n, sc in low_matches:
            print(f"  - {n} (score={sc})")

    for src, dst in plan:
        print(f"{src.name} -> {dst.name}")

    if args.commit:
        for src, dst in plan:
            src.rename(dst)
        print("完成更名。")
    else:
        print("乾跑模式：未實際更名。加入 --commit 以套用。")

if __name__ == "__main__":
    main()