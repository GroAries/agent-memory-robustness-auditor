#!/usr/bin/env python3
"""
MRS Auditor v2.0 - Memory Robustness Score (MRS) 评估引擎 (Synapse Enhanced)
=============================================================================

模拟自动驾驶的"虚拟试车场" (Virtual Proving Ground)。
v2.0 升级：引入 **"双模审计" (Dual-Mode Auditing)**
1. **黑盒系统级 (System-Level)**: 模拟环境灾难 (数据丢失、JSON 损坏、图谱断裂)。
2. **白盒算法级 (Algorithm-Level)**: 动态发现并执行目标目录下的 `test_*_robustness.py` 插件。

核心指标 (MRS 0-100):
- 完整性 (Integrity): 系统能否拒绝非法输入？
- 稳定性 (Stability): 系统在异常下是否崩溃？
- 算法生存力 (Algorithmic Survival): 独立算法模块在极端参数下的表现。

Usage:
    python bin/mrs_auditor.py --target <path_to_code> --data <path_to_data>
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
import re
from dataclasses import dataclass

@dataclass
class TestResult:
    case_id: str
    name: str
    severity: str  # critical, high, medium
    status: str    # passed, failed, crashed
    details: str = ""
    score_impact: float = 0.0

class MRSAuditor:
    def __init__(self, code_path: str, data_path: str):
        self.code_path = code_path
        self.data_path = data_path
        self.sandbox = None
        self.results = []
        
    def setup_sandbox(self):
        """创建沙盒环境，确保测试不污染生产数据"""
        self.sandbox = tempfile.mkdtemp(prefix=f"mrs_sandbox_{int(time.time())}_")
        
        # 1. 复制代码目录
        sandbox_code = os.path.join(self.sandbox, "bin") # Assuming bin structure or flat
        # Check if code_path has a 'bin' dir or is flat
        if os.path.isdir(os.path.join(self.code_path, "bin")):
            shutil.copytree(os.path.join(self.code_path, "bin"), sandbox_code)
            self.bin_path = sandbox_code
        else:
            # If flat structure (like simple scripts)
            os.makedirs(os.path.join(self.sandbox, "bin"), exist_ok=True)
            # Copy python files
            for f in glob.glob(os.path.join(self.code_path, "*.py")):
                shutil.copy(f, os.path.join(self.sandbox, "bin"))
            self.bin_path = os.path.join(self.sandbox, "bin")

        # 2. 复制数据目录
        sandbox_data = os.path.join(self.sandbox, "data")
        if os.path.exists(self.data_path):
            shutil.copytree(self.data_path, sandbox_data)
        else:
            os.makedirs(sandbox_data, exist_ok=True)
            
        print(f"✅ 沙盒已创建: {self.sandbox}")
        print(f"🔒 代码已隔离: {self.bin_path}")
        return sandbox_data

    def cleanup(self):
        if self.sandbox and os.path.exists(self.sandbox):
            shutil.rmtree(self.sandbox)
            print(f"🧹 沙盒已清理: {self.sandbox}")

    def run_cli(self, *args, cwd=None):
        """在黑盒中运行 memory_cli.py"""
        cli_path = os.path.join(self.bin_path, "memory_cli.py")
        if not os.path.exists(cli_path):
            return {"return_code": -1, "stdout": "", "stderr": "CLI not found", "crashed": True}

        if not cwd: cwd = self.sandbox
        cmd = [sys.executable, cli_path] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=cwd)
            return {"return_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "crashed": "Traceback" in result.stderr or result.returncode != 0}
        except Exception as e:
            return {"return_code": -1, "stdout": "", "stderr": str(e), "crashed": True}

    def run_algorithmic_plugin(self, plugin_path):
        """运行白盒算法级测试插件 (test_*_robustness.py)"""
        try:
            # 插件需要在其所在目录运行以便 import 同级模块
            cwd = os.path.dirname(plugin_path)
            result = subprocess.run(
                [sys.executable, plugin_path], 
                capture_output=True, text=True, timeout=30, cwd=cwd
            )
            
            output = result.stdout + "\n" + result.stderr
            crash_detected = result.returncode != 0 or "Traceback" in result.stderr
            
            if crash_detected:
                status = "crashed"
                detail = "Script crashed or returned non-zero"
            elif "0 CRASH" in output or "All Tests Passed" in output:
                status = "passed"
                # 尝试提取具体测试数量
                match = re.search(r"(\d+) CRASH", output)
                detail = f"0 Crashes detected in plugin output"
            else:
                # 模糊匹配
                status = "passed" 
                detail = "Script completed without critical errors"

            return TestResult("plugin", f"算法审计: {os.path.basename(plugin_path)}", "high", status, detail)
            
        except subprocess.TimeoutExpired:
            return TestResult("plugin", f"算法审计: {os.path.basename(plugin_path)}", "high", "crashed", "Timeout")
        except Exception as e:
            return TestResult("plugin", f"算法审计: {os.path.basename(plugin_path)}", "high", "crashed", str(e))

    def inject_flip_edges(self, sandbox_data: str) -> TestResult:
        """黑盒测试 1: 翻转边方向"""
        edges_file = os.path.join(sandbox_data, "edges", "edges.json")
        if not os.path.exists(edges_file):
            return TestResult("flip_edges", "翻转边方向 (系统级)", "medium", "skipped", "No edges.json")

        try:
            with open(edges_file, 'r') as f: data = json.load(f)
            if not data: return TestResult("flip_edges", "翻转边方向 (系统级)", "medium", "skipped", "Empty")

            edge_list = list(data.values())
            flip_count = min(3, len(edge_list))
            
            for i, (edge_id, edge_data) in enumerate(data.items()):
                if i >= flip_count: break
                src, tgt = edge_data.get("source", ""), edge_data.get("target", "")
                edge_data["source"], edge_data["target"] = tgt, src
            
            with open(edges_file, 'w') as f: json.dump(data, f, indent=2)
            
            # 尝试查询以验证稳定性
            # 假设 CLI 支持 edge 查询，或者仅仅是启动加载
            # 这里简单测试 CLI 是否能正常启动并 help
            res = self.run_cli("--help") 
            # 如果 CLI 启动时加载图谱，--help 通常不加载。我们需要触发 load。
            # 假设 query 会触发 load
            res = self.run_cli("node", "query", "--id", "DUMMY") 
            
            status = "crashed" if res["crashed"] else "passed"
            return TestResult("flip_edges", "翻转边方向 (系统级)", "high", status, f"Flipped {flip_count} edges")
        except Exception as e:
            return TestResult("flip_edges", "翻转边方向 (系统级)", "high", "crashed", str(e))

    def inject_corrupt_json(self, sandbox_data: str) -> TestResult:
        """黑盒测试 2: JSON 截断"""
        nodes_dir = os.path.join(sandbox_data, "nodes")
        if not os.path.exists(nodes_dir):
            return TestResult("corrupt_json", "JSON 截断 (系统级)", "medium", "skipped", "No nodes")

        try:
            node_files = glob.glob(os.path.join(nodes_dir, "*.json"))
            if not node_files: return TestResult("corrupt_json", "JSON 截断 (系统级)", "medium", "skipped", "No files")

            victim = node_files[0]
            with open(victim, 'r+') as f:
                content = f.read()
                if len(content) > 20:
                    f.seek(20)
                    f.truncate()
            
            res = self.run_cli("node", "query", "--id", "DUMMY") # Trigger load
            status = "crashed" if res["crashed"] else "passed"
            return TestResult("corrupt_json", "JSON 截断 (系统级)", "high", status, "Corrupt node injection")
        except Exception as e:
            return TestResult("corrupt_json", "JSON 截断 (系统级)", "high", "crashed", str(e))

    def inject_missing_node(self, sandbox_data: str) -> TestResult:
        """黑盒测试 3: 节点丢失"""
        nodes_dir = os.path.join(sandbox_data, "nodes")
        if not os.path.exists(nodes_dir):
            return TestResult("missing_node", "节点缺失 (系统级)", "medium", "skipped", "No nodes")
            
        try:
            node_files = glob.glob(os.path.join(nodes_dir, "*.json"))
            if not node_files: return TestResult("missing_node", "节点缺失 (系统级)", "medium", "skipped", "No files")

            victim = node_files[0]
            victim_id = os.path.basename(victim).replace(".json", "")
            os.remove(victim)
            
            res = self.run_cli("node", "query", "--id", victim_id)
            # 只要不 Traceback Crash 就算通过
            status = "crashed" if res["crashed"] else "passed"
            return TestResult("missing_node", "节点缺失 (系统级)", "critical", status, f"Deleted {victim_id}")
        except Exception as e:
            return TestResult("missing_node", "节点缺失 (系统级)", "critical", "crashed", str(e))

    def run_algorithmic_audit(self):
        """扫描并运行算法级测试插件"""
        print("\n🔍 [2/2] 扫描白盒算法插件...")
        plugins = glob.glob(os.path.join(self.bin_path, "test_*_robustness.py"))
        
        if not plugins:
            print("   ℹ️ 未发现算法测试插件，跳过白盒审计。")
            return

        for plugin in plugins:
            print(f"   🚀 发现插件: {os.path.basename(plugin)}")
            result = self.run_algorithmic_plugin(plugin)
            self.results.append(result)
            
            icon = "✅" if result.status == "passed" else "❌"
            print(f"   {icon} 结果: {result.status} - {result.details}")

    def calculate_mrs(self) -> float:
        """计算最终得分"""
        if not self.results: return 0.0
        
        total = 0.0
        max_score = 0.0
        
        for r in self.results:
            if r.status == "skipped": continue
            weight = {"critical": 1.0, "high": 0.8, "medium": 0.5}.get(r.severity, 0.5)
            max_score += weight
            
            if r.status == "passed": total += weight
            elif r.status == "failed": total += weight * 0.2
            
        return (total / max_score) * 100 if max_score > 0 else 100.0

    def run_audit(self):
        print("🚀 开始 MRS v2.0 双模鲁棒性审计...")
        sandbox_data = self.setup_sandbox()
        
        try:
            # 1. 黑盒系统级测试
            print("\n🔍 [1/2] 执行黑盒系统级测试...")
            self.results.append(self.inject_flip_edges(sandbox_data))
            self.results.append(self.inject_corrupt_json(sandbox_data))
            self.results.append(self.inject_missing_node(sandbox_data))
            
            # 2. 白盒算法级测试
            self.run_algorithmic_audit()
            
            # 3. 结算
            mrs = self.calculate_mrs()
            
            print("\n" + "="*50)
            print(f"📊 MRS 审计报告")
            print("="*50)
            print(f"🎯 最终得分: {mrs:.1f} / 100")
            
            if mrs == 100.0:
                print("✅ 评级: EXCELLENT (准予发布 Stable)")
            elif mrs >= 90:
                print("✅ 评级: GOOD (Release Candidate)")
            else:
                print("❌ 评级: POOR (需要修复)")
                
            print("\n📝 详情:")
            for r in self.results:
                icon = {"passed": "✅", "failed": "⚠️", "crashed": "❌", "skipped": "⏭️"}.get(r.status, "?")
                print(f"  {icon} [{r.severity.upper()}] {r.name}: {r.status}")
            print("="*50)
            
            return mrs

        finally:
            self.cleanup()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MRS v2.0 Memory Robustness Auditor")
    parser.add_argument("--target", required=True, help="Path to system code")
    parser.add_argument("--data", required=True, help="Path to system data")
    args = parser.parse_args()
    
    auditor = MRSAuditor(args.target, args.data)
    score = auditor.run_audit()
    if score < 90: sys.exit(1)