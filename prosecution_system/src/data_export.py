# -*- coding: utf-8 -*-
"""
数据导出模块 - data_export.py

功能：
- CSV导出
- JSON导出
- Excel导出
- 统计分析报表
"""

import json
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class DataExporter:
    """数据导出器"""
    
    @staticmethod
    def export_to_csv(data: List[Dict], columns: List[str] = None, output: io.StringIO = None) -> str:
        """导出为CSV格式"""
        if not data:
            return ""
        
        if output is None:
            output = io.StringIO()
        
        writer = csv.writer(output)
        
        # 写入表头
        if columns is None:
            columns = list(data[0].keys())
        writer.writerow(columns)
        
        # 写入数据
        for row in data:
            writer.writerow([row.get(col, '') for col in columns])
        
        return output.getvalue()
    
    @staticmethod
    def export_to_json(data: Any, pretty: bool = True) -> str:
        """导出为JSON格式"""
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def export_to_markdown_table(data: List[Dict], columns: List[str] = None) -> str:
        """导出为Markdown表格"""
        if not data:
            return ""
        
        if columns is None:
            columns = list(data[0].keys())
        
        lines = []
        
        # 表头
        header = "| " + " | ".join(columns) + " |"
        separator = "|" + "|".join([" --- " for _ in columns]) + "|"
        lines.append(header)
        lines.append(separator)
        
        # 数据行
        for row in data:
            values = [str(row.get(col, '')) for col in columns]
            lines.append("| " + " | ".join(values) + " |")
        
        return "\n".join(lines)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, db=None):
        self.db = db
    
    def generate_user_report(self) -> Dict:
        """生成用户报告"""
        if not self.db:
            return {"error": "数据库未连接"}
        
        stats = self.db.get_stats()
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户增长趋势
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM users
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """)
            user_growth = [dict(row) for row in cursor.fetchall()]
            
            # 角色分布
            cursor.execute("""
                SELECT role, COUNT(*) as count
                FROM users
                GROUP BY role
            """)
            role_distribution = [dict(row) for row in cursor.fetchall()]
        
        return {
            "title": "用户统计报告",
            "generated_at": datetime.now().isoformat(),
            "total_users": stats.get("total_users", 0),
            "user_growth": user_growth,
            "role_distribution": role_distribution,
        }
    
    def generate_activity_report(self) -> Dict:
        """生成活动报告"""
        if not self.db:
            return {"error": "数据库未连接"}
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 操作统计
            cursor.execute("""
                SELECT action, COUNT(*) as count
                FROM operation_logs
                GROUP BY action
                ORDER BY count DESC
            """)
            action_stats = [dict(row) for row in cursor.fetchall()]
            
            # 每日活跃
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM operation_logs
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            daily_activity = [dict(row) for row in cursor.fetchall()]
            
            # 热门操作
            cursor.execute("""
                SELECT action, COUNT(*) as count
                FROM operation_logs
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            """)
            popular_actions = [dict(row) for row in cursor.fetchall()]
        
        return {
            "title": "系统活动报告",
            "generated_at": datetime.now().isoformat(),
            "action_statistics": action_stats,
            "daily_activity": daily_activity,
            "popular_actions": popular_actions,
        }
    
    def generate_content_report(self) -> Dict:
        """生成内容报告"""
        if not self.db:
            return {"error": "数据库未连接"}
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 热门收藏
            cursor.execute("""
                SELECT case_id, COUNT(*) as count
                FROM favorites
                GROUP BY case_id
                ORDER BY count DESC
                LIMIT 20
            """)
            popular_favorites = [dict(row) for row in cursor.fetchall()]
            
            # 热门搜索
            cursor.execute("""
                SELECT query, COUNT(*) as count
                FROM search_history
                GROUP BY query
                ORDER BY count DESC
                LIMIT 20
            """)
            popular_searches = [dict(row) for row in cursor.fetchall()]
        
        return {
            "title": "内容统计报告",
            "generated_at": datetime.now().isoformat(),
            "popular_favorites": popular_favorites,
            "popular_searches": popular_searches,
        }
    
    def generate_full_report(self) -> Dict:
        """生成完整报告"""
        return {
            "report_generated_at": datetime.now().isoformat(),
            "user_report": self.generate_user_report(),
            "activity_report": self.generate_activity_report(),
            "content_report": self.generate_content_report(),
        }
    
    def export_report(self, format: str = "json") -> str:
        """导出报告"""
        report = self.generate_full_report()
        
        if format == "json":
            return DataExporter.export_to_json(report)
        elif format == "csv":
            # 导出为CSV格式
            rows = []
            for section, data in report.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    rows.append(item)
            return DataExporter.export_to_csv(rows)
        else:
            return DataExporter.export_to_json(report)


class CaseDataExporter:
    """案件数据导出器"""
    
    @staticmethod
    def export_cases_to_csv(cases: List[Dict]) -> str:
        """导出案件为CSV"""
        columns = ['case_id', 'case_name', 'crime', 'province', 'sentence_years']
        optional_cols = ['is_初犯', 'is_累犯', 'is_自首', 'is_坦白', 'is_赔偿']
        
        all_columns = columns + optional_cols
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 表头
        writer.writerow(all_columns)
        
        # 数据
        for case in cases:
            row = []
            for col in all_columns:
                value = case.get(col, '')
                if isinstance(value, bool):
                    value = '是' if value else '否'
                row.append(value)
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def export_sentencing_summary(cases: List[Dict]) -> str:
        """导出量刑摘要"""
        from collections import defaultdict
        
        # 按罪名分组
        by_crime = defaultdict(list)
        for case in cases:
            by_crime[case['crime']].append(case)
        
        lines = ["# 量刑案例摘要报告", ""]
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "")
        lines.append(f"案例总数: {len(cases)}", "")
        lines.append(f"罪名种类: {len(by_crime)}", "")
        lines.append("", "---", "")
        
        for crime, crime_cases in sorted(by_crime.items()):
            lines.append(f"\n## {crime}")
            lines.append(f"- 案例数: {len(crime_cases)}")
            
            # 计算统计
            years = [c.get('sentence_years', 0) for c in crime_cases]
            if years:
                avg = sum(years) / len(years)
                lines.append(f"- 平均刑期: {avg:.2f}年")
                lines.append(f"- 最短: {min(years):.1f}年")
                lines.append(f"- 最长: {max(years):.1f}年")
        
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== 数据导出模块 ===")
    print("✅ 模块已加载")
    print("\n使用方式:")
    print("  from data_export import DataExporter, ReportGenerator")
    print("  csv = DataExporter.export_to_csv(data)")
    print("  report = ReportGenerator(db).generate_full_report()")
