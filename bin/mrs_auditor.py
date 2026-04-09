#!/usr/bin/env python3
"""
MRS Auditor - Memory Robustness Score (MRS) 评估引擎
====================================================

模拟自动驾驶的“虚拟试车场” (Virtual Proving Ground)。
通过沙盒隔离、对抗注入、黑盒调用，量化评估记忆系统的鲁棒性。

核心指标 (MRS 0-100):
- 完整性 (Integrity): 系统能否拒绝非法输入？ (权重 40%)
- 稳定性 (Stability): 系统在异常下是否崩溃？ (权重 40%)
- 可用性 (Availability): 降级策略是否生效？ (权重 20%)

Usage:
    python bin/mrs_auditor.py --target <path_to_v5_code> --data <path_to_v5_data>
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import random
import time
import glob
from dataclasses import dataclass, field

@dataclass
class TestResult:
    case_id: str
    name: str
    severity: str  # critical, high, medium
    status: str    # passed, failed, crashed
    details: str = ""
    score_impact: float = 0.0

class MRSAuditor:
    def __init__(self, v5_path: str, data_path: str):
        self.v5_path = v5_path
        self.data_path = data_path
        self.sandbox = None
        self.results = []
        self.cli_path = os.path.join(v5_path, "bin", "memory_cli.py")
        
    def setup_sandbox(self):
        """创建沙盒环境，确保测试不污染生产数据"""
        self.sandbox = tempfile.mkdtemp(prefix=f"mrs_sandbox_{int(time.time())}_")
        
        # 1. 复制代码目录 (bin) -> 确保 CLI 运行时能找到相对路径下的 data
        sandbox_bin = os.path.join(self.sandbox, "bin")
        shutil.copytree(os.path.join(self.v5_path, "bin"), sandbox_bin)
        
        # 2. 复制数据目录 (data) -> 用于破坏测试
        sandbox_data = os.path.join(self.sandbox, "data")
        shutil.copytree(self.data_path, sandbox_data)
        
        # 更新 CLI 路径指向沙盒
        self.cli_path = os.path.join(sandbox_bin, "memory_cli.py")
        
        print(f"✅ 沙盒已创建: {self.sandbox}")
        print(f"🔒 代码已隔离: {sandbox_bin}")
        return sandbox_data

    def cleanup(self):
        """清理沙盒"""
        if self.sandbox and os.path.exists(self.sandbox):
            shutil.rmtree(self.sandbox)
            print(f"🧹 沙盒已清理: {self.sandbox}")

    def run_cli(self, *args, cwd=None):
        """在黑盒中运行 v5 CLI 命令"""
        # 强制使用沙盒环境（如果 CLI 依赖相对路径）
        if not cwd:
            cwd = self.sandbox
            
        cmd = [sys.executable, self.cli_path] + list(args)
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10,
                cwd=cwd
            )
            return {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "crashed": False
            }
        except subprocess.TimeoutExpired:
            return {"return_code": -1, "stdout": "", "stderr": "TIMEOUT", "crashed": True}
        except Exception as e:
            return {"return_code": -1, "stdout": "", "stderr": str(e), "crashed": True}

    def inject_flip_edges(self, sandbox_data: str) -> TestResult:
        """Case 1: 攻击图谱 - 随机翻转边的方向 (破坏因果性)"""
        edges_file = os.path.join(sandbox_data, "edges", "edges.json")
        if not os.path.exists(edges_file):
            return TestResult("flip_edges", "翻转边方向", "medium", "skipped", "无 edges.json")

        try:
            with open(edges_file, 'r') as f:
                data = json.load(f)
            
            # v5 edges.json 是 dict: {"EDGE-001": {...}, ...}
            edge_list = list(data.values())
            
            if len(edge_list) > 3:
                # 翻转前 3 条边
                flip_count = 0
                for edge_id, edge_data in data.items():
                    if flip_count >= 3: break
                    src, tgt = edge_data.get("source", ""), edge_data.get("target", "")
                    edge_data["source"], edge_data["target"] = tgt, src
                    flip_count += 1
                
                with open(edges_file, 'w') as f:
                    json.dump(data, f, indent=2)

                # 验证：尝试查询被修改的路径
                # 获取最后一条被翻转的边的 target (原 source)
                target_node = edge_list[2].get("source")
                
                res = self.run_cli("edge", "query", "--from", target_node)
                
                status = "crashed" if res["crashed"] or "Traceback" in res["stderr"] else "passed"
                return TestResult("flip_edges", "翻转边方向", "high", status, f"翻转了 {flip_count} 条边")
            
            return TestResult("flip_edges", "翻转边方向", "medium", "skipped", "边数量不足")

        except Exception as e:
            return TestResult("flip_edges", "翻转边方向", "high", "crashed", str(e))

    def inject_timestamp_chaos(self, sandbox_data: str) -> TestResult:
        """Case 2: 时序攻击 - 随机打乱日志时间戳"""
        logs_dir = os.path.join(sandbox_data, "logs")
        if not os.path.exists(logs_dir):
            return TestResult("timestamp_chaos", "时序错乱", "medium", "skipped", "无 logs")

        try:
            log_files = glob.glob(os.path.join(logs_dir, "*.jsonl"))
            if log_files:
                target_log = random.choice(log_files)
                with open(target_log, 'r') as f:
                    lines = f.readlines()
                
                if len(lines) > 2:
                    # 随机交换两行的内容 (保持行格式但破坏时间顺序)
                    # 注意：实际攻击应修改 json 内部的时间戳字段，这里简化为交换行
                    i, j = random.sample(range(len(lines)), 2)
                    lines[i], lines[j] = lines[j], lines[i]
                    
                    with open(target_log, 'w') as f:
                        f.writelines(lines)
                    
                    res = self.run_cli("trace", "--node", "STRATEGY") # 尝试触发溯源
                    status = "crashed" if res["crashed"] or "Traceback" in res["stderr"] else "passed"
                    return TestResult("timestamp_chaos", "时序错乱", "high", status, res["stderr"][:100])
            
            return TestResult("timestamp_chaos", "时序错乱", "medium", "skipped", "日志内容不足")
        except Exception as e:
            return TestResult("timestamp_chaos", "时序错乱", "high", "crashed", str(e))

    def inject_missing_node(self, sandbox_data: str) -> TestResult:
        """Case 3: 缺失测试 - 故意删除一个关键节点文件"""
        nodes_dir = os.path.join(sandbox_data, "nodes")
        if not os.path.exists(nodes_dir):
            return TestResult("missing_node", "节点缺失", "medium", "skipped", "无 nodes")

        try:
            node_files = glob.glob(os.path.join(nodes_dir, "*.json"))
            # 过滤掉 CONFIG/RULE 等系统节点，只删普通节点
            safe_files = [f for f in node_files if "CONFIG" not in os.path.basename(f) and "RULE" not in os.path.basename(f)]
            
            if safe_files:
                victim = random.choice(safe_files)
                victim_id = os.path.basename(victim).replace(".json", "")
                
                # 删除文件
                os.remove(victim)
                
                # 验证：查询被删节点，系统应返回 "Not Found" 而不是 Crash
                res = self.run_cli("node", "query", "--id", victim_id)
                
                # 期望：return_code 0 且 stdout 包含 "Not found" 或类似提示
                # 如果 return_code != 0 且 stderr 有 traceback，则 Crash
                if res["crashed"] or "Traceback" in res["stderr"]:
                    status = "crashed"
                elif "not found" in res["stdout"].lower() or res["return_code"] != 0:
                    status = "passed" # 正确识别了缺失
                else:
                    status = "failed" # 居然返回了数据？(缓存污染？)
                
                return TestResult("missing_node", "节点缺失", "critical", status, res["stdout"][:100])

            return TestResult("missing_node", "节点缺失", "medium", "skipped", "无安全节点可删")
        except Exception as e:
            return TestResult("missing_node", "节点缺失", "critical", "crashed", str(e))

    def inject_corrupt_json(self, sandbox_data: str) -> TestResult:
        """Case 4: 数据污染 - 截断节点 JSON 文件"""
        nodes_dir = os.path.join(sandbox_data, "nodes")
        if not os.path.exists(nodes_dir):
            return TestResult("corrupt_json", "JSON 截断", "medium", "skipped", "无 nodes")

        try:
            node_files = glob.glob(os.path.join(nodes_dir, "*.json"))
            if node_files:
                victim = random.choice(node_files)
                victim_id = os.path.basename(victim).replace(".json", "")
                
                # 截断文件
                with open(victim, 'r+') as f:
                    content = f.read()
                    if len(content) > 20:
                        f.seek(20)
                        f.truncate()
                
                res = self.run_cli("node", "query", "--id", victim_id)
                
                # 期望：Graceful Error (e.g. "Invalid JSON")
                status = "crashed" if res["crashed"] or "Traceback" in res["stderr"] else "passed"
                return TestResult("corrupt_json", "JSON 截断", "high", status, res["stderr"][:100])

            return TestResult("corrupt_json", "JSON 截断", "medium", "skipped", "节点文件不足")
        except Exception as e:
            return TestResult("corrupt_json", "JSON 截断", "high", "crashed", str(e))

    def calculate_mrs(self) -> float:
        """计算 Memory Robustness Score (0-100)"""
        if not self.results:
            return 0.0

        total_score = 0.0
        max_possible_score = 0.0

        for r in self.results:
            if r.status == "skipped":
                continue
                
            # 权重映射
            weight = {"critical": 1.0, "high": 0.8, "medium": 0.5}.get(r.severity, 0.5)
            max_possible_score += weight
            
            if r.status == "passed":
                total_score += weight
            elif r.status == "failed":
                total_score += weight * 0.2  # 失败但没崩溃，给点辛苦分
            else:
                total_score += 0.0  # 崩溃，0 分

        if max_possible_score == 0:
            return 100.0

        return (total_score / max_possible_score) * 100

    def run_audit(self):
        """执行完整审计流程"""
        print("🚀 开始 MRS 鲁棒性审计...")
        sandbox_data = self.setup_sandbox()
        
        try:
            # 运行测试集
            self.results.append(self.inject_flip_edges(sandbox_data))
            self.results.append(self.inject_timestamp_chaos(sandbox_data))
            self.results.append(self.inject_missing_node(sandbox_data))
            self.results.append(self.inject_corrupt_json(sandbox_data))
            
            # 计算分数
            mrs = self.calculate_mrs()
            
            # 输出报告
            print("\n" + "="*50)
            print("📊 MRS 鲁棒性审计报告")
            print("="*50)
            print(f"🎯 Memory Robustness Score: {mrs:.1f} / 100")
            
            if mrs >= 99.9:
                print("✅ 评级: EXCELLENT (准予发布)")
            elif mrs >= 90:
                print("⚠️ 评级: GOOD (建议优化)")
            else:
                print("❌ 评级: POOR (禁止发布)")
                
            print("\n📝 测试详情:")
            for r in self.results:
                icon = {"passed": "✅", "failed": "⚠️", "crashed": "❌", "skipped": "⏭️"}.get(r.status, "?")
                print(f"  {icon} [{r.severity.upper()}] {r.name}: {r.status} - {r.details}")
            
            print("="*50)
            
            return mrs

        finally:
            self.cleanup()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MRS Memory Robustness Auditor")
    parser.add_argument("--target", required=True, help="Path to v5 code (contains bin/memory_cli.py)")
    parser.add_argument("--data", required=True, help="Path to v5 data directory")
    args = parser.parse_args()
    
    auditor = MRSAuditor(args.target, args.data)
    score = auditor.run_audit()
    
    # 返回非 0 退出码以便 CI 使用
    if score < 90:
        sys.exit(1)
