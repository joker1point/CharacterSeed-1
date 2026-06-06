from fastapi import FastAPI
from .api.chat import router as chat_router

app = FastAPI()

app.include_router(chat_router)

from .pipeline.generator import generate_runtime

# #小测试
# print("开始")
# session_id = input("请输入本次会话id：")
# aiRuntime = generate_runtime(session_id)

# while True:
#     user_input = input("用户：")
#     response=aiRuntime.chat(user_input)
#     print("小助手：", response)

# # 测试向量化管线
# from .pipeline.embedding_runtime import EmbeddingRuntime
# embedding_runtime = EmbeddingRuntime("ai/data/raw/Mesmer.txt")
# embedding_runtime.process_file()

# # 测试脚本生成
# print("测试脚本生成")
# runtime = generate_runtime("test_session")
# script = runtime.make_script("ai/data/raw/Mesmer.txt", "基于文本创建成年小梅斯梅尔的角色设定")
# 测试脚本生成后角色互动
print("测试角色互动")
runtime = generate_runtime("toothfairy_session", script_path="ai/data/character_scripts/牙仙.json")
while True:
    user_input = input("用户：")
    response=runtime.chat_cosplay(user_input)# 默认测试
    print("角色：", response)
