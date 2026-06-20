import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.prompt_manager import PromptManager

pm = PromptManager(enable_log_masking=False)

history = [
    {"role": "user", "content": "解读 Marker A-B 之间数据"},
    {"role": "assistant", "content": "A=1.0s B=2.0s 区间平均电流约 5mA（旧结论）"},
]

waveform_old_in_history = any("5mA" in m["content"] for m in history)

msgs = pm.build_messages(
    page_key="datalog",
    history=history,
    user_text="现在重设了 Marker，再解读一次",
    waveform_context="[波形数据摘要]\n分析范围：3.0~4.0 s（屏幕可见区）\n[Marker A→B 区间] A=3s, B=4s, 时长=1s\n- 通道 F1-A-I1：avg=20 mA",
)

print("=== messages roles ===")
for i, m in enumerate(msgs):
    head = m["content"].replace("\n", " ")[:90]
    print(f"[{i}] {m['role']}: {head}")

last_user = msgs[-1]["content"]
print("\n=== checks ===")
print("最后一条是 user:", msgs[-1]["role"] == "user")
print("波形摘要在最后 user 段:", "本轮波形数据" in last_user and "20 mA" in last_user)
print("含时效声明(以此为准):", "以此为准" in last_user)
print("system 段不含本轮波形:", "20 mA" not in msgs[0]["content"])
print("history 旧结论仍在(role保持):", any("旧结论" in m["content"] for m in msgs))
print("旧结论位置在新波形之前(被时效声明压制):",
      [i for i, m in enumerate(msgs) if "旧结论" in m["content"]][0] < len(msgs) - 1)
