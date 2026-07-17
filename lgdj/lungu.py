import sys
import termios
import tty
import threading
import time
import serial

# CRC8-MAXIM校验算法（双电机通用，按附件实现）
def crc8_maxim(data):
    """计算CRC8校验值，返回十六进制字符串和十进制值供查验"""
    crc = 0x00
    polynomial = 0x31  # 多项式0x31
    for byte in data:
        # 输入反射
        byte_reflected = 0
        for i in range(8):
            if byte & (1 << i):
                byte_reflected |= (1 << (7 - i))
        crc ^= byte_reflected
        
        # 迭代计算
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFF  # 保持8位
    
    # 输出反射
    crc_reflected = 0
    for i in range(8):
        if crc & (1 << i):
            crc_reflected |= (1 << (7 - i))
    
    # 返回校验值（十进制+十六进制）
    return crc_reflected, f"0x{crc_reflected:02X}"

# 电机配置
LEFT_MOTOR_ID = 0x01    # 左轮ID
RIGHT_MOTOR_ID = 0x02   # 右轮ID
MAX_SPEED = 500         # 速度范围：±3000
STOP_SPEED = 0

# 串口配置
SERIAL_PORT = '/dev/ttyCH341USB0'  # 替换为实际串口号
BAUDRATE = 115200

# 全局状态
is_running = True
current_keys = set()
lock = threading.Lock()
serial_port = None

def init_serial():
    """初始化串口"""
    try:
        port = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=0.1,
            parity=serial.PARITY_NONE,
            stopbits=1,
            bytesize=8
        )
        if port.is_open:
            print(f"串口 {SERIAL_PORT} 已打开（波特率 {BAUDRATE}）")
            return port
        print(f"无法打开串口 {SERIAL_PORT}")
        return None
    except Exception as e:
        print(f"串口初始化失败: {str(e)}")
        return None

def get_keyboard_input():
    """非阻塞读取键盘输入"""
    global is_running, current_keys
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while is_running:
            key = sys.stdin.read(1)
            with lock:
                if key == '\x03':  # Ctrl+C退出
                    is_running = False
                    break
                elif key in ['w', 'a', 's', 'd']:
                    current_keys.add(key)
                elif key == '\x1b':
                    sys.stdin.read(2)  # 忽略方向键
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def send_command(motor_id, speed):
    """发送10字节指令，输出校验值供查验"""
    global serial_port
    if not serial_port or not serial_port.is_open:
        print("串口未连接，无法发送指令")
        return False
    
    # 构建前9字节数据帧
    func_code = 0x64  # 速度环控制功能码
    speed_low = speed & 0xFF         # 速度低8位（小端模式）
    speed_high = (speed >> 8) & 0xFF # 速度高8位
    data_frame = [
        motor_id,       # 字节0：电机ID
        func_code,      # 字节1：功能码
        speed_low,      # 字节2：速度低8位
        speed_high,     # 字节3：速度高8位
        0x00, 0x00, 0x00, 0x00, 0x00  # 字节4-8：保留位
    ]
    
    # 计算校验值（输出十进制和十六进制供查验）
    crc_value, crc_hex = crc8_maxim(data_frame)
    
    # 完整10字节指令
    full_command = bytes(data_frame + [crc_value])
    
    # 输出校验值和指令详情（供查验）
    print(f"[校验信息] 电机ID={motor_id} | 前9字节: {[hex(b) for b in data_frame]} | 校验值: {crc_hex} ({crc_value})")
    print(f"[发送指令] {[hex(b) for b in full_command]} | 速度: {speed}\n")
    
    # 发送指令
    try:
        written = serial_port.write(full_command)
        return written == 10
    except Exception as e:
        print(f"指令发送失败: {str(e)}")
        return False

def stop_motors():
    """发送刹车指令（速度0）"""
    send_command(LEFT_MOTOR_ID, STOP_SPEED)
    send_command(RIGHT_MOTOR_ID, STOP_SPEED)
    print("已发送刹车指令")

def control_loop():
    """控制逻辑：按下按键运行，松开停止"""
    global is_running, current_keys
    while is_running:
        with lock:
            keys = current_keys.copy()
            current_keys.clear()
        
        # 速度控制逻辑
        if 'w' in keys:  # 前进
            left_speed, right_speed = -MAX_SPEED, MAX_SPEED
        elif 's' in keys:  # 后退
            left_speed, right_speed = MAX_SPEED, -MAX_SPEED
        elif 'a' in keys:  # 左转
            left_speed, right_speed = MAX_SPEED, MAX_SPEED
        elif 'd' in keys:  # 右转
            left_speed, right_speed = -MAX_SPEED, -MAX_SPEED
        else:  # 停止
            left_speed, right_speed = STOP_SPEED, STOP_SPEED
        
        # 发送指令
        send_command(LEFT_MOTOR_ID, left_speed)
        send_command(RIGHT_MOTOR_ID, right_speed)
        time.sleep(0.05)  # 20Hz控制频率

def main():
    global serial_port, is_running
    print("双电机校验控制程序（带校验值输出）")
    print("W前进 | S后退 | A左转 | D右转 | Ctrl+C退出")
    print("注：每次发送指令将输出前9字节和校验值供查验\n")
    
    serial_port = init_serial()
    if not serial_port:
        return
    
    input_thread = threading.Thread(target=get_keyboard_input, daemon=True)
    input_thread.start()
    
    try:
        control_loop()
    except KeyboardInterrupt:
        pass
    finally:
        is_running = False
        stop_motors()
        if serial_port.is_open:
            serial_port.close()
            print("串口已关闭")
        print("程序退出")

if __name__ == "__main__":
    main()

