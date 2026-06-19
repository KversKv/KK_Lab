# AI Eval 回归集（Phase 7）

把"已知坑"固化为"输入 → 期望行为"用例，改 prompt / nudges 前后跑一遍，防止修 A 坏 B。

## 用例格式（cases/*.json）

每个文件一条用例，字段如下：

```json
{
  "id": "唯一标识",
  "desc": "用例说明",
  "page_key": "对应页面键，决定 Profile 与 page 级 nudge",
  "user": "用户输入文本",
  "history": [{"role": "user|assistant", "content": "可选的前置对话"}],
  "expect": {
    "expect_tool": false,
    "any_keywords": ["命中其一即可的关键字"],
    "all_keywords": ["必须全部命中的关键字"],
    "forbid_keywords": ["不得出现的关键字"]
  }
}
```

- `expect_tool=true`：期望模型发起工具调用（agent 模式）。
- `any_keywords` / `all_keywords` / `forbid_keywords`：对模型正文做关键字断言。
- 字段缺省即不校验该项。

## 运行

```powershell
.\.venv\Scripts\Activate.ps1
python -m core.ai.eval_runner            # 真模型（需配置 base_url / API Key）
python -m core.ai.eval_runner --mock     # 离线 mock（不连网，仅校验拼装/裁剪不报错）
```

退出码非零表示存在失败用例（供 CI / 脚本判断）。

## 与服务器回流联动

telemetry 上报的坑 → 转成一条 case → 进回归集；本机「一键沉淀为 eval 用例」也写入 `cases/`。
