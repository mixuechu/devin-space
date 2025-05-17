import pandas as pd

# 读取Excel文件
df = pd.read_excel('result.xlsx')  # 替换为你的文件名

# 提取"所需APIkey等"列，处理多值情况
api_key_types = (
    df['所需APIkey等']
    .dropna()  # 移除空值
    .str.split(',')  # 按逗号分割
    .explode()  # 展开所有分割后的值
    .str.strip()  # 去除每个值两端的空格
    .unique()  # 去重
    .tolist()  # 转换为列表
)
api_key_types = [s.lower() for s in api_key_types]
print("去重后的API key类型列表:")
print(api_key_types)
print(f"\n共计 {len(api_key_types)} 种不同的API key类型")