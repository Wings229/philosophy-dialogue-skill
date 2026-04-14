#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雄辩天下杯赛 - 角色分配脚本 v2.0
- 从 philosopher-registry.md 动态读取人物（不硬编码）
- 从观众提交的题目文件动态读取题目（不硬编码）
- 确保角色唯一性：主持人/参赛者/评委/观众互斥
- 出题人只能是观众（参赛者与评委不能出题）

安全声明：
- 仅使用 Python 标准库（random, os, re, sys, json）
- 无网络调用（无 urllib, requests, socket 等）
- 无子进程调用（无 subprocess, os.system 等）
- 文件读取范围：仅 references/philosopher-registry.md 和用户指定的题目文件
- 文件写入范围：仅 memory/philosophy-dialogues/tournaments/ 目录
"""

import random
import os
import re
import sys
import json
from typing import List, Dict, Optional


def load_philosophers(registry_path: str) -> List[str]:
    """
    从 philosopher-registry.md 动态读取哲学家中文名称列表。
    解析 Markdown 表格，提取「中文名称」列。
    """
    if not os.path.exists(registry_path):
        print(f"❌ 注册表文件不存在: {registry_path}")
        sys.exit(1)

    philosophers = []
    with open(registry_path, 'r', encoding='utf-8') as f:
        in_table = False
        header_parsed = False
        name_col_idx = -1

        for line in f:
            line = line.strip()
            # 跳过空行
            if not line:
                in_table = False
                header_parsed = False
                continue

            # 检测表格行（包含 |）
            if '|' not in line:
                in_table = False
                header_parsed = False
                continue

            cols = [c.strip() for c in line.split('|')]
            # 去掉首尾空元素
            cols = [c for c in cols if c or cols.index(c) not in (0, len(cols)-1)]

            # 跳过分隔行（--- 行）
            if all(re.match(r'^[-:]+$', c) for c in cols if c):
                continue

            # 解析表头，找到「中文名称」列
            if not header_parsed:
                for i, col in enumerate(cols):
                    if '中文名称' in col:
                        name_col_idx = i
                        break
                if name_col_idx >= 0:
                    header_parsed = True
                    in_table = True
                continue

            # 解析数据行
            if in_table and header_parsed and name_col_idx >= 0:
                if name_col_idx < len(cols):
                    name = cols[name_col_idx].strip()
                    if name and name != '中文名称' and not re.match(r'^[-:]+$', name):
                        philosophers.append(name)

    # 去重
    seen = set()
    unique = []
    for p in philosophers:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return unique


def load_questions(questions_path: str) -> List[Dict[str, str]]:
    """
    从观众提交的题目文件动态读取辩论题目。
    支持两种格式：
    1. 纯文本（每行一个题目）
    2. Markdown 表格（| # | 题目 | 贡献者 |）
    """
    if not os.path.exists(questions_path):
        return []

    questions = []
    with open(questions_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 尝试解析 Markdown 表格
    if '|' in content:
        in_table = False
        header_parsed = False
        question_col_idx = -1
        contributor_col_idx = -1

        for line in content.split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                in_table = False
                header_parsed = False
                continue

            cols = [c.strip() for c in line.split('|')]
            cols = [c for c in cols if c or cols.index(c) not in (0, len(cols)-1)]

            if all(re.match(r'^[-:]+$', c) for c in cols if c):
                continue

            if not header_parsed:
                for i, col in enumerate(cols):
                    if '题目' in col:
                        question_col_idx = i
                    if '贡献者' in col:
                        contributor_col_idx = i
                if question_col_idx >= 0:
                    header_parsed = True
                    in_table = True
                continue

            if in_table and header_parsed:
                q = cols[question_col_idx].strip() if question_col_idx < len(cols) else ''
                c = cols[contributor_col_idx].strip() if contributor_col_idx >= 0 and contributor_col_idx < len(cols) else '匿名'
                if q and not q.startswith('#') and not re.match(r'^[-:]+$', q):
                    questions.append({
                        'question': q,
                        'contributor': c
                    })
    else:
        # 纯文本格式：每行一个题目
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                questions.append({
                    'question': line,
                    'contributor': '匿名'
                })

    return questions


def allocate_roles(
    philosophers: List[str],
    num_contestants: int = 32,
    num_judges: int = 20
) -> Dict[str, List[str]]:
    """
    分配角色：主持人/参赛者/评委/观众
    确保角色互斥，每人只能担任一个角色
    """
    total = len(philosophers)
    needed = 1 + num_contestants + num_judges
    if total < needed:
        print(f"⚠️ 人数不足: 需要 {needed} 人，实际 {total} 人")
        print(f"   自动调整: 参赛者 {min(num_contestants, total - 1 - num_judges)} 人")
        num_contestants = min(num_contestants, total - 1 - num_judges)
        if num_contestants < 2:
            print("❌ 人数太少，无法举办比赛")
            sys.exit(1)

    shuffled = random.sample(philosophers, total)

    idx = 0

    # 1. 选择 1 名主持人
    host = shuffled[idx]
    idx += 1

    # 2. 选择参赛者
    contestants = shuffled[idx:idx + num_contestants]
    idx += num_contestants

    # 3. 选择评委
    judges = shuffled[idx:idx + num_judges]
    idx += num_judges

    # 4. 剩余为观众（出题人只能是观众）
    audience = shuffled[idx:]

    return {
        "host": [host],
        "contestants": contestants,
        "judges": judges,
        "audience": audience
    }


def assign_questions_to_audience(
    audience: List[str],
    questions: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    将题目分配给观众。
    如果题目数 < 观众数，循环使用。
    如果题目数 > 观众数，截断。
    每个题目重新标记贡献者为对应的观众。
    """
    assigned = []
    for i, person in enumerate(audience):
        if i < len(questions):
            assigned.append({
                'id': i + 1,
                'question': questions[i]['question'],
                'contributor': person
            })
        # 如果题目不够，该观众不出题
    return assigned


def generate_bracket(contestants: List[str]) -> List[Dict]:
    """
    生成对阵图（单败淘汰）
    """
    shuffled = contestants.copy()
    random.shuffle(shuffled)

    rounds = []
    current_round = shuffled

    round_num = 1
    while len(current_round) > 1:
        matches = []

        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                match = {
                    "round": round_num,
                    "match_id": len(matches) + 1,
                    "contestant1": current_round[i],
                    "contestant2": current_round[i + 1],
                    "winner": None,
                    "score1": None,
                    "score2": None
                }
                matches.append(match)
            else:
                # 轮空（奇数人数时）
                matches.append({
                    "round": round_num,
                    "match_id": len(matches) + 1,
                    "contestant1": current_round[i],
                    "contestant2": "（轮空）",
                    "winner": current_round[i],
                    "score1": "自动晋级",
                    "score2": "-"
                })

        rounds.append({
            "round_number": round_num,
            "round_name": f"第{round_num}轮（{len(current_round)}进{len(current_round)//2}）",
            "matches": matches
        })

        # 准备下一轮
        next_round = []
        for m in matches:
            if m["winner"]:
                next_round.append(m["winner"])
            else:
                next_round.append(f"第{m['match_id']}场胜者")
        current_round = next_round
        round_num += 1

    return rounds


def save_tournament_data(
    roles: Dict,
    questions: List[Dict],
    bracket: List[Dict],
    output_dir: str
):
    """
    保存比赛数据到 memory 目录
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. 比赛信息
    info_md = f"""# 第 1 届雄辩天下杯 · 比赛信息

**举办时间**: [待填写]
**参赛规模**: {len(roles['contestants'])} 人
**评委人数**: {len(roles['judges'])} 人
**观众人数**: {len(roles['audience'])} 人
**辩论题目数**: {len(questions)} 题
**总比赛场次**: {sum(len(r['matches']) for r in bracket)} 场
**冠军**: [待产生]

---

## 角色分配

| 角色 | 人数 | 说明 |
|------|------|------|
| 主持人 | |