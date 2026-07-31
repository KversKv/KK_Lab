"""W2-a 基准落盘 + 比对（ExecutionLogsFrame 静态样式 1:1 迁移验证）。"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.makedirs("tests/_w2_baseline", exist_ok=True)

import ui.modules.execution_logs_module_frame as m


def dump():
    open("tests/_w2_baseline/log_frame.qss.txt", "w", encoding="utf-8").write(
        m._LOG_FRAME_STYLE)
    open("tests/_w2_baseline/log_splitter.qss.txt", "w", encoding="utf-8").write(
        m._LOG_SPLITTER_STYLE)
    print("baseline dumped")


def norm(s: str):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return [l.strip() for l in s.splitlines() if l.strip()]


def check():
    """原 124/9 行必须在迁移后原样保留（W2 新增的 transparent/chip 规则为扩展，
    只增不改——故断言旧行是迁移后输出的子序列且逐行一致）。"""
    for name, new in [
        ("log_frame.qss.txt", m._LOG_FRAME_STYLE),
        ("log_splitter.qss.txt", m._LOG_SPLITTER_STYLE),
    ]:
        old = open(f"tests/_w2_baseline/{name}", encoding="utf-8").read()
        o, n = norm(old), norm(new)
        # 原行须按序出现在迁移后输出中（允许插入新规则，不允许改/删原行）
        it = iter(n)
        missing = [line for line in o if line not in it]
        if missing:
            print(f"DIFF {name}: 原行被改/删，首处: {missing[0]!r}")
            return False
        print(f"{name}: 原 {len(o)} 行全部保留（迁移后 {len(n)} 行，W2 扩展 "
              f"{len(n) - len(o)} 行）")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dump":
        dump()
    else:
        sys.exit(0 if check() else 1)
