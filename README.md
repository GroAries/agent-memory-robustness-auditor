# 🛡️ Agent Memory Robustness Auditor (MRS)

**The "Virtual Proving Ground" for Agent Memories.**

> Like Tesla uses simulation to validate autonomous driving models, MRS uses adversarial injection to verify Agent Memory survival under extreme conditions.

---

## 🎯 What is MRS?

**MRS (Memory Robustness Score)** is a quantitative metric to evaluate the stability, integrity, and availability of Agent Memory systems.

Instead of just testing if "it works when data is good," MRS tests **how the system fails when data is corrupted, missing, or chaotic.**

### Key Metrics
*   **Integrity**: Does the system reject invalid inputs? (Weight: 40%)
*   **Stability**: Does the system crash under pressure? (Weight: 40%)
*   **Availability**: Does the fallback strategy work? (Weight: 20%)

---

## 🧪 Test Dimensions (Corner Cases)

The auditor creates an isolated **Sandbox**, clones your memory data, and performs destructive tests:

| Attack Vector | Severity | Description | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **Edge Flip** | High | Reverses graph direction (A→B becomes B→A). | Detect path break or return empty (No crash). |
| **Timestamp Chaos** | High | Shuffles log timestamps randomly. | Handle out-of-order events gracefully. |
| **Node Deletion** | Critical | Physically deletes a critical L1 node. | Return "Not Found" (No implicit hallucination). |
| **JSON Corruption** | High | Truncates a node file mid-sentence. | Catch JSON error (No Traceback crash). |

---

## 🚀 Quick Start

### 1. Installation
Clone the repository:
```bash
git clone https://github.com/GroAries/agent-memory-robustness-auditor.git
cd agent-memory-robustness-auditor
```

### 2. Run Audit (CLI)
Target your Agent Memory system (e.g., Agent Memory DNA v5):

```bash
python bin/mrs_auditor.py \
  --target /path/to/agent-memory-code \
  --data /path/to/agent-memory-data
```

### 3. CI/CD Integration
Use it in your CI pipeline. The script returns **Exit Code 1** if the score is too low.

```bash
if ! python bin/mrs_auditor.py --target ./v5 --data ./v5/data; then
  echo "❌ MRS Score too low! Aborting release."
  exit 1
fi
```

---

## 📊 MRS Score Card

| Score | Rating | Action |
| :--- | :--- | :--- |
| **99.9 - 100** | 🏆 **EXCELLENT** | Safe for Production. |
| **90.0 - 99.8** | ⚠️ **GOOD** | Optimize handling of specific errors. |
| **< 90.0** | ❌ **POOR** | **BLOCK RELEASE.** System is unstable. |

---

## 🧬 Architecture

1.  **Sandbox Engine**: Uses Python `tempfile` to create an ephemeral environment.
2.  **Injection Module**: Modifies JSON, logs, and graph files safely in the sandbox.
3.  **Observer**: Runs your system's CLI in the sandbox and analyzes `stdout`/`stderr` for crashes or logical errors.

---

**Version**: 1.0.0
**License**: MIT
**Related Project**: [Agent Memory DNA v5](https://github.com/GroAries/agent-memory-dna-v5)
