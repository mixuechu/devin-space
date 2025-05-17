import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import re

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 调试时可先关闭无头模式
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_page(driver, url):
    result = {
        "tools": [],
        "additional_info": ""
    }
    try:
        driver.get(url)
    except Exception as e:
        print(f"加载页面失败: {url}，原因: {e}")
        return result  # 返回空结果，流程不中断
    
    # 获取tools信息
    try:
        tools = []
        # 先尝试点击"View more tools"展开全部
        try:
            view_more = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'View more tools')]"))
            )
            driver.execute_script("arguments[0].click();", view_more)
            time.sleep(1)
        except Exception as e:
            pass
        
        tool_elements = driver.find_elements(By.CSS_SELECTOR, "div.flex.flex-col.my-6 [class*='rounded-md']:not(.p-3)")
        for tool in tool_elements:
            try:
                name = tool.find_element(By.CSS_SELECTOR, "h3").text
                desc = tool.find_element(By.CSS_SELECTOR, "p.text-sm").text
                tools.append({"name": name, "description": desc})
            except Exception as e:
                continue
        result["tools"] = tools
        print(f"成功获取: {len(tools)} 个tools")
    except Exception as e:
        print(f"获取tools信息失败: {str(e)}")
    
    # 获取additional info内容
    try:
        add_info_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.border.rounded-lg.p-4"))
        )
        additional_info = add_info_elem.text
        result["additional_info"] = additional_info
        print(f"成功获取additional info，内容长度: {len(additional_info)}")
    except Exception as e:
        print(f"获取additional info失败: {e}")
    
    return result

def build_config(tool_id):
    return {
        "mcpServers": {
            "toolbox": {
                "command": "npx",
                "args": [
                    "-y",
                    "@smithery/cli@latest",
                    "run",
                    tool_id,
                    "--key",
                    "8f2e1d1c-c386-46e9-bef6-23d8347a8757",
                    "--profile",
                    "binding-bee-q5rL1h"
                ]
            }
        }
    }

def extract_info(additional_info):
    mtc_match = re.search(r"Monthly Tool Calls\s*([\d,]+)", additional_info, re.MULTILINE)
    monthly_tool_calls = mtc_match.group(1) if mtc_match else ""
    pub_match = re.search(r"Published\s*([\d]{1,2}/[\d]{1,2}/[\d]{4})", additional_info, re.MULTILINE)
    published = pub_match.group(1) if pub_match else ""
    return monthly_tool_calls, published

def main():
    # 加载你的JSON数据
    with open("smithery-ai-cards-page-106.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    driver = setup_driver()
    results = []
    
    try:
        for idx, item in enumerate(data["data"]):
            url = item["url"]
            print(f"\n处理项目 {idx+1}/{len(data['data'])}: {item['title']}")
            try:
                result = scrape_page(driver, url)
                if result:
                    item.update(result)
                    # 提取Monthly Tool Calls和Published
                    monthly_tool_calls, published = extract_info(result.get("additional_info", ""))
                    item["monthly_tool_calls"] = monthly_tool_calls
                    item["published"] = published
                    # 增加config字段
                    tool_id = item.get("id", "")
                    item["config"] = build_config(tool_id)
                    results.append(item)
                    print(f"成功获取: {len(result['tools'])}个tools")
            except Exception as e:
                print(f"处理 {url} 时发生异常: {e}")
                continue
            # 保存临时结果
            if (idx+1) % 5 == 0:
                with open("temp_output.json", "w", encoding="utf-8") as f:
                    json.dump({"data": results}, f, indent=2, ensure_ascii=False)
            # 提速，缩短sleep
            time.sleep(0.2)
            
    finally:
        driver.quit()
        # 保存最终结果
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump({"data": results}, f, indent=2, ensure_ascii=False)
        print("爬取完成，结果已保存到output.json")

if __name__ == "__main__":
    main()