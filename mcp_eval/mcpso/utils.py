import json
import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt
from config import OPENAI_API_KEY, MODEL_NAME

openai.api_key = OPENAI_API_KEY

def build_eval_prompt(item):
    return (
        "你是一个MCP Server评测专家，请根据以下四个维度对给定的MCP Server信息进行1-5分打分，并给出简要理由：\n"
        "1. 价值（商业价值）：不仅仅是有用，还要考虑：\n"
        "  - 是否有明确的市场需求和用户群体？\n"
        "  - 用户是否有为此付费的意愿？\n"
        "  - 功能是否有独特性/创新性，还是同质化严重？\n"
        "  - 是否具备可规模化、可持续的商业模式？\n"
        "  - 是否有一定的行业壁垒或技术门槛？\n"
        "  - 是否能为企业/开发者带来实际收益或降本增效？\n"
        "  - 仅仅是开源/免费/有用但无商业模式的，不能给高分。\n"
        "2. 可用性：content中是否有mcp server用来使用的配置信息，比如这种带command和env的json结构\n"
        "3. 易用性：content中是否包含了明确的apikey和配置信息，比如如果明确说明不需要apikey，给满分，如果明确说明了使用哪些apikey，给高分，如果你判断肯定要用apikey，但content中没有提及，给低分\n"
        "4. 可移植性：如果command是npx这种不需要本地部署，可以直接远程连接的，给满分，如果明确说明本地部署流程，并且你认为部署流程清晰，部署比较简单的，给高分，如果你认为部署非常复杂，或者不是远程连接，是本地部署，但部署指令不明，部署很困难，或者没有部署指令，给低分\n\n"
        "请用如下JSON格式输出：\n"
        "{\n"
        "  \"value\": {\"score\": 1-5, \"reason\": \"xxx\"},\n"
        "  \"usability\": {\"score\": 1-5, \"reason\": \"xxx\"},\n"
        "  \"ease_of_use\": {\"score\": 1-5, \"reason\": \"xxx\"},\n"
        "  \"portability\": {\"score\": 1-5, \"reason\": \"xxx\"},\n"
        "  \"apikeys\": [\"xxx\", \"yyy\"],\n"
        "  \"total_score\": 0-5\n"
        "}\n\n"
        "其中total_score为加权总分，权重为：价值40%、可用性20%、易用性20%、可移植性20%，请严格按照上述商业价值标准打分。\n"
        f"MCP Server信息如下：\n{json.dumps(item, ensure_ascii=False, indent=2)}"
    )

@retry(wait=wait_random_exponential(min=2, max=10), stop=stop_after_attempt(5))
def gpt_eval(item):
    prompt = build_eval_prompt(item)
    response = openai.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=16384
    )
    content = response.choices[0].message.content
    try:
        result = json.loads(content)
    except Exception:
        result = {"raw": content}
    return result

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2) 