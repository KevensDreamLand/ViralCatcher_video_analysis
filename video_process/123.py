import os
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
folder = r'D:\Users\81150\Desktop\新增資料夾\downloaded_shorts4'
json_file = r'D:\Users\81150\Desktop\新增資料夾\shorts_data3.json'

# 取得資料夾所有 mp4 檔名（不含副檔名）
files = [f for f in os.listdir(folder) if f.lower().endswith('.mp4')]
filenames = set(os.path.splitext(f)[0] for f in files)

# 取得 JSON 所有 title
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
json_titles = set(item.get('title', '') for item in data if 'title' in item)

# 找出資料夾有但 JSON 沒有的檔名
diff = filenames - json_titles

print("資料夾有但 JSON 沒有的影片：")
for name in diff:
    print(name)