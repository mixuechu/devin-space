import json
import pandas as pd

# 读取 JSON 文件
with open('api_pricing_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 只保留主要字段
main_cols = ["信息名", "信息类型", "是否找到价格", "价格", "免费额度", "搜索来源", "状态"]
rows = []
seen = set()
for item in data:
    # 用信息名和类型做去重key
    key = (item.get("信息名", "").replace('_', ' ').lower().strip(), item.get("信息类型", "").lower().strip())
    if key in seen:
        continue
    seen.add(key)
    row = {col: item.get(col, "") for col in main_cols}
    rows.append(row)

# 转为 DataFrame
df = pd.DataFrame(rows)

# 输出为 Excel
df.to_excel("部分api key价格.xlsx", index=False)
print("已保存为 部分api key价格.xlsx") 