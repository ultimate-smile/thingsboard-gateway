import OpenOPC

# 创建客户端
opc = OpenOPC.client()

# 连接到服务器
opc.connect('Matrikon.OPC.Simulation.1')

# 列出所有标签
tags = opc.list()
print(tags)

# 读取一个标签
value = opc.read('Random.Int4')
print(value)

# 关闭连接
opc.close()