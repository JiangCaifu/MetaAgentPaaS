import dashscope
dashscope.api_key = "sk-987afc27d130457bb5b038047feaabd3"
response = dashscope.Generation.call(
    model ='qwen-turbo',
    prompt='你好'
)
print(response)