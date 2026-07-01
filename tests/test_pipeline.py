# Credit Lead Mining - Unit Tests
"""
核心管线单元测试：企业名提取、事件分类、评分排序、输出schema
"""

import unittest
from src.pipeline import (
    build_report,
    classify_event_type,
    extract_company_name,
    is_noise_lead,
    is_plausible_company_name,
    normalize_lead,
    score_lead,
)


class TestExtractCompanyName(unittest.TestCase):
    """企业名称智能提取测试"""

    def test_extract_from_financing_summary(self):
        text = "维他动力（北京）科技有限公司完成5.00亿人民币Pre-A轮融资，由某产业基金领投。"
        self.assertEqual(extract_company_name(text), "维他动力（北京）科技有限公司")

    def test_extract_from_bidding_title(self):
        text = "北京中科软科技有限公司中标某银行核心系统升级项目"
        self.assertEqual(extract_company_name(text), "北京中科软科技有限公司")

    def test_returns_unknown_for_commentary(self):
        text = "财联社5月3日电，阿贝尔表示，伯克希尔并不排斥投资科技公司。"
        self.assertEqual(extract_company_name(text), "未知企业")

    def test_returns_unknown_for_empty(self):
        self.assertEqual(extract_company_name(""), "未知企业")
        self.assertEqual(extract_company_name(None), "未知企业")

    def test_filters_macro_noise_prefix(self):
        text = "2026年小微企业融资支持政策发布"
        self.assertEqual(extract_company_name(text), "未知企业")


class TestClassifyEventType(unittest.TestCase):
    """事件三分类测试"""

    def test_funding_event(self):
        item = {"title": "维他动力完成5亿元Pre-A轮融资", "summary": "公司宣布完成Pre-A轮融资。"}
        self.assertEqual(classify_event_type(item), "融资")

    def test_risk_event(self):
        item = {"title": "某企业被列入经营异常名录", "summary": "因未按时公示年报，被列入经营异常名录。"}
        self.assertEqual(classify_event_type(item), "风险")

    def test_award_event(self):
        item = {"title": "某科技公司中标智慧城市项目", "summary": "项目公示期为5个工作日。"}
        self.assertEqual(classify_event_type(item), "中标/资质")

    def test_other_event(self):
        item = {"title": "行业峰会即将召开", "summary": "多个企业将参展。"}
        self.assertEqual(classify_event_type(item), "其他")


class TestScoreLead(unittest.TestCase):
    """线索评分模型测试"""

    def test_funding_scores_higher_than_risk(self):
        funding = {"title": "融资", "summary": "完成5亿元融资。", "event_type": "融资", "source_type": "news"}
        risk = {"title": "风险", "summary": "经营异常。", "event_type": "风险", "source_type": "risk_notice"}
        self.assertGreater(score_lead(funding), score_lead(risk))

    def test_large_amount_gets_bonus(self):
        small = {"title": "融资", "summary": "完成千万元融资。", "event_type": "融资", "source_type": "news"}
        large = {"title": "融资", "summary": "完成5亿元融资。", "event_type": "融资", "source_type": "news"}
        self.assertGreater(score_lead(large), score_lead(small))

    def test_score_clamped_to_100(self):
        item = {"title": "领投", "summary": "完成5亿元融资领投。", "event_type": "融资", "source_type": "news"}
        self.assertLessEqual(score_lead(item), 100)

    def test_score_non_negative(self):
        item = {"title": "", "summary": "", "event_type": "其他", "source_type": "risk_notice"}
        self.assertGreaterEqual(score_lead(item), 0)


class TestBuildReport(unittest.TestCase):
    """完整管线集成测试"""

    def test_sorts_by_score_descending(self):
        raw_items = [
            {"title": "风险", "source_url": "https://x.com/r", "summary": "北京某达科技有限公司经营异常。", "source_type": "risk_notice"},
            {"title": "融资", "source_url": "https://x.com/f", "summary": "维他动力（北京）科技有限公司完成5亿元融资。", "source_type": "news"},
        ]
        report = build_report(raw_items)
        self.assertGreaterEqual(report[0]["potential_score"], report[1]["potential_score"])

    def test_unified_output_schema(self):
        raw_items = [
            {"title": "融资", "url": "https://x.com", "description": "维他动力（北京）科技有限公司完成融资。", "source": "news"}
        ]
        report = build_report(raw_items)
        item = report[0]
        required_keys = ["company_name", "title", "event_type", "source_url", "summary",
                         "source_type", "discovery_time", "potential_score",
                         "follow_up_reason", "follow_up_action"]
        for key in required_keys:
            self.assertIn(key, item, f"Missing key: {key}")

    def test_filters_noise(self):
        raw_items = [
            {"title": "政策通知", "source_url": "", "summary": "北京市人民政府办公厅发布营商环境工作要点。", "source_type": "news"}
        ]
        report = build_report(raw_items)
        self.assertEqual(len(report), 0)


class TestIsPlausibleCompanyName(unittest.TestCase):
    """企业名称合理性判断测试"""

    def test_valid_company(self):
        self.assertTrue(is_plausible_company_name("北京中科软科技有限公司"))

    def test_invalid_short_name(self):
        self.assertFalse(is_plausible_company_name("北京"))

    def test_invalid_generic_name(self):
        self.assertFalse(is_plausible_company_name("提高企业"))


if __name__ == "__main__":
    unittest.main()
