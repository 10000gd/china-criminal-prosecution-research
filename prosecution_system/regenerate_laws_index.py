#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新生成 laws_full_index.json
从文件头部元数据行正确提取日期，并对无效日期尝试从文件名修复或置空
"""

import json
import re
import os
from pathlib import Path

LAWS_DIR = Path(__file__).parent / "cases" / "legaldb" / "laws"
OUTPUT_FILE = Path(__file__).parent / "cases" / "legaldb" / "laws_full_index.json"

CATEGORY_KEYWORDS = {
    "宪法": ["宪法", "宪法的修改", "关于修改宪法"],
    "法律": ["中华人民共和国", "全国人民代表大会", "全国人民代表大会常务委员会", "全国人大"],
    "行政法规": ["条例", "办法", "规定", "细则", "规程", "决定"],
    "司法解释": ["最高人民法院", "最高人民检察院", "关于执行", "关于办理", "关于审理", "关于适用", "关于确定罪名"],
    "监察法规": ["监察法", "监察机关"],
}


def infer_category(name: str) -> str:
    """根据名称推断分类"""
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return cat
    return "其他"


def extract_date_from_path(path_str: str) -> str:
    """
    从路径中提取日期。
    路径格式示例:
    docx/法律/xxx_20201226_ff8080817.docx  -> 20201226
    docx/宪法/xxx_19880412_2c909fdd.docx   -> 19880412
    docx/法律/xxx_ff8080817.docx           -> ""
    """
    basename = os.path.basename(path_str)
    # 匹配8位数字
    match = re.search(r'_(\d{8})', basename)
    if match:
        date_str = match.group(1)
        # 验证是否为合理日期
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        if 1949 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
            return date_str
    return ""


def load_laws() -> dict:
    """加载所有法律文件，返回 dict{名称: info}"""
    all_laws = {}
    bad_dates = []
    fixed_dates = []  # 从路径修复的

    txt_files = list(LAWS_DIR.glob("*.txt"))

    for fpath in txt_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            meta = {"category": "其他", "date": "", "path": str(fpath), "name": ""}
            text_lines = []
            name_set = False

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    if not name_set and not any(kw in stripped for kw in ["分类:", "发布:", "来源:"]):
                        meta["name"] = stripped[1:].strip()
                        name_set = True
                    elif "分类:" in stripped:
                        cat = stripped.split(":", 1)[1].strip()
                        meta["category"] = cat
                    elif ("\u53d1\u5e03\u65e5\u671f\uff1a" in stripped or
                          "\u53d1\u5e03\u65e5\u671f:" in stripped):
                        # 发布日期行，支持全角冒号 (\uff1a) 或 ASCII 冒号
                        sep = "\uff1a" if "\uff1a" in stripped else ":"
                        raw = stripped.split(sep, 1)[1].strip()
                        # 验证：必须以8位数字开头
                        if re.match(r"^\d{8}", raw):
                            meta["date"] = raw[:8]
                        else:
                            # 无效，尝试从文件名中找8位日期
                            path_date = extract_date_from_path(str(fpath))
                            if path_date:
                                meta["date"] = path_date
                                fixed_dates.append((meta["name"], raw[:20], path_date))
                            else:
                                meta["date"] = ""
                                bad_dates.append((meta["name"], raw[:20], str(fpath)))
                    elif "来源:" in stripped:
                        meta["path"] = stripped
                elif not line.startswith("=") and line.strip() == "" and not text_lines:
                    continue
                else:
                    text_lines.append(line.rstrip())

            name = meta.get("name") or fpath.stem
            text = "\n".join(text_lines).strip()

            if len(text) > 50 and name:
                # 分类推断兜底
                if meta["category"] == "其他" or meta["category"] == "未知":
                    inferred = infer_category(name)
                    if inferred != "其他":
                        meta["category"] = inferred

                all_laws[name] = {
                    "name": name,
                    "date": meta["date"],
                    "path": meta["path"],
                    "category": meta["category"],
                }

        except Exception as e:
            print(f"  ⚠️ 加载失败: {fpath.name}: {e}")

    return all_laws, bad_dates, fixed_dates


def main():
    print("=== 重新生成 laws_full_index.json ===\n")

    all_laws, bad_dates, fixed_dates = load_laws()

    # 统计分类
    cats = {}
    for info in all_laws.values():
        cats[info["category"]] = cats.get(info["category"], 0) + 1

    # 验证日期
    good_dates = sum(1 for i in all_laws.values() if re.match(r"^\d{8}$", i["date"]))
    total = len(all_laws)

    output = {
        "total": total,
        "categories": cats,
        "all_laws": all_laws,
        "date_quality": {
            "valid_8digit": good_dates,
            "invalid_or_empty": total - good_dates,
            "coverage": f"{good_dates / total * 100:.1f}%",
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"总条目: {total}")
    print(f"日期有效(8位): {good_dates} ({good_dates/total*100:.1f}%)")
    print(f"日期无效/空: {total - good_dates} ({(total-good_dates)/total*100:.1f}%)")
    print()
    print("分类统计:")
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")
    print()

    if fixed_dates:
        print(f"✅ 从路径修复了 {len(fixed_dates)} 条日期:")
        for name, raw, fixed in fixed_dates[:5]:
            print(f"  [{raw}] -> [{fixed}] | {name[:50]}")
        if len(fixed_dates) > 5:
            print(f"  ... 还有 {len(fixed_dates)-5} 条")
        print()

    if bad_dates:
        print(f"⚠️  有 {len(bad_dates)} 条无法确定日期:")
        for name, raw, path in bad_dates[:5]:
            print(f"  [{raw}] | {name[:50]}")
        if len(bad_dates) > 5:
            print(f"  ... 还有 {len(bad_dates)-5} 条")
        print()

    print(f"已写入: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
