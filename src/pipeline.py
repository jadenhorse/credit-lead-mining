# Credit Lead Mining - Core Pipeline
"""
金融信贷线索挖掘引擎 - 核心处理管线

从非结构化新闻/公告中提取企业融资、风险、中标信号，
自动评分并生成客户经理跟进建议。

Author: Ma Zhibin (马志斌)
Background: Applied Statistics MS, Financial Risk Control Data PM
"""

import re
from datetime import datetime
from typing import Optional

# ============================================================
# 1. 企业名称识别引擎
# ============================================================

FORMAL_COMPANY_SUFFIXES = [
    "股份有限公司",
    "集团有限公司",
    "有限责任公司",
    "有限公司",
]

GENERIC_SUFFIXES = ["集团", "企业", "厂", "中心", "工作室"]

COMPANY_PATTERN = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9（）()·]{2,40}"
    r"(?:股份有限公司|集团有限公司|有限责任公司|有限公司|集团|企业|厂|中心|工作室))"
)

FUNDING_KEYWORDS = ["融资", "Pre-A", "A轮", "B轮", "C轮", "天使轮", "战略投资", "领投", "投融资"]
RISK_KEYWORDS = ["经营异常", "行政处罚", "失信", "诉讼", "被执行人", "风险", "异常名录"]
AWARD_KEYWORDS = ["中标", "入选", "公示", "认定", "补贴", "专项资金", "拟支持"]

MACRO_NOISE_KEYWORDS = [
    "营商环境", "工作要点", "北京市人民政府", "人民政府办公厅",
    "公示公告", "政策", "通知", "工作站", "征求意见稿", "证券时报", "人民财讯",
]

INVALID_COMPANY_NAMES = {
    "日期", "提高企业", "持续用好小微企业", "累计服务企业",
    "走访小微企业", "一个企业", "通过际华集团", "融资信息查询",
    "公示公告", "未知企业",
}

INVALID_COMPANY_FRAGMENTS = ["表示", "排斥", "投资", "理解", "考虑", "工作", "支持"]
GENERIC_COMPANY_PREFIXES = ["2026年", "2025年", "2024年", "年度", "累计", "通过", "一个", "走访"]
GENERIC_COMPANY_CONTAINS = ["小微企业", "科技型中小企业", "个体工商户", "高新技术企业认定"]


def is_plausible_company_name(name: str) -> bool:
    """判断提取的名称是否为合理的企业名称"""
    if not name or name in INVALID_COMPANY_NAMES:
        return False
    stripped = name.strip()
    if len(stripped) <= 2:
        return False
    if any(fragment in stripped for fragment in INVALID_COMPANY_FRAGMENTS):
        return False
    if any(stripped.startswith(prefix) for prefix in GENERIC_COMPANY_PREFIXES):
        return False
    if any(fragment in stripped for fragment in GENERIC_COMPANY_CONTAINS):
        return False
    if any(stripped.endswith(suffix) for suffix in FORMAL_COMPANY_SUFFIXES):
        return True
    if any(stripped.endswith(suffix) for suffix in GENERIC_SUFFIXES) and len(stripped) >= 3:
        return True
    return False


def extract_company_name(text: str) -> str:
    """从非结构化文本中提取企业全称"""
    if not text:
        return "未知企业"
    candidates = COMPANY_PATTERN.findall(text)
    plausible = [c for c in candidates if is_plausible_company_name(c)]
    if plausible:
        return plausible[-1]
    first_segment = re.split(r"[，。,；;：:\s]", text.strip())[0]
    cleaned = first_segment[:30] if first_segment else "未知企业"
    return cleaned if is_plausible_company_name(cleaned) else "未知企业"


# ============================================================
# 2. 事件分类器
# ============================================================

def classify_event_type(item: dict) -> str:
    """基于关键词权重的事件三分类：融资/中标资质/风险"""
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    if any(kw in text for kw in FUNDING_KEYWORDS):
        return "融资"
    if any(kw in text for kw in RISK_KEYWORDS):
        return "风险"
    if any(kw in text for kw in AWARD_KEYWORDS):
        return "中标/资质"
    return "其他"


# ============================================================
# 3. 线索评分模型
# ============================================================

def score_lead(item: dict) -> int:
    """
    线索商业价值评分 (0-100)
    
    评分逻辑基于金融风控专家经验：
    - 融资事件：资金需求强，商业价值最高 (+30)
    - 中标/资质：经营稳定，回款/保函需求 (+20)
    - 风险信号：预警场景，审慎触达 (+5)
    - 亿元级金额：大额信号提升优先级 (+10)
    - 风险来源：非正面来源适度降权 (-5)
    """
    event_type = item.get("event_type") or classify_event_type(item)
    score = 50
    if event_type == "融资":
        score += 30
    elif event_type == "中标/资质":
        score += 20
    elif event_type == "风险":
        score += 5

    text = f"{item.get('title', '')} {item.get('summary', '')}"
    if any(kw in text for kw in ["亿元", "领投", "专项资金", "拟支持", "高新技术企业"]):
        score += 10
    if item.get("source_type") == "risk_notice":
        score -= 5
    return max(0, min(score, 100))


# ============================================================
# 4. 跟进建议生成器
# ============================================================

def build_follow_up_reason(event_type: str, summary: str) -> str:
    """生成线索跟进理由"""
    if event_type == "融资":
        return "企业近期出现融资事件，通常意味着扩张、采购或账户结算需求上升。"
    if event_type == "中标/资质":
        return "企业近期获得项目/资质/补贴，通常意味着经营稳定性和资金周转需求提升。"
    if event_type == "风险":
        return "企业出现风险信号，适合用于存量客户预警或审慎触达。"
    return f"发现公开事件线索：{summary[:40]}"


def build_follow_up_action(company_name: str, event_type: str) -> str:
    """生成客户经理行动建议"""
    if event_type == "融资":
        return f"建议客户经理优先联系{company_name}，核实融资用途、开户需求与授信扩额机会。"
    if event_type == "中标/资质":
        return f"建议跟进{company_name}的项目回款、保函、供应链金融或结算服务机会。"
    if event_type == "风险":
        return f"建议将{company_name}纳入观察名单，复核工商、司法与经营异常变化。"
    return f"建议人工复核{company_name}的具体业务场景后再决定是否触达。"


# ============================================================
# 5. 噪声过滤与管线整合
# ============================================================

def is_noise_lead(title: str, summary: str, company_name: str) -> bool:
    """多层噪声识别：无效名称 + 宏观噪声 + 通用公告"""
    text = f"{title} {summary}"
    if not is_plausible_company_name(company_name):
        return True
    if any(kw in text for kw in MACRO_NOISE_KEYWORDS):
        return True
    if company_name == "未知企业":
        return True
    return False


def normalize_lead(item: dict) -> Optional[dict]:
    """单条线索标准化：提取→分类→评分→建议→过滤"""
    summary = item.get("summary") or item.get("description") or ""
    title = item.get("title") or item.get("company_hint") or summary[:50]
    event_type = classify_event_type({"title": title, "summary": summary})
    company_name = extract_company_name(summary if summary else title)

    if is_noise_lead(title, summary, company_name):
        return None

    source_type = item.get("source_type") or item.get("source") or "news"
    normalized = {
        "company_name": company_name,
        "title": title,
        "event_type": event_type,
        "source_url": item.get("source_url") or item.get("url") or "",
        "summary": summary,
        "source_type": source_type,
        "discovery_time": item.get("discovery_time") or datetime.now().isoformat(),
    }
    normalized["potential_score"] = score_lead(normalized)
    normalized["follow_up_reason"] = build_follow_up_reason(event_type, summary)
    normalized["follow_up_action"] = build_follow_up_action(company_name, event_type)
    return normalized


def build_report(raw_items: list[dict]) -> list[dict]:
    """完整管线：批量标准化 + 噪声过滤 + 评分排序"""
    report = []
    for item in raw_items:
        normalized = normalize_lead(item)
        if normalized is not None:
            report.append(normalized)
    report.sort(key=lambda x: x["potential_score"], reverse=True)
    return report
