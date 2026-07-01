# Credit Lead Mining - Agent Wrapper
"""
Agent封装：搜索→处理→存储 全自动运行

支持接入定时任务（cron），实现无人值守的线索监控。
"""

import json
import os
from datetime import datetime
from typing import Optional

from src.pipeline import build_report


class CreditLeadAgent:
    """信贷线索挖掘Agent — 搜索、处理、持久化一体化"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.log_dir = os.path.join(base_dir, "logs")
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

    def collect_raw_leads(self, targets: list[str]) -> list[dict]:
        """
        从多个搜索目标收集原始线索
        
        注意：此方法需配合搜索API使用。
        示例中使用web_search，可替换为任何数据源适配器。
        """
        raw_items = []
        for target in targets:
            # 用户需自行接入搜索API
            # results = web_search(target, limit=10)
            # raw_items.extend(results)
            print(f"[INFO] Searching: {target}")
        return raw_items

    def save_report(self, report: list[dict], prefix: str = "mining_report") -> str:
        """持久化报告到JSON文件"""
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        save_path = os.path.join(self.data_dir, filename)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return save_path

    def run(self, raw_items: list[dict]) -> list[dict]:
        """完整管线：收集→处理→评分→存储"""
        report = build_report(raw_items)
        if report:
            save_path = self.save_report(report)
            print(f"[OK] {len(report)} leads saved → {save_path}")
        else:
            print("[INFO] No valid leads found.")
        return report


if __name__ == "__main__":
    # 示例：使用本地测试数据运行
    sample_data = [
        {
            "title": "维他动力完成5亿元Pre-A轮融资",
            "source_url": "https://example.com/1",
            "summary": "维他动力（北京）科技有限公司完成5.00亿人民币Pre-A轮融资。",
            "source_type": "news",
        }
    ]
    agent = CreditLeadAgent()
    agent.run(sample_data)
