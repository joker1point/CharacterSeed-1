"""
[优化] 原 main.py 中的阻塞式角色扮演测试移至独立脚本。
用法（在 heart-time 项目根目录）:
  python -m ai.scripts.cli_cosplay_test
"""
from ai.config import CHARACTER_SCRIPTS_DIR
from ai.pipeline.generator import generate_runtime


def main():
    script_path = CHARACTER_SCRIPTS_DIR / "小梅斯梅尔.json"
    runtime = generate_runtime("Mesmer_session", script_path=str(script_path))

    print("角色扮演测试已启动，输入 quit 退出")
    while True:
        user_input = input("用户：").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            break
        response = runtime.chat_cosplay(user_input)
        print("角色：", response)


if __name__ == "__main__":
    main()
