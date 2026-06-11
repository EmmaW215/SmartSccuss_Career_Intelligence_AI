# Phase 2 Agent Tools — 完成状态与验收证据

> 对应 PRD: `02_PHASE2_AGENT_TOOLS.md`（Step C 验收证据 → Step D 预发布演练 → Step E MCP parity）
>
> 注意：本仓库（GitHub）此前不包含本地 `PHASE2_PCodingPlace_20260611/source` 中的 agent-tools 代码，
> 因此本次按 PRD 在 `smartsuccess-interview-backend` 内完整实现了 agent tools 层 + 全部验收项。
> 如果你本地 iCloud 已有另一份实现，请以合并时间较新者为准进行对照。

---

## 架构总览

```
app/agent/
├── tools.py              # AgentToolkit：4 个直连工具（永不抛异常，返回 ok/error payload）
│                         #   search_question_bank / score_answer /
│                         #   get_candidate_profile / save_interview_note
├── registry.py           # ToolRegistry：OpenAI function-calling schema + 安全执行
├── interviewer_agent.py  # AgentInterviewer：agent loop（self-healing + tool_call_log）
│                         # write_tool_call_log：Step D 证据文件输出
├── scripted_chat.py      # 离线脚本化 LLM（测试 + 无 key 时的演练）
└── mcp_server.py         # MCP server（Step E，与直连工具同名同行为）
```

**开关（默认全部关闭，Phase 1 行为完全不变）：**

| 环境变量 | 默认 | 作用 |
|---|---|---|
| `USE_AGENT_TOOLS` | `false` | `true` 时面试轮次走 agent loop（出错自动回退 Phase 1） |
| `USE_MCP_TOOLS` | `false` | `true` 时提示启动 MCP server（`python -m app.agent.mcp_server`） |
| `AGENT_MAX_TOOL_ITERATIONS` | `6` | 每轮 LLM↔tool 循环上限 |
| `TOOL_CALL_LOG_DIR` | `data/tool_call_logs` | 每轮 tool_call_log JSON 输出目录 |

**接入点：** `app/interview/base_interview.py::_handle_interview_response` —
flag 为 true 时调用 `_handle_agent_round()`；任何异常都会落回原 Phase 1 流程（优雅降级）。

**每轮硬性保证（PRD 验收标准）：**
1. tool_call_log 至少含一次成功的 `score_answer`（LLM 漏调时由 agent 强制补调，标记 `enforced: true`）
2. 每条 tool call 记录都带 `decision`（决策链），`decision_chain` 全程可追溯
3. tool 报错不会中断面试：错误以 `{"ok": false, "error": ...}` 回灌给 LLM 继续；
   LLM 整体不可用时从题库取下一题兜底（`used_fallback: true`）

---

## ✅ Step C — 验收证据（3 项 PRD 测试已补齐）

PRD 要求的 3 个 `@pytest.mark.llm` 场景，见 `tests/test_llm_integration.py`：

1. **真实 LLM 集成测试** — `test_real_llm_scripted_round`：脚本化一轮真实 interviewer
2. **tool 报错 → agent 继续提问** — `test_real_llm_self_heals_after_tool_error`：self-healing E2E
3. **每轮至少含 score_answer + 决策链** — `test_real_llm_log_quality_statistics`：tool_call_log 质量统计断言

手动运行（需要真实 OpenAI API key，约 $0.05/次）：

```bash
cd smartsuccess-interview-backend
OPENAI_API_KEY=sk-... pytest -m llm tests/test_llm_integration.py -v
```

默认 `pytest` 运行**不**包含这 3 个测试（`pytest.ini: addopts = -m "not llm"`），无 key 时自动 skip。

同时每个场景都有**离线（mock LLM）版本**，常驻 CI：

| 离线测试 | 对应 PRD 场景 |
|---|---|
| `test_agent_interviewer.py::TestSelfHealingLoop::test_tool_error_fed_back_and_round_completes` | tool 报错 → agent 继续提问 |
| `test_agent_interviewer.py::TestToolCallLogQuality::test_statistics_every_round_has_score_and_decisions` | 每轮 score_answer + 决策链统计 |
| `test_agent_interviewer.py::TestHappyPath::*` | 脚本化一轮 interviewer |

**当前测试结果（本仓库实测，2026-06-11）：**

```
pytest tests/ → 55 passed, 3 deselected (llm)
  test_api.py               11  (原 Phase 1 回归，全部保留)
  test_agent_tools.py       24  (toolkit + registry 单测)
  test_agent_interviewer.py  9  (agent loop / self-healing / log 质量)
  test_agent_regression.py   5  (flag on/off 回归)
  test_mcp_parity.py         6  (Step E parity)
```

---

## ✅ Step D — 预发布演练

### 1. `USE_AGENT_TOOLS=false` 全量回归（Phase 1 行为完全恢复）

```bash
USE_AGENT_TOOLS=false pytest tests/  →  55 passed, 3 deselected
```

代码级证明（`tests/test_agent_regression.py`）：
- `test_default_flags_are_off` — 两个 flag 默认值均为 `false`
- `test_phase1_flow_never_touches_agent` — flag 关闭时 `AgentInterviewer.run_round`
  被 monkeypatch 成必炸断言，整轮 `process_message` 照常完成 ⇒ agent 代码零参与

### 2. `USE_AGENT_TOOLS=true` staging 演练

```bash
USE_AGENT_TOOLS=true USE_MCP_TOOLS=true uvicorn app.main:app
# 启动日志：
# 🤖 Agent tools ENABLED (USE_AGENT_TOOLS=true) — tool_call_logs → data/tool_call_logs
# 🔌 MCP tools flag set (USE_MCP_TOOLS=true) — run: python -m app.agent.mcp_server
# /health → 200 healthy；/api/interview/screening/start → 200
```

### 3. 三份 tool_call_log 样本（简历证据）

```bash
python scripts/collect_tool_call_logs.py            # 输出到 docs/phase2_evidence/
```

已生成并入库：`docs/phase2_evidence/step_d_staging_scripted_mock_round{1,2,3}.json`
（每份含完整 tool_calls、decision_chain、score_answer 结果、latency）。

⚠️ 当前样本为 `"mode": "scripted_mock"`（云端环境无真实 OPENAI_API_KEY）。
**拿真实样本只需一条命令**（脚本自动切换 `real_llm` 模式，约 $0.05）：

```bash
OPENAI_API_KEY=sk-... python scripts/collect_tool_call_logs.py
```

生成的文件 `mode` 字段会变为 `"real_llm"` —— 这才是给面试官看的最终版本，请在本地跑一次后覆盖提交。

---

## ✅ Step E — MCP parity（可选项，已完成代码与测试）

- `app/agent/mcp_server.py`：FastMCP server，工具与直连 ToolRegistry **同名同行为**
- `tests/test_mcp_parity.py`（7 个测试）：工具名集合、正常/错误 payload、
  `score_answer` 确定性结果、`call_tool` 全链路 — 全部与直连结果逐字段相等

Claude Desktop / Cursor 接入（demo 视频录制用）：

```json
{
  "mcpServers": {
    "smartsuccess-interview": {
      "command": "python",
      "args": ["-m", "app.agent.mcp_server"],
      "cwd": "/path/to/smartsuccess-interview-backend"
    }
  }
}
```

---

## 剩余的人工动作（需要你本机/真实 key）

| 动作 | 命令 | 耗时 |
|---|---|---|
| 跑 3 个真实 LLM 测试拿绿色截图 | `pytest -m llm tests/test_llm_integration.py -v` | ~2 分钟, ~$0.05 |
| 重新生成 real_llm 模式日志样本并提交 | `python scripts/collect_tool_call_logs.py` | ~1 分钟, ~$0.05 |
| （可选）录 Claude Desktop 连接 MCP server 的 demo | 上方 JSON 配置 | ~0.5 天 |

完成以上两条命令后，Phase 2 即全部收口，可进入 Phase 3（RAG 升级）。
