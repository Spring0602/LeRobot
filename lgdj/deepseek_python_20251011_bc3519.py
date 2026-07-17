def crc8_maxim(data):
    """
    计算CRC-8/MAXIM校验值
    多项式: x8 + x5 + x4 + 1 (0x31)
    初始值: 0x00
    输入反射: True
    输出反射: True
    最终异或值: 0x00
    """
    crc = 0x00
    polynomial = 0x31  # 多项式: x8 + x5 + x4 + 1
    
    for byte in data:
        # 输入反射
        byte_reflected = 0
        for i in range(8):
            if byte & (1 << i):
                byte_reflected |= (1 << (7 - i))
        
        crc ^= byte_reflected
        
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc = (crc << 1)
            crc &= 0xFF  # 保持8位
    
    # 输出反射
    crc_reflected = 0
    for i in range(8):
        if crc & (1 << i):
            crc_reflected |= (1 << (7 - i))
    
    return crc_reflected

def main():
    # 示例数据: 02 64 00 64 00 00 00 00 00
    data = [0x02, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00]
    
    crc_value = crc8_maxim(data)
    
    print(f"输入数据: {[hex(x) for x in data]}")
    print(f"CRC8校验值: {hex(crc_value)}")
    print(f"完整指令: {[hex(x) for x in data]} {hex(crc_value)}")

if __name__ == "__main__":
    main()
