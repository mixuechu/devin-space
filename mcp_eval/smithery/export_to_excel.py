import json
import pandas as pd

# 读取 output.json
with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

rows = []
for item in data["data"]:
    row = {
        "title": item.get("title", ""),
        "id": item.get("id", ""),
        "url": item.get("url", ""),
        "tools": "; ".join([f"{t['name']}:{t['description']}" for t in item.get("tools", [])]),
        "monthly_tool_calls": item.get("monthly_tool_calls", ""),
        "published": item.get("published", ""),
        "additional_info": item.get("additional_info", ""),
        "config": json.dumps(item.get("config", {}), ensure_ascii=False)
    }
    rows.append(row)

# 转为DataFrame并导出Excel
if rows:
    df = pd.DataFrame(rows)
    df.to_excel("output.xlsx", index=False)
    print("已导出到output.xlsx")
else:
    print("没有可导出的数据。") 