---
name: agent-memory-robustness-auditor
description: "Agent 记忆系统鲁棒性量化评估工具 v2.0 (MRS)。基于黑盒模糊测试与白盒插件注入，验证系统在记忆污染、时序错乱、图谱断裂及极端算法参数下的生存能力。"
version: "2.0.0"
author: "Jarvis"
created: "2026-04-10"
metadata:
  category: "testing"
  tags: ["robustness", "testing", "auditing", "mrs", "dual-mode"]
  requires: ["python3"]
  related_skills: ["agent-memory-dna-v5", "agent-memory-dna-synapse"]
---

# 🛡️ Agent Memory Robustness Auditor v2.0

**The "Virtual Proving Ground" for Agent Memories.**
> 就像特斯拉用仿真测试验证自动驾驶模型一样，本 Skill 用于验证记忆系统在对抗环境下的鲁棒性。
> **v2.0 核心升级：双模审计 (Dual-Mode Auditing)** - 结合**系统级黑盒攻击**与**算法级白盒插件扫描**。

## 🎯 核心目标

在记忆系统发版或重大升级前，自动执行 **Corner Case 注入测试**，输出量化的 **MRS (Memory Robustness Score)** 指标。
*   **MRS = 100**：系统坚如磐石 (System & Algorithm Stable)，准予发布 Stable。
*   **MRS ≥ 90**：系统存在轻微瑕疵，可标记为 Release Candidate。
*   **MRS < 90**：存在崩溃风险，禁止进入生产环境。

## 🧪 双模审计机制 (Dual-Mode Auditing)

### 1. 📦 黑盒系统级测试 (System-Level Blackbox)
*模拟环境灾难，测试系统架构的完整性。*
*   **完整性 (Integrity)**：随机翻转图谱边方向（因果倒置），验证路径检索是否安全拦截。
*   **稳定性 (Stability)**：截断 JSON 文件、注入非法字符，验证解析器是否 Graceful Degrade 而非 Crash。
*   **可用性 (Availability)**：物理删除关键节点文件，验证 `Not Found` 处理机制。

### 2. 🔬 白盒算法级测试 (Algorithm-Level Whitebox)
*动态扫描目标 `bin` 目录下的 `test_*_robustness.py` 脚本，进行极限参数攻击。*
*   **噪声注入 (Noise Injection)**：输入纯符号、乱码、空集，测试分词器与打分器的抗干扰能力。
*   **边界压力 (Stress Test)**：输入超长上下文 (50+ Keywords)、极大负载，测试内存与时间复杂度。
*   **数学异常 (Math Robustness)**：注入除零异常、几何平均零值，测试融合器逻辑。

## 🚀 使用方法

### CLI 运行 (标准用法)

```bash
# 针对目标记忆系统运行审计
# target: 代码目录 (含 bin/)
# data: 数据目录 (含 nodes/, edges/)
python bin/mrs_auditor.py \
  --target /path/to/agent-memory-system \
  --data /path/to/agent-memory-system/data
```

### 扩展白盒测试 (Whitebox Plugin)

只需在目标系统的 `bin/` 目录下添加符合命名规范的测试脚本即可：
*   **命名**: `test_*_robustness.py` (例如 `test_synapse_robustness.py`)
*   **机制**: MRS 会自动发现这些脚本，在隔离沙盒中运行它们，并解析输出中的 `CRASH` 或 `PASS` 关键词来判定算法鲁棒性。

## 📊 MRS 评分标准

MRS 是加权后的综合得分 (0-100)：

| 严重等级 | 权重 | 含义 |
| :--- | :--- | :--- |
| **Critical** | 1.0 | 核心节点丢失、数据结构损坏、算法模块 Crash |
| **High** | 0.8 | 图谱断裂、算法返回非法结果 |
| **Medium** | 0.5 | 边缘属性缺失、格式微瑕 |

## 📄 审计报告示例

```
==================================================
📊 MRS 审计报告
==================================================
🎯 最终得分: 100.0 / 100
✅ 评级: EXCELLENT (准予发布 Stable)

📝 详情:
  ✅ [HIGH] 翻转边方向 (系统级): passed
  ✅ [CRITICAL] 节点缺失 (系统级): passed
  ✅ [HIGH] 算法审计: test_synapse_robustness.py: passed
==================================================
```

---
**维护者**: 系统架构组
**版本**: 2.0.0
**关联项目**: Agent Memory DNA v5 (Synapse v5.2.2)