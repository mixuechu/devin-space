import json
from crawler_by_pages import setup_driver, scrape_page, extract_info, build_config

def main():
    # 1. 读取 output.json
    with open("output.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    failed_items = []
    for item in data["data"]:
        if not item.get("tools") and not item.get("additional_info"):
            failed_items.append(item)

    print(f"共发现 {len(failed_items)} 个疑似失败项，准备重试...")

    if not failed_items:
        print("没有需要补漏的项。")
        return

    driver = setup_driver()
    try:
        for idx, item in enumerate(failed_items, 1):
            url = item["url"]
            print(f"重试 {idx}/{len(failed_items)}: {url}")
            try:
                result = scrape_page(driver, url)
                if result:
                    item.update(result)
                    monthly_tool_calls, published = extract_info(result.get("additional_info", ""))
                    item["monthly_tool_calls"] = monthly_tool_calls
                    item["published"] = published
                    tool_id = item.get("id", "")
                    item["config"] = build_config(tool_id)
                    print(f"  -> 成功获取: {len(result['tools'])}个tools, info长度: {len(result['additional_info'])}")
                else:
                    print("  -> 依然失败")
            except Exception as e:
                print(f"  -> 重试时异常: {e}")
            # 可适当sleep防止过快
            import time
            time.sleep(0.2)
    finally:
        driver.quit()

    # 3. 写回 output.json
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("补漏完成，output.json已更新。")

if __name__ == "__main__":
    main() 