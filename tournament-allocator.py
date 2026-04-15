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
from datetime import datetime


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
            if not line:
                in_table = False
                header_parsed = False
                continue

            if '|' not in line:
                in_table = False
                header_parsed = False
                continue

            cols = [c.strip() for c in line.split('|')]
            cols = [c for c in cols if c or cols.index(c) not in (0, len(cols)-1)]

            # 跳过分隔行
            if all(re.match(r'^[-:]+$', c) for c in cols if c):
                continue

            # 解析表头
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
        # 纯文本格式
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
        num_contestants = min(num_contestants, max(2, total - 1 - num_judges))
        num_judges = min(num_judges, total - 1 - num_contestants)
        print(f"   自动调整: 参赛者 {num_contestants} 人，评委 {num_judges} 人")

    shuffled = random.sample(philosophers, total)
    idx = 0

    host = shuffled[idx]
    idx += 1

    contestants = shuffled[idx:idx + num_contestants]
    idx += num_contestants

    judges = shuffled[idx:idx + num_judges]
    idx += num_judges

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
    """
    assigned = []
    for i, person in enumerate(audience):
        if i < len(questions):
            assigned.append({
                'id': i + 1,
                'question': questions[i]['question'],
                'contributor': person
            })
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
                matches.append({
                    "round": round_num,
                    "match_id": len(matches) + 1,
                    "contestant1": current_round[i],
                    "contestant2": current_round[i + 1],
                    "winner": None,
                    "score1": None,
                    "score2": None
                })
            else:
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
    output_dir: str,
    tournament_name: str = "第 1 届雄辩天下杯"
):
    """
    保存比赛数据到 memory 目录
    生成：比赛信息.md、角色分配.md、题目池.md、对阵图.md
    """
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    # ========== 1. 比赛信息.md ==========
    total_matches = sum(len(r['matches']) for r in bracket)
    info_md = f"""# {tournament_name} · 比赛信息

**举办时间**: {today}
**参赛规模**: {len(roles['contestants'])} 人
**评委人数**: {len(roles['judges'])} 人
**观众人数**: {len(roles['audience'])} 人
**辩论题目数**: {len(questions)} 题
**总比赛场次**: {total_matches} 场
**冠军**: [待产生]

---

## 角色分配

| 角色 | 人数 | 说明 |
|------|------|------|
| 主持人 | {len(roles['host'])} | 掌控全场，不参赛，不出题 |
| 参赛者 | {len(roles['contestants'])} | 参加辩论，不出题 |
| 评委 | {len(roles['judges'])} | 打分投票，不出题 |
| 观众 | {len(roles['audience'])} | 出题 + 投票 |

**角色互斥**: ✅ 每人仅担任一个角色
**出题限制**: ✅ 仅观众可出题
"""
    with open(os.path.join(output_dir, "比赛信息.md"), 'w', encoding='utf-8') as f:
        f.write(info_md)

    # ========== 2. 角色分配.md ==========
    roles_md = f"# {tournament_name} · 角色分配\n\n"

    roles_md += f"## 主持人（{len(roles['host'])} 人）\n"
    roles_md += "| # | 姓名 |\n|---|------|\n"
    for i, h in enumerate(roles['host']):
        roles_md += f"| {i+1} | {h} |\n"

    roles_md += f"\n## 参赛者（{len(roles['contestants'])} 人）\n"
    roles_md += "| # | 姓名 | 编号 |\n|---|------|------|\n"
    for i, c in enumerate(roles['contestants']):
        roles_md += f"| {i+1} | {c} | {i+1:02d} |\n"

    roles_md += f"\n## 评委（{len(roles['judges'])} 人）\n"
    roles_md += "| # | 姓名 |\n|---|------|\n"
    for i, j in enumerate(roles['judges']):
        roles_md += f"| {i+1} | {j} |\n"

    roles_md += f"\n## 观众（{len(roles['audience'])} 人，出题人）\n"
    roles_md += "| # | 姓名 |\n|---|------|\n"
    for i, a in enumerate(roles['audience']):
        roles_md += f"| {i+1} | {a} |\n"

    with open(os.path.join(output_dir, "角色分配.md"), 'w', encoding='utf-8') as f:
        f.write(roles_md)

    # ========== 3. 题目池.md ==========
    questions_md = f"# {tournament_name} · 题目池\n\n"
    questions_md += f"**总题目数**: {len(questions)} 题\n\n"
    questions_md += "**出题规则**: 仅观众可出题，参赛者与评委不得出题\n\n"
    questions_md += "| # | 题目 | 贡献者 |\n|---|------|--------|\n"
    for q in questions:
        questions_md += f"| {q['id']} | {q['question']} | {q['contributor']} |\n"

    with open(os.path.join(output_dir, "题目池.md"), 'w', encoding='utf-8') as f:
        f.write(questions_md)

    # ========== 4. 对阵图.md ==========
    bracket_md = f"# {tournament_name} · 对阵图\n\n**赛制**: 单败淘汰\n\n"
    for round_data in bracket:
        bracket_md += f"## {round_data['round_name']}\n\n"
        bracket_md += "| 场次 | 对阵 | 获胜者 | 比分 |\n"
        bracket_md += "|------|------|--------|------|\n"
        for m in round_data['matches']:
            winner = m['winner'] or '待决'
            s1 = m['score1'] or '-'
            s2 = m['score2'] or '-'
            bracket_md += f"| 第{m['match_id']}场 | {m['contestant1']} vs {m['contestant2']} | {winner} | {s1}:{s2} |\n"
        bracket_md += "\n"

    with open(os.path.join(output_dir, "对阵图.md"), 'w', encoding='utf-8') as f:
        f.write(bracket_md)

    # ========== 5. 创建比赛记录目录 ==========
    for round_data in bracket:
        round_dir = os.path.join(output_dir, "比赛记录", f"第{round_data['round_number']}轮")
        os.makedirs(round_dir, exist_ok=True)

    # ========== 6. 保存 JSON 数据（供程序读取） ==========
    data = {
        "tournament_name": tournament_name,
        "date": today,
        "roles": roles,
        "questions": questions,
        "bracket": [
            {
                "round_number": r["round_number"],
                "round_name": r["round_name"],
                "matches": r["matches"]
            }
            for r in bracket
        ]
    }
    with open(os.path.join(output_dir, "tournament-data.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_dir


# ========== 主程序 ==========
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="雄辩天下杯赛 - 角色分配脚本")
    parser.add_argument("--registry", default="references/philosopher-registry.md",
                        help="哲学家注册表路径 (默认: references/philosopher-registry.md)")
    parser.add_argument("--questions", default=None,
                        help="观众题目文件路径 (可选，不提供则无题目池)")
    parser.add_argument("--contestants", type=int, default=32,
                        help="参赛者人数 (默认: 32)")
    parser.add_argument("--judges", type=int, default=20,
                        help="评委人数 (默认: 20)")
    parser.add_argument("--output", default="memory/philosophy-dialogues/tournaments",
                        help="输出目录 (默认: memory/philosophy-dialogues/tournaments)")
    parser.add_argument("--name", default="第 1 届雄辩天下杯",
                        help="比赛名称 (默认: 第 1 届雄辩天下杯)")
    parser.add_argument("--seed", type=int, default=None,
                        help="随机种子 (可选，用于复现)")
    args = parser.parse_args()

    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
        print(f"🎲 随机种子: {args.seed}")

    # 1. 加载哲学家
    print(f"📖 读取注册表: {args.registry}")
    philosophers = load_philosophers(args.registry)
    print(f"   共 {len(philosophers)} 位哲学家")

    if len(philosophers) == 0:
        print("❌ 未读取到任何哲学家，请检查注册表文件格式")
        sys.exit(1)

    # 2. 分配角色
    print(f"\n🎭 分配角色（参赛: {args.contestants}，评委: {args.judges}）...")
    roles = allocate_roles(philosophers, args.contestants, args.judges)
    print(f"   主持人: {roles['host'][0]}")
    print(f"   参赛者: {len(roles['contestants'])} 人")
    print(f"   评委: {len(roles['judges'])} 人")
    print(f"   观众: {len(roles['audience'])} 人")

    # 3. 加载题目
    questions = []
    if args.questions:
        print(f"\n📝 读取题目: {args.questions}")
        raw_questions = load_questions(args.questions)
        questions = assign_questions_to_audience(roles['audience'], raw_questions)
        print(f"   共 {len(questions)} 题（分配给观众）")
    else:
        print(f"\n📝 未指定题目文件，跳过题目池生成")

    # 4. 生成对阵图
    print(f"\n⚔️ 生成对阵图...")
    bracket = generate_bracket(roles['contestants'])
    total_matches = sum(len(r['matches']) for r in bracket)
    print(f"   共 {len(bracket)} 轮，{total_matches} 场比赛")

    # 5. 保存数据
    print(f"\n💾 保存数据到: {args.output}")
    save_tournament_data(roles, questions, bracket, args.output, args.name)

    # 6. 输出摘要
    print(f"\n{'='*50}")
    print(f"✅ {args.name} 初始化完成！")
    print(f"{'='*50}")
    print(f"   主持人: {roles['host'][0]}")
    print(f"   参赛者: {len(roles['contestants'])} 人")
    print(f"   评委: {len(roles['judges'])} 人")
    print(f"   观众: {len(roles['audience'])} 人")
    print(f"   题目: {len(questions)} 题")
    print(f"   比赛: {total_matches} 场")
    print(f"\n📁 生成文件:")
    print(f"   {args.output}/比赛信息.md")
    print(f"   {args.output}/角色分配.md")
    print(f"   {args.output}/题目池.md")
    print(f"   {args.output}/对阵图.md")
    print(f"   {args.output}/tournament-data.json")
    print(f"   {args.output}/比赛记录/第1轮/ ~ 第{len(bracket)}轮/")
    print(f"\n🎯 下一步: 开始第 1 轮第 1 场比赛！")
