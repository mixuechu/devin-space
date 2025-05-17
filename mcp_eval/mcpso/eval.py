import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from config import RAW_DATA_PATH, PROGRESS_PATH, RESULT_JSON_PATH, RESULT_XLSX_PATH, BATCH_SIZE, MAX_WORKERS
from utils import load_json, save_json, gpt_eval
import json

def parse_raw_json_if_needed(eval_result):
    if isinstance(eval_result, dict) and 'raw' in eval_result and isinstance(eval_result['raw'], str):
        raw = eval_result['raw']
        # 直接去除markdown代码块包裹
        for prefix in ['```json\n', '```json\r\n', '```json', '```']:
            if raw.strip().startswith(prefix):
                raw = raw.strip()[len(prefix):]
        for suffix in ['\n```', '\r\n```', '```']:
            if raw.strip().endswith(suffix):
                raw = raw.strip()[:-len(suffix)]
        try:
            parsed = eval_result.copy()
            parsed.pop('raw')
            parsed.update(json.loads(raw))
            return parsed
        except Exception:
            pass
    return eval_result

def main():
    # 加载原始数据
    all_data = load_json(RAW_DATA_PATH)
    if isinstance(all_data, dict):
        items = list(all_data.values())
    else:
        items = all_data
    # items = items[:BATCH_SIZE]

    # 断点续传
    if os.path.exists(PROGRESS_PATH):
        progress = load_json(PROGRESS_PATH)
    else:
        progress = {}

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for idx, item in enumerate(items):
            if str(idx) in progress:
                results.append(progress[str(idx)])
                continue
            future = executor.submit(gpt_eval, item)
            futures[future] = (idx, item)

        for future in tqdm(as_completed(futures), total=len(futures), desc="评测中"):
            idx, item = futures[future]
            try:
                eval_result = future.result()
                eval_result = parse_raw_json_if_needed(eval_result)
            except Exception as e:
                eval_result = {"error": str(e)}
            record = {
                "idx": idx,
                "origin": item,
                "eval": eval_result
            }
            results.append(record)
            progress[str(idx)] = record
            save_json(progress, PROGRESS_PATH)

    # 保存最终结果
    save_json(results, RESULT_JSON_PATH)

    # 导出Excel
    rows = []
    for r in results:
        row = {
            "名称": r["origin"].get("title", ""),
            "GitHub Url": r["origin"].get("github_url", ""),
            "Marketplace Url": r["origin"].get("page_url", ""),
            "价值分数": r["eval"].get("value", {}).get("score"),
            "可用性分数": r["eval"].get("usability", {}).get("score"),
            "易用性分数": r["eval"].get("ease_of_use", {}).get("score"),
            "可移植性分数": r["eval"].get("portability", {}).get("score"),
            "总分": r["eval"].get("total_score", None),
            "所需APIkey等": ", ".join(r["eval"].get("apikeys", [])),
            "易用性理由": r["eval"].get("ease_of_use", {}).get("reason"),
            "价值评分理由": r["eval"].get("value", {}).get("reason"),
            "可用性理由": r["eval"].get("usability", {}).get("reason"),
            "可移植性理由": r["eval"].get("portability", {}).get("reason"),
        }
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_excel(RESULT_XLSX_PATH, index=False)
    print(f"评测完成，结果已保存到 {RESULT_XLSX_PATH}")

if __name__ == "__main__":
    main() 