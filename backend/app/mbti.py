"""MBTI 自适应测试引擎：维度状态、出题路由、收敛判定、类型计算。

自适应逻辑（类似计算机化自适应测验 CAT 的简化版）：
1. 每轮选出「置信度最低」的维度出题（置信度 = 已收集证据的可靠程度）
2. 选项作答的 evidence 由出题时预设的 lean 直接给出（确定、可信）；
   自由文本作答由 LLM 语义评分
3. 四个维度置信度全部达标，或题数到达上限，即收敛出结果
"""

DIMENSIONS = ("EI", "SN", "TF", "JP")

DIMENSION_INFO = {
    "EI": {
        "pole1": "E", "pole2": "I",
        "name": "外向 E — 内向 I",
        "pole1_desc": "从人际互动中获取能量",
        "pole2_desc": "从独处思考中获取能量",
    },
    "SN": {
        "pole1": "S", "pole2": "N",
        "name": "实感 S — 直觉 N",
        "pole1_desc": "关注具体事实与当下经验",
        "pole2_desc": "关注可能性、概念与未来",
    },
    "TF": {
        "pole1": "T", "pole2": "F",
        "name": "思考 T — 情感 F",
        "pole1_desc": "依据逻辑与公平做决定",
        "pole2_desc": "依据感受与和谐做决定",
    },
    "JP": {
        "pole1": "J", "pole2": "P",
        "name": "判断 J — 知觉 P",
        "pole1_desc": "偏好计划、秩序与确定",
        "pole2_desc": "偏好灵活、即兴与开放",
    },
}

TYPE_NAMES = {
    "INTJ": "建筑师", "INTP": "逻辑学家", "ENTJ": "指挥官", "ENTP": "辩论家",
    "INFJ": "提倡者", "INFP": "调停者", "ENFJ": "主人公", "ENFP": "竞选者",
    "ISTJ": "物流师", "ISFJ": "守卫者", "ESTJ": "总经理", "ESFJ": "执政官",
    "ISTP": "鉴赏家", "ISFP": "探险家", "ESTP": "企业家", "ESFP": "表演者",
}

CONFIDENCE_TARGET = 5.0
MAX_QUESTIONS = 20
OPTION_CONFIDENCE_DELTA = 1.5
FREETEXT_CONFIDENCE_DELTA = 1.2
SCORE_MAX = 8.0  # 每维度最多4题×2分


def pick_next_dimension(states: dict[str, dict], last_dimension: str | None = None) -> str | None:
    """选出下一题要测的维度：置信度未达标的维度中，
    排除上一题刚测过的维度后，取置信度最低（并列时取得分越接近0越优先）。"""
    pending = [d for d in DIMENSIONS if states[d]["confidence"] < CONFIDENCE_TARGET]
    if not pending:
        return None
    candidates = [d for d in pending if d != last_dimension]
    if not candidates:
        candidates = pending
    return min(candidates, key=lambda d: (states[d]["confidence"], abs(states[d]["score"])))


def is_converged(states: dict[str, dict]) -> bool:
    return all(states[d]["confidence"] >= CONFIDENCE_TARGET for d in DIMENSIONS)


def compute_type(scores: dict[str, float]) -> str:
    letters = []
    for d in DIMENSIONS:
        info = DIMENSION_INFO[d]
        letters.append(info["pole1"] if scores[d] < 0 else info["pole2"])
    return "".join(letters)


def dimension_percent(score: float) -> int:
    """维度得分转 0-100 百分比（100 表示完全偏向第二字母，如 I/N/F/P）。"""
    percent = 50 + score * (50 / SCORE_MAX)
    return max(0, min(100, round(percent)))


def build_report_dimensions(scores: dict[str, float], descriptions: dict[str, str]) -> dict:
    result = {}
    for d in DIMENSIONS:
        info = DIMENSION_INFO[d]
        percent = dimension_percent(scores[d])
        pole = info["pole1"] if scores[d] < 0 else info["pole2"]
        result[d] = {
            "name": info["name"],
            "pole1": info["pole1"],
            "pole2": info["pole2"],
            "score": round(scores[d], 1),
            "percent": percent,          # pole2 方向的百分比
            "dominant_pole": pole,       # 本维度占优的字母
            "dominant_percent": 100 - percent if pole == info["pole1"] else percent,
            "description": descriptions.get(d, ""),
        }
    return result
