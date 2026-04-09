---
name: agent-memory-robustness-auditor
description: "Agent 记忆系统鲁棒性量化评估工具 (MRS)。基于黑盒模糊测试与对抗注入，验证系统在记忆污染、时序错乱、图谱断裂等极端场景下的生存能力。"
version: "1.0.0"
author: "Jarvis"
created: "2026-04-09"
metadata:
  category: "testing"
  tags: ["robustness", "testing", "auditing", "mrs"]
  requires: ["python3"]
  related_skills: ["agent-memory-dna-v5"]
---

# 🛡️ Agent Memory Robustness Auditor

**The "Virtual Proving Ground" for Agent Memories.**
> 就像特斯拉用仿真测试验证自动驾驶模型一样，本 Skill 用于验证记忆系统在对抗环境下的鲁棒性。

## 🎯 核心目标

在 v5 发版或重大升级前，自动执行 **Corner Case 注入测试**，输出量化的 **MRS (Memory Robustness Score)** 指标。
*   **MRS ≥ 99.9**：系统坚如磐石，准予发布。
*   **MRS < 90**：存在崩溃风险，禁止进入生产环境。

## 🧪 测试维度 (基于控制论与第一性原理)

本引擎通过沙盒隔离，对记忆数据进行**不可逆破坏**，并观察系统的反应：

1.  **完整性 (Integrity)**：
    *   **攻击**: 随机翻转图谱边方向（因果倒置）。
    *   **标准**: 系统应识别路径断裂或返回空，而非返回错误路径。
2.  **稳定性 (Stability)**：
    *   **攻击**: 截断 JSON 文件、注入非法字符。
    *   **标准**: 系统应捕获异常并报错（Graceful Degradation），绝不 Crash (Traceback)。
3.  **可用性 (Availability)**：
    *   **攻击**: 物理删除关键节点文件。
    *   **标准**: 系统应提示 "Not Found" 或触发降级策略，而非阻塞挂起。
4.  **时序鲁棒性**:
    *   **攻击**: 打乱 Event Log 时间戳。
    *   **标准**: 溯源系统应能识别异常或拒绝处理时序错乱的日志。

## 🚀 使用方法

### 快速运行 (CLI)

```bash
# 针对本地 v5 运行审计
python bin/mrs_auditor.py \
  --target /path/to/agent-memory-dna-v5 \
  --data /path/to/agent-memory-dna-v5/data
```

### 参数说明

*   `--target`: v5 代码根目录（包含 `bin/memory_cli.py`）。
*   `--data`: v5 数据目录（包含 `nodes/`, `edges/` 等）。**脚本会自动复制到沙盒，不会破坏原数据。**

## 📊 MRS 评分标准

MRS 是加权后的综合得分：

| 严重等级 | 权重 | 含义 |
| :--- | :--- | :--- |
| **Critical** | 1.0 | 核心节点丢失、数据损坏 |
| **High** | 0.8 | 图谱断裂、时序错乱 |
| **Medium** | 0.5 | 边缘属性缺失、格式微瑕 |

## 🔧 扩展测试用例

在 `cases/corner_cases.json` 中添加新的攻击模式：

```json
{
  "test_cases": [
    {
      "id": "custom_attack_001",
      "name": "注入超大节点",
      "method": "inject_huge_node",
      "severity": "high"
    }
  ]
}
```
然后在 `bin/mrs_auditor.py` 中实现对应的 `inject_huge_node` 方法。

---

**维护者**: 系统架构组
**版本**: 1.0.0
**关联项目**: Agent Memory DNA v5
