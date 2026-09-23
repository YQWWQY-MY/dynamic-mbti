"""LLM 客户端：出题 / 自由回答评分 / 报告生成。

默认对接智谱 GLM（OpenAI 兼容协议，glm-4-flash 永久免费）。
通过 LLM_API_KEY 配置；未配置 key 时自动进入模拟模式（mock），
题目来自内置题库、评分为确定性规则、报告为模板文本，
保证离线开发与答辩断网演示可用。
"""

import hashlib
import json
import re

from openai import OpenAI

from .config import settings
from .mbti import DIMENSION_INFO, TYPE_NAMES


class LLMError(Exception):
    pass


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?|```", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("响应中未找到 JSON 对象")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"JSON 解析失败: {e}")


# ---------------- 模拟模式题库（每维度 4 题，lean 从 -2 到 2） ----------------

MOCK_QUESTIONS: dict[str, list[dict]] = {
    "EI": [
        {"question": "周五晚上你刚忙完一周的工作，朋友突然喊你出来聚会，你会？",
         "options": [{"text": "找个理由婉拒，在家安静待着", "lean": -2},
                     {"text": "看心情，多半不太想去", "lean": -1},
                     {"text": "犹豫一下还是去了", "lean": 1},
                     {"text": "立刻答应，正想找人玩", "lean": 2}]},
        {"question": "在一个几乎全是陌生人的聚会上，你通常会？",
         "options": [{"text": "找个角落待着刷手机", "lean": -2},
                     {"text": "只和带来的熟人说话", "lean": -1},
                     {"text": "和旁边的人聊上几句", "lean": 1},
                     {"text": "主动到处找人搭话", "lean": 2}]},
        {"question": "连续参加两天社交活动之后，你的状态是？",
         "options": [{"text": "感觉被掏空，急需独处回血", "lean": -2},
                     {"text": "有点累，想休息一下", "lean": -1},
                     {"text": "还行，睡一觉就恢复了", "lean": 1},
                     {"text": "意犹未尽，还想再约", "lean": 2}]},
        {"question": "团队讨论时，你更习惯哪种参与方式？",
         "options": [{"text": "先听大家说完，想法会后私下补", "lean": -2},
                     {"text": "记下想法，有把握再说", "lean": -1},
                     {"text": "被点名时能清晰表达", "lean": 1},
                     {"text": "边说边想，说着说着思路就来了", "lean": 2}]},
    ],
    "SN": [
        {"question": "朋友送你一台功能繁多的新咖啡机，你会？",
         "options": [{"text": "凭手感直接上手试", "lean": -2},
                     {"text": "大概扫一眼就开始用", "lean": -1},
                     {"text": "先翻一遍说明书", "lean": 1},
                     {"text": "逐字读完说明书并研究参数", "lean": 2}]},
        {"question": "你更喜欢的旅行方式是？",
         "options": [{"text": "说走就走，到了再看", "lean": -2},
                     {"text": "定个大方向随缘逛", "lean": -1},
                     {"text": "列个清单按兴趣走", "lean": 1},
                     {"text": "详细攻略精确到小时", "lean": 2}]},
        {"question": "学习一门新技能时，你更喜欢？",
         "options": [{"text": "直接上手，边试边学", "lean": -2},
                     {"text": "看个速成视频就开干", "lean": -1},
                     {"text": "找一套系统课程跟完", "lean": 1},
                     {"text": "从原理学起，先啃文档", "lean": 2}]},
        {"question": "别人夸你时，最常提到的特点是？",
         "options": [{"text": "脑洞大、点子多", "lean": -2},
                     {"text": "反应快、够灵活", "lean": -1},
                     {"text": "靠谱、务实", "lean": 1},
                     {"text": "细致、严谨", "lean": 2}]},
    ],
    "TF": [
        {"question": "同事的方案被否了，在群里诉苦，你的第一反应是？",
         "options": [{"text": "先安慰情绪，别的以后再说", "lean": -2},
                     {"text": "安慰两句，再顺着他的话说", "lean": -1},
                     {"text": "简单安慰后，给出想法", "lean": 1},
                     {"text": "直接分析方案哪里出了问题", "lean": 2}]},
        {"question": "两份工作：一份待遇好但你不喜欢，一份你喜欢但钱少，你怎么选？",
         "options": [{"text": "选喜欢的，钱不是最重要的", "lean": -2},
                     {"text": "看团队氛围和感受", "lean": -1},
                     {"text": "列出利弊清单来权衡", "lean": 1},
                     {"text": "算清楚收入差，理性决定", "lean": 2}]},
        {"question": "朋友让你评价他写的东西，但其实写得一般，你会？",
         "options": [{"text": "先夸亮点，别的不好说", "lean": -2},
                     {"text": "挑好的先说，再委婉提一句", "lean": -1},
                     {"text": "拐着弯给些建议", "lean": 1},
                     {"text": "直接指出问题在哪", "lean": 2}]},
        {"question": "刷到一个你不认同的观点，你通常会？",
         "options": [{"text": "划过去，没必要争", "lean": -2},
                     {"text": "看心情要不要回一句", "lean": -1},
                     {"text": "想想对方是不是也有道理", "lean": 1},
                     {"text": "把逻辑漏洞摆出来辩一辩", "lean": 2}]},
    ],
    "JP": [
        {"question": "出发旅行前一晚，你的行李箱是什么状态？",
         "options": [{"text": "明早现抓几件塞进去就行", "lean": -2},
                     {"text": "睡前随手装个大概", "lean": -1},
                     {"text": "列好清单逐项放进去", "lean": 1},
                     {"text": "按天搭配装袋，还留了备用", "lean": 2}]},
        {"question": "你的电脑桌面和文件夹是什么样的？",
         "options": [{"text": "满屏文件，靠搜索找", "lean": -2},
                     {"text": "大概分几个区域放", "lean": -1},
                     {"text": "分类清晰，命名规范", "lean": 1},
                     {"text": "严格的命名规则加定期归档", "lean": 2}]},
        {"question": "一个项目还有两周截止，你的推进方式是？",
         "options": [{"text": "等灵感来了集中冲", "lean": -2},
                     {"text": "想到哪做到哪", "lean": -1},
                     {"text": "排好大致节点按部就班", "lean": 1},
                     {"text": "每天的任务精确到小时", "lean": 2}]},
        {"question": "朋友临时改约，打乱了你原定的计划，你会？",
         "options": [{"text": "无所谓，随机应变", "lean": -2},
                     {"text": "有点不爽但能调整", "lean": -1},
                     {"text": "得重新把计划捋一遍", "lean": 1},
                     {"text": "很难受，计划就是计划", "lean": 2}]},
    ],
}

MOCK_POLE_TRAITS = {
    "E": "你的能量来自人群，在社交中感到充电",
    "I": "你的能量来自独处，安静中恢复状态",
    "S": "你关注具体现实，相信经验与眼前的事实",
    "N": "你关注可能性与想象力，喜欢琢磨概念和未来",
    "T": "你做决定时优先看逻辑与公平",
    "F": "你做决定时优先看感受与人际和谐",
    "J": "你喜欢计划与秩序，事情确定下来才安心",
    "P": "你喜欢灵活与即兴，保留选项才自在",
}


class LLMClient:
    def __init__(self):
        self.mock = not settings.llm_api_key
        if not self.mock:
            self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    # ---------- 基础对话 ----------

    def _chat(self, system: str, user: str, max_tokens: int = 1024, temperature: float = 0.8) -> str:
        resp = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def _chat_json(
        self, system: str, user: str, retries: int = 2, max_tokens: int = 1024, temperature: float = 0.8
    ) -> dict:
        last_err: Exception | None = None
        for _ in range(retries):
            try:
                return _extract_json(self._chat(system, user, max_tokens, temperature))
            except LLMError as e:
                last_err = e
        raise LLMError(f"多次重试后仍无法获得合法 JSON: {last_err}")

    # ---------- 1. 生成题目 ----------

    def generate_question(self, dimension: str, asked_questions: list[str]) -> dict:
        """出题。asked_questions 为该维度已出过的题干列表（用于避免重复）。
        返回 {"question": str, "options": [{"text": str, "lean": -2..2} x4]}"""
        if self.mock:
            pool = MOCK_QUESTIONS[dimension]
            return pool[len(asked_questions) % len(pool)]

        info = DIMENSION_INFO[dimension]
        avoid = "\n".join(f"- {q}" for q in asked_questions[-20:]) or "（暂无）"
        system = (
            "你是一位专业的MBTI人格测验出题专家。请针对指定性格维度出一道情境选择题。\n"
            "要求：\n"
            "1. 题目是具体、贴近大学生或年轻人日常生活的情境，一道题只测一个维度，题干30字以内\n"
            "2. 四个选项真实自然，代表该维度从一端到另一端的不同程度倾向，每个选项18字以内\n"
            "3. 题目和选项中不得出现任何字母缩写或人格术语\n"
            '4. 四个选项的 lean 值分别约为 -2、-1、1、2，选项顺序要打乱，不要固定规律\n'
            '5. 只输出JSON，不要多余文字，格式：\n'
            '{"question": "题干", "options": [{"text": "选项内容", "lean": -2}, {"text": "...", "lean": -1}, '
            '{"text": "...", "lean": 1}, {"text": "...", "lean": 2}]}'
        )
        user = (
            f"测试维度：{info['name']}（{info['pole1_desc']} ↔ {info['pole2_desc']}）\n"
            f"避免与以下已出题目相似：\n{avoid}"
        )
        data = self._chat_json(system, user, max_tokens=280)
        opts = data.get("options")
        if not isinstance(data.get("question"), str) or not isinstance(opts, list) or len(opts) != 4:
            raise LLMError("题目格式不合法")
        options = []
        for opt in opts:
            text = str(opt.get("text", "")).strip()
            if not text:
                raise LLMError("选项内容为空")
            try:
                lean = max(-2, min(2, int(opt.get("lean", 0))))
            except (TypeError, ValueError):
                raise LLMError("选项 lean 值不合法")
            options.append({"text": text, "lean": lean})
        return {"question": data["question"].strip(), "options": options}

    # ---------- 2. 自由文本回答评分 ----------

    def score_free_text(self, dimension: str, question: str, answer: str) -> dict:
        """返回 {"evidence": -2..2, "reasoning": str}"""
        if self.mock:
            evidence = int(hashlib.md5(answer.encode()).hexdigest(), 16) % 5 - 2
            return {"evidence": evidence, "reasoning": "（模拟评分）"}

        info = DIMENSION_INFO[dimension]
        system = (
            "你是MBTI测验评分专家。用户没有选择预设选项，而是自由输入了回答。"
            "请根据题干和用户的回答，判断用户在该维度上的倾向。\n"
            f"evidence 为负表示偏向「{info['pole1']} {info['pole1_desc']}」，"
            f"为正表示偏向「{info['pole2']} {info['pole2_desc']}」，0 表示无法判断。\n"
            '只输出JSON：{"evidence": -2到2的整数, "reasoning": "20字以内的判断依据"}'
        )
        user = f"测试维度：{info['name']}\n题干：{question}\n用户回答：{answer}"
        data = self._chat_json(system, user, max_tokens=120, temperature=0.2)
        try:
            evidence = max(-2, min(2, int(data.get("evidence", 0))))
        except (TypeError, ValueError):
            raise LLMError("evidence 值不合法")
        return {"evidence": evidence, "reasoning": str(data.get("reasoning", ""))}

    # ---------- 3. 生成报告 ----------

    def generate_report(self, mbti_type: str, scores: dict[str, float]) -> dict:
        """返回报告 JSON（不含维度分数，分数由引擎计算）"""
        if self.mock:
            traits = [MOCK_POLE_TRAITS[c] for c in mbti_type]
            return {
                "type_name": TYPE_NAMES.get(mbti_type, "未知类型"),
                "portrait": f"你是{TYPE_NAMES.get(mbti_type, mbti_type)}型人格。" + "；".join(traits) + "。（模拟模式生成的模板报告，配置 LLM_API_KEY 后可体验完整版）",
                "strengths": ["思维活跃", "适应力强", "有好奇心"],
                "weaknesses": ["容易分心", "计划性待加强"],
                "careers": ["产品经理", "数据分析师", "心理咨询师", "教师"],
                "famous": ["（配置真实 API Key 后显示）"],
                "advice": "这是模拟模式的占位建议。配置 LLM_API_KEY 后，AI 将根据你的四维度得分给出个性化成长建议。",
                "dimensions": {d: f"（模拟）{DIMENSION_INFO[d]['name']}" for d in scores},
            }

        score_desc = "、".join(
            f"{d}={scores[d]:.1f}（{DIMENSION_INFO[d]['pole1']}↔{DIMENSION_INFO[d]['pole2']}，"
            f"负值偏向{DIMENSION_INFO[d]['pole1']}）"
            for d in scores
        )
        system = (
            "你是资深的MBTI人格分析师，文风温暖、专业、具体，避免空洞套话，内容基于用户四维度得分展开。\n"
            "只输出JSON，格式：\n"
            "{\n"
            '  "type_name": "该类型的中文昵称",\n'
            '  "portrait": "150字左右的人格画像",\n'
            '  "strengths": ["3条核心优势，每条15字左右"],\n'
            '  "weaknesses": ["3条潜在短板，每条15字左右"],\n'
            '  "careers": ["4个适合的职业方向"],\n'
            '  "famous": ["2-3位该类型的真实名人"],\n'
            '  "advice": "80字左右的成长建议",\n'
            '  "dimensions": {"EI": "30字内结合得分描述", "SN": "...", "TF": "...", "JP": "..."}\n'
            "}"
        )
        user = f"用户的MBTI类型是 {mbti_type}。四维度得分（范围约-8到8）：{score_desc}"
        data = self._chat_json(system, user, max_tokens=1200, temperature=0.5)

        def _str_list(key: str, default: list[str]) -> list[str]:
            val = data.get(key, default)
            if isinstance(val, list):
                return [str(x) for x in val if str(x).strip()]
            return default

        dims = data.get("dimensions") if isinstance(data.get("dimensions"), dict) else {}
        return {
            "type_name": str(data.get("type_name") or TYPE_NAMES.get(mbti_type, mbti_type)),
            "portrait": str(data.get("portrait") or "").strip(),
            "strengths": _str_list("strengths", []),
            "weaknesses": _str_list("weaknesses", []),
            "careers": _str_list("careers", []),
            "famous": _str_list("famous", []),
            "advice": str(data.get("advice") or "").strip(),
            "dimensions": {d: str(dims.get(d, "")) for d in scores},
        }


llm_client = LLMClient()
