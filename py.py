# Python后端收到JSON后的处理逻辑（示例）

# 假设收到的数据是 data = {'command': 'SEND_QUEUE', 'payload': {...}}
if data.get('command') == 'SEND_QUEUE':
  payload = data.get('payload')

  # 开始“翻译”
  serial_command_string = ""
  for i in range(1, 9): # 遍历 s1 到 s8
    key = f"s{i}"
    if key in payload:
      h = payload[key].get('h_angle')
      v = payload[key].get('v_angle')
      serial_command_string += f"{key}:{h},{v};"

  # 加上一个换行符作为结束标志
  serial_command_string += "\n"

  # 此时，serial_command_string == "s1:90,45;s2:92,46;s3:94,47;...s8:104,52;\n"

  # 通过串口发送给Hi3861
  # serial_port.write(serial_command_string.encode('utf-8'))

  print(f"已发送串口指令: {serial_command_string}")