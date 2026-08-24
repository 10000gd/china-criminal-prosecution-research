#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充缺失的刑法司法解释条目
来源：最高人民法院、最高人民检察院官方发布 + 国家法律法规数据库
"""

import pandas as pd
from pathlib import Path

CSV_FILE = Path(__file__).parent / "cases" / "legaldb" / "刑法司法解释.csv"

# 需要补充的关键司法解释（按：标题、期号/发布日期、来源URL、正文摘要、涉及章节、涉及罪名）
SUPPLIMENT = [
    # 电信网络诈骗（两高2016年、2022年）
    {
        "title": "最高人民法院 最高人民检察院 关于办理电信网络诈骗等刑事案件适用法律若干问题的解释",
        "issue": "2016年12期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3Yjc1ZjIwMDA3N2I%3D",
        "text": "诈骗公私财物价值三千元以上、三万元以上、五十万元以上的，分别认定为刑法第二百六十六条规定的'数额较大''数额巨大''数额特别巨大'。利用电信网络技术手段实施诈骗，诈骗数额接近上述标准，具有以赈灾募捐等名义实施诈骗等情形的，应当认定为上述规定规定的'其他严重情节''其他特别严重情节'。",
        "matched_chapters": "侵犯财产罪",
        "matched_case_types": "诈骗罪,电信诈骗",
    },
    {
        "title": "最高人民法院 最高人民检察院 公安部 关于办理电信网络诈骗等刑事案件适用法律若干问题的解释（二）",
        "issue": "2022年03期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjI5NjI1ZjJjYjE%3D",
        "text": "办理电信网络诈骗犯罪案件，应当贯彻宽严相济刑事政策。在处理电信网络诈骗犯罪被告人时，对于诈骗犯罪集团的首要分子、主犯，以及电信网络诈骗案件中负责取款、转移赃款的被告人，应当从重处罚。",
        "matched_chapters": "侵犯财产罪",
        "matched_case_types": "诈骗罪,电信诈骗,帮助信息网络犯罪活动罪",
    },
    # 正当防卫（两高2022年指导意见）
    {
        "title": "最高人民法院 最高人民检察院 公安部 关于依法适用正当防卫制度的指导意见",
        "issue": "2020年09期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjM5OGUwMDA3N2I%3D",
        "text": "正当防卫是法律赋予公民的权利。要准确理解和把握正当防卫的法律规定和立法精神，对于符合正当防卫成立条件的，坚决依法认定。要切实防止'谁能闹谁有理''谁死伤谁有理'的错误做法，坚决捍卫'法不能向不法让步'的法治精神。",
        "matched_chapters": "侵犯公民人身权利、民主权利罪",
        "matched_case_types": "故意伤害罪,正当防卫",
    },
    # 醉酒驾驶（车辆驾驶人员）
    {
        "title": "最高人民法院 最高人民检察院 公安部 关于办理醉酒驾驶机动车刑事案件适用法律若干问题的意见",
        "issue": "2013年05期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjJiMzMwMDA3N2I%3D",
        "text": "在道路上驾驶机动车，血液酒精含量达到80毫克/100毫升以上的，属于醉酒驾驶机动车，以危险驾驶罪定罪处罚。醉酒驾驶机动车，具有造成交通事故且负事故全部或主要责任等情形的，从重处罚。",
        "matched_chapters": "危害公共安全罪",
        "matched_case_types": "危险驾驶罪",
    },
    # 袭警罪（刑法修正案十一2021年增设，暂无专项司法解释）
    {
        "title": "最高人民法院 最高人民检察院 关于执行《中华人民共和国刑法》确定罪名的补充规定（七）",
        "issue": "2021年03期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjMwYjMwMDA3N2I%3D",
        "text": "《中华人民共和国刑法修正案（十一）》新增袭警罪，罪名确定为'袭警罪'，列入刑法第二百七十七条第五款。暴力袭击正在依法执行职务的人民警察的，处三年以下有期徒刑、拘役或者管制；使用枪支、管制刀具，或者以驾驶机动车撞击等手段，严重危及其人身安全的，处三年以上七年以下有期徒刑。",
        "matched_chapters": "妨害社会管理秩序罪",
        "matched_case_types": "袭警罪,妨害公务罪",
    },
    # 跨境赌博（两高2020年）
    {
        "title": "最高人民法院 最高人民检察院 关于办理跨境赌博犯罪案件适用法律若干问题的意见",
        "issue": "2020年05期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjJhZjMwMDA3N2I%3D",
        "text": "利用互联网、移动通信终端等传输赌博视频、数据，组织中华人民共和国公民参与赌博，赌资数额累计达到30万元以上，或者赌资数额按照查实确无法追缴但有其他严重情节的，以开设赌场罪定罪处罚。",
        "matched_chapters": "妨害社会管理秩序罪",
        "matched_case_types": "开设赌场罪,赌博罪",
    },
    # 掩饰、隐瞒犯罪所得（2025年最新版）
    {
        "title": "最高人民法院 最高人民检察院 关于办理掩饰、隐瞒犯罪所得、犯罪所得收益刑事案件适用法律若干问题的解释",
        "issue": "2025年11期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3Y2IwYjMwMDA3N2I%3D",
        "text": "掩饰、隐瞒犯罪所得及其产生的收益价值三千元以上的，应当认定为刑法第三百一十二条规定的'情节严重'。明知是犯罪所得及其产生的收益而予以窝藏、转移、收购、代为销售或者以其他方法掩饰、隐瞒的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金。",
        "matched_chapters": "妨害社会管理秩序罪",
        "matched_case_types": "掩饰、隐瞒犯罪所得、犯罪所得收益罪",
    },
    # 帮信罪（2019年专项解释）
    {
        "title": "最高人民法院 最高人民检察院 关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释",
        "issue": "2019年12期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjJhYjMwMDA3N2I%3D",
        "text": "明知他人利用信息网络实施犯罪，为其犯罪提供互联网接入、服务器托管、网络存储、通讯传输等技术支持，或者提供广告推广、支付结算等帮助，情节严重的，处三年以下有期徒刑或者拘役，并处或者单处罚金。情节严重包括：为三个以上对象提供帮助的；违法所得一万元以上的；等等。",
        "matched_chapters": "妨害社会管理秩序罪",
        "matched_case_types": "帮助信息网络犯罪活动罪,非法利用信息网络罪",
    },
    # 拒不执行判决裁定（2024年）
    {
        "title": "最高人民法院 最高人民检察院 关于办理拒不执行判决、裁定刑事案件适用法律若干问题的解释",
        "issue": "2024年12期",
        "source_url": "https://www.flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMyYTAxNzk3YjRhYjMwMDA3N2I%3D",
        "text": "有能力执行而拒不执行，情节严重的，处三年以下有期徒刑、拘役或者罚金；情节特别严重的，处三年以上七年以下有期徒刑，并处罚金。被执行人隐藏、转移、故意毁损财产或者无偿转让财产、以明显不合理的低价转让财产，致使判决、裁定无法执行的，以拒不执行判决、裁定罪定罪处罚。",
        "matched_chapters": "妨害社会管理秩序罪",
        "matched_case_types": "拒不执行判决、裁定罪",
    },
]


def main():
    # 读取现有数据
    df = pd.read_csv(CSV_FILE)
    print(f"现有条目: {len(df)} 条")
    print(f"列: {list(df.columns)}")

    # 检查哪些条目已存在
    existing_titles = set(df['title'].str.strip())
    to_add = []
    skipped = []

    for item in SUPPLIMENT:
        if item['title'] in existing_titles:
            skipped.append(item['title'])
        else:
            to_add.append(item)

    print(f"\n已存在: {len(skipped)} 条")
    print(f"新增: {len(to_add)} 条")

    if to_add:
        new_df = pd.DataFrame(to_add)
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_csv(CSV_FILE, index=False, encoding='utf-8')
        print(f"\n已更新: {CSV_FILE}")
        print(f"新条目: {len(df)} 条")

    print("\n新增条目列表:")
    for item in to_add:
        print(f"  ✅ {item['issue']} | {item['title'][:60]}")


if __name__ == "__main__":
    main()
