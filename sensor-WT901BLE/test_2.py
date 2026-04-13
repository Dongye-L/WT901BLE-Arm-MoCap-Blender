import asyncio
import bleak
import device_model
import json
import serial

# ================= 配置区 =================
# 1. 填入你扫描确定的 MAC 地址
MAC_UPPER_ARM = "FF:6F:55:03:8C:64"  # 大臂 -> /joint/0
MAC_LOWER_ARM = "E3:50:0A:AD:C5:5E"  # 小臂 -> /joint/1（请确保这是你刚才扫描到的那个）

# 2. 串口配置
SERIAL_PORT = "COM1"
BAUD_RATE = 115200
# ==========================================

# --- 初始化串口 ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"✅ 虚拟串口 {SERIAL_PORT} 已成功打开")
except Exception as e:
    print(f"❌ 串口打开失败: {e}")
    ser = None

# --- 数据更新回调函数 ---


def updateData(DeviceModel):
    """当任何一个传感器数据更新时，此方法会被触发"""
    # 获取当前发数据传感器的 MAC 地址（转大写对比）
    address = getattr(DeviceModel, 'address', "").upper()

    # 获取四元数
    q = [DeviceModel.get("Q0"), DeviceModel.get(
        "Q1"), DeviceModel.get("Q2"), DeviceModel.get("Q3")]

    if all(v is not None for v in q):
        # 根据 MAC 地址自动分配 Key
        if address == MAC_UPPER_ARM:
            key = "/joint/0"
        elif address == MAC_LOWER_ARM:
            key = "/joint/1"
        else:
            return  # 忽略非配置内的设备

        # 封装并发送
        packet = {"key": key, "value": q}
        payload = json.dumps(packet) + "\n"

        if ser and ser.is_open:
            ser.write(payload.encode('utf-8'))
            # 开启实时监控输出
            print(f"📡 转发中 [{key}]: {q}")


async def start_single_sensor(mac, name):
    """启动单个传感器的搜索与连接"""
    print(f"🔍 正在连接 {name} ({mac})...")
    try:
        # 直接通过地址找设备，超时设为 20 秒
        device = await bleak.BleakScanner.find_device_by_address(mac, timeout=20.0)

        if device:
            # 创建模型并手动绑定地址属性，方便 updateData 区分
            model = device_model.DeviceModel(name, device, updateData)
            model.address = mac
            print(f"✅ {name} 连接成功，开启数据流...")
            await model.openDevice()
        else:
            print(f"❌ 搜寻超时：找不到 {name}")
    except Exception as e:
        print(f"⚠️ {name} 连接发生异常: {e}")


async def main():
    print("🚀 动捕发射端启动，准备连接双传感器...")
    # 使用 gather 同时启动两个任务
    await asyncio.gather(
        start_single_sensor(MAC_UPPER_ARM, "大臂传感器"),
        start_single_sensor(MAC_LOWER_ARM, "小臂传感器")
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已被用户停止")
