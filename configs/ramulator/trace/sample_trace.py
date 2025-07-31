import packet_pb2

# === PacketHeader 생성 ===
header = packet_pb2.PacketHeader()
header.obj_id = "CPU_0"
header.ver = 1
header.tick_freq = 1000000000  # 예: 1GHz

# id_strings에 값 추가
entry1 = header.id_strings.add()
entry1.key = 0
entry1.value = "Load"

entry2 = header.id_strings.add()
entry2.key = 1
entry2.value = "Store"

# === Packet 생성 ===
packet1 = packet_pb2.Packet()
packet1.tick = 1000
packet1.cmd = 0  # 예: LOAD
packet1.addr = 0xABCD1234
packet1.size = 64
packet1.flags = 0x01  # 예: 캐시 가능
packet1.pkt_id = 42
packet1.pc = 0x400123

packet2 = packet_pb2.Packet()
packet2.tick = 1500
packet2.cmd = 1  # 예: STORE
packet2.addr = 0xDEADBEEF
packet2.size = 32
packet2.flags = 0x02  # 예: 비캐시
packet2.pkt_id = 43
packet2.pc = 0x400126

# === 직렬화하여 저장하기 (예: trace.bin) ===
with open("trace_output.bin", "wb") as f:
    f.write(header.SerializeToString())
    f.write(packet1.SerializeToString())
    f.write(packet2.SerializeToString())
