# -*- coding: utf-8 -*-
"""
判决文书网实时更新模块 - prosecution_system/src/wenshu_updater.py
实时更新 + 案件进展跟踪

⚠️ 注意：中国裁判文书网（wenshu.court.gov.cn）官方API需机构认证。
本模块提供两种方案：
  1. WenshuAPI（需要 court.gov.cn 授权 Token，需申请）
  2. WebScraper（模拟浏览器抓取，适用于公开案件）
  3. ManualTracker（手动更新，用于无API情况）

申请官方API: https://wenshu.court.gov.cn
"""

import os
import re
import json
import time
import hashlib
import asyncio
import aiohttp
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DATA_DIR = Path(__file__).parent.parent / "data"
TRACKER_FILE = DATA_DIR / "case_tracker.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class WenshuAPI:
    """
    判决文书网官方API客户端

    使用条件：
    - 在 https://wenshu.court.gov.cn 注册账号并申请API Token
    - Token 设置为环境变量 WENSHU_TOKEN

    ⚠️ 官方API目前仅对司法机关、高校等机构开放
    """

    BASE_URL = "https://wenshu.court.gov.cn/website/wenshu"

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("WENSHU_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.BASE_URL,
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=15),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _async_search(self, case_num: str, court: str, max_results: int) -> List[Dict]:
        """异步搜索案件（带 tenacity 重试）"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/181224CPTG/PT1ServerProxy.aspx",
                json={"cmenu": "case", "keyword": case_num, "court": court, "pageSize": max_results},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                raise aiohttp.ClientError(f"HTTP {resp.status}")

    def search_case(self, case_num: str, court: str = "", max_results: int = 10) -> List[Dict]:
        """
        按案号搜索案件文书（同步包装，自动重试 3 次）
        """
        if not self.token:
            print("⚠️ Wenshu API Token 未设置，请设置环境变量 WENSHU_TOKEN")
            print("   或访问 https://wenshu.court.gov.cn 申请API权限")
            return []

        try:
            return asyncio.run(self._async_search(case_num, court, max_results))
        except Exception as e:
            print(f"Wenshu API 请求失败（已达最大重试次数）: {e}")
            return []

    def get_case_detail(self, doc_id: str) -> Optional[Dict]:
        """获取指定文书详情"""
        if not self.token:
            return None

        try:
            response = self.session.get(
                f"{self.BASE_URL}/D000000001/{doc_id}.html",
                timeout=15,
            )
            if response.status_code == 200:
                return self._parse_doc_html(response.text)
        except Exception as e:
            print(f"获取文书详情失败: {e}")

        return None

    def _parse_doc_html(self, html: str) -> Dict:
        """解析文书HTML"""
        # 简化解析（实际需根据页面结构调整）
        data = {}
        patterns = {
            "case_num": r"案号[：:]\s*([^\s<>]+)",
            "court": r"审理法院[：:]\s*([^\s<>]+)",
            "judgment_date": r"判决日期[：:]\s*(\d{4}[年-]\d{1,2}[月-]\d{1,2}日?)",
            "judges": r"审判员[：:]\s*([^\s<>]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                data[key] = match.group(1).strip()
        return data


class WenshuScraper:
    """
    判决文书网爬虫（适用于无API Token的情况）

    警告：大规模爬取可能违反网站使用条款，仅用于合法研究目的
    请遵守 robots.txt 和网站的访问频率限制
    """

    BASE_URL = "https://wenshu.court.gov.cn"
    DELAY_SECONDS = 3  # 请求间隔（秒）

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://wenshu.court.gov.cn",
        })
        self.last_request_time = 0

    def _rate_limit(self):
        """请求频率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.DELAY_SECONDS:
            time.sleep(self.DELAY_SECONDS - elapsed)
        self.last_request_time = time.time()

    def search(self, keyword: str, case_type: str = "刑事", max_pages: int = 3) -> List[Dict]:
        """
        搜索案件文书（模拟搜索接口）

        警告：此方法仅用于研究目的，大规模爬取需获得授权
        """
        self._rate_limit()
        results = []

        try:
            # 实际请求（需处理反爬）
            response = self.session.get(
                f"{self.BASE_URL}/website/wenshu/181224CPTG/PT2ServerProxy.aspx",
                params={
                    "q": keyword,
                    "c": case_type,
                    "p": 1,
                },
                timeout=20,
            )
            # 解析结果（此处为伪代码，需根据实际响应调整）
            if response.status_code == 200:
                print(f"⚠️ 爬虫已请求，请手动验证结果页面")
        except Exception as e:
            print(f"爬虫请求失败: {e}")

        return results


class CaseTracker:
    """
    案件进展跟踪器

    功能：
    - 记录案件历史状态
    - 检测状态变更并发出告警
    - 支持多案件并行跟踪
    """

    def __init__(self, tracker_file: Path = TRACKER_FILE):
        _ensure_data_dir()
        self.tracker_file = tracker_file
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        self.tracked: Dict[str, Dict] = self._load()

    def _load(self) -> Dict:
        if self.tracker_file.exists():
            with open(self.tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(self.tracked, f, ensure_ascii=False, indent=2)

    def add_case(self, case_id: str, case_num: str = "", court: str = "",
                 status: str = "investigating", notes: str = ""):
        """添加跟踪案件"""
        self.tracked[case_id] = {
            "case_id": case_id,
            "case_num": case_num,
            "court": court,
            "status": status,
            "notes": notes,
            "added_date": datetime.now().strftime("%Y-%m-%d"),
            "last_check": None,
            "last_status": status,
            "history": [
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": status,
                    "event": "案件添加",
                }
            ],
        }
        self._save()
        print(f"✅ 已添加跟踪: {case_id}")

    def update_status(self, case_id: str, new_status: str,
                      event: str = "", notes: str = ""):
        """更新案件状态"""
        if case_id not in self.tracked:
            print(f"⚠️ 案件未在跟踪列表中: {case_id}")
            return

        entry = self.tracked[case_id]
        old_status = entry.get("last_status", "")
        now = datetime.now().strftime("%Y-%m-%d")

        entry["status"] = new_status
        entry["last_status"] = new_status
        entry["last_check"] = now
        if notes:
            entry["notes"] = notes

        history_entry = {
            "date": now,
            "status": new_status,
            "event": event or f"状态变更为：{new_status}",
        }
        if "history" not in entry:
            entry["history"] = []
        entry["history"].append(history_entry)

        self._save()

        if new_status != old_status:
            print(f"🔔 案件状态变更 [{case_id}]: {old_status} → {new_status}")
        else:
            print(f"✅ 案件状态已确认 [{case_id}]: {new_status}（无变化）")

    def check_for_updates(self, api_client: WenshuAPI = None) -> List[Dict]:
        """
        批量检查案件更新

        建议每天运行一次，不要频繁调用
        """
        updates = []

        for case_id, entry in self.tracked.items():
            case_num = entry.get("case_num", "")
            if not case_num or not api_client:
                continue

            results = api_client.search_case(case_num, court=entry.get("court", ""))

            # 比较判决日期、罪名等关键字段
            if results:
                latest = results[0]
                # 检测是否有新的判决文书
                if "judgment_date" in latest:
                    last_check = entry.get("last_check", "")
                    if latest["judgment_date"] != last_check:
                        updates.append({
                            "case_id": case_id,
                            "case_num": case_num,
                            "new_doc": latest,
                            "change_type": "new_judgment",
                        })
                        self.update_status(
                            case_id,
                            "judged",
                            event=f"发现新判决文书：{latest.get('judgment_date', '')}",
                        )

        return updates

    def get_case_history(self, case_id: str) -> List[Dict]:
        """获取案件状态历史"""
        if case_id in self.tracked:
            return self.tracked[case_id].get("history", [])
        return []

    def list_tracked(self) -> List[Dict]:
        """列出所有跟踪案件"""
        return [
            {
                "case_id": cid,
                "case_num": e.get("case_num", ""),
                "court": e.get("court", ""),
                "status": e.get("status", ""),
                "last_check": e.get("last_check", ""),
                "last_event": e.get("history", [{}])[-1].get("event", ""),
            }
            for cid, e in self.tracked.items()
        ]

    def remove_case(self, case_id: str):
        """移除跟踪案件"""
        if case_id in self.tracked:
            del self.tracked[case_id]
            self._save()
            print(f"✅ 已移除跟踪: {case_id}")
        else:
            print(f"⚠️ 案件不在跟踪列表中: {case_id}")


class ManualTracker:
    """
    手动案件跟踪（无需API）

    用于：
    - 没有Wenshu API Token时
    - 手动输入案件进展
    - 记录文献调研结果
    """

    def __init__(self, tracker_file: Path = TRACKER_FILE):
        _ensure_data_dir()
        self.tracker_file = tracker_file
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        self.tracked: Dict[str, Dict] = self._load()

    def _load(self) -> Dict:
        if self.tracker_file.exists():
            with open(self.tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(self.tracked, f, ensure_ascii=False, indent=2)

    def log_event(self, case_id: str, event: str, source: str = "",
                  url: str = "", date: str = None):
        """记录案件事件"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        if case_id not in self.tracked:
            self.tracked[case_id] = {
                "case_id": case_id,
                "events": [],
            }
        if "events" not in self.tracked[case_id]:
            self.tracked[case_id]["events"] = []

        entry = {
            "date": date,
            "event": event,
            "source": source,
            "url": url,
        }
        self.tracked[case_id]["events"].append(entry)
        self._save()
        print(f"✅ 事件已记录 [{case_id}]: {date} - {event}")

    def get_events(self, case_id: str) -> List[Dict]:
        """获取案件所有事件"""
        if case_id in self.tracked:
            return self.tracked[case_id].get("events", [])
        return []

    def list_cases(self) -> List[str]:
        """列出所有有记录的案件"""
        return list(self.tracked.keys())


# ---- CLI 入口 ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="判决文书网案件跟踪器")
    parser.add_argument("--add", type=str, help="添加跟踪案件（案件ID）")
    parser.add_argument("--case-num", type=str, help="案号")
    parser.add_argument("--court", type=str, help="审理法院")
    parser.add_argument("--status", type=str, default="investigating",
                        help="初始状态")
    parser.add_argument("--update", type=str, help="更新案件状态（案件ID）")
    parser.add_argument("--new-status", type=str, help="新状态")
    parser.add_argument("--event", type=str, help="事件描述")
    parser.add_argument("--list", action="store_true", help="列出所有跟踪案件")
    parser.add_argument("--history", type=str, help="查看案件历史（案件ID）")
    parser.add_argument("--remove", type=str, help="移除跟踪案件")
    parser.add_argument("--log", type=str, nargs=3, metavar=("CASE_ID", "EVENT", "SOURCE"),
                        help="记录事件: --log CASE_ID 事件描述 来源")
    parser.add_argument("--check-updates", action="store_true", help="批量检查更新（需API Token）")
    args = parser.parse_args()

    tracker = CaseTracker()

    if args.add:
        tracker.add_case(args.add, case_num=args.case_num or "",
                         court=args.court or "", status=args.status)

    elif args.update:
        tracker.update_status(args.update, args.new_status or "investigating",
                              event=args.event or "")

    elif args.list:
        for c in tracker.list_tracked():
            print(f"[{c['case_id']}] {c['case_num']} | {c['court']} | {c['status']}")
            print(f"    最近事件: {c.get('last_event', '无')}")

    elif args.history:
        for h in tracker.get_case_history(args.history):
            print(f"  {h.get('date', '')}: {h.get('status', '')} — {h.get('event', '')}")

    elif args.remove:
        tracker.remove_case(args.remove)

    elif args.log:
        case_id, event, source = args.log
        manual = ManualTracker()
        manual.log_event(case_id, event, source=source)

    elif args.check_updates:
        api = WenshuAPI()
        updates = tracker.check_for_updates(api)
        if updates:
            for u in updates:
                print(f"🔔 检测到更新 [{u['case_id']}]: {u['change_type']}")
        else:
            print("✅ 未检测到更新")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
