import argparse
import struct
import packet_pb2
from google.protobuf.internal.encoder import _VarintBytes
from packet_pb2 import Packet  # Generated via protoc

# 명령어 문자열을 enum 번호로 매핑
def cmd_to_int(opcode):
    opcode_map = {
        "LD": 1,
        "ST": 4,
        "P_LD": 60,          # PimReadReq
        "P_LD_A": 61,        # PimReadReqAP
        "P_ST": 62,          # PimWriteReq
        "P_ST_A": 63,        # PimWriteReqAP
        "P_IV_RD32_4A": 64,   # PimIvReadReqAP
        "P_OV_RD32_4A": 65,   # PimOvReadReqAP
        "P_OV_WR32_4A": 66,   # PimOvWriteReqAP
        "P_MACPB_8": 67      # PimMacPb8
    }
    return opcode_map.get(opcode.upper(), 255)  # Unknown: 255

# 한 줄을 파싱해서 (cmd, addr) 반환
def parse_line(line):
    parts = line.strip().split()
    if len(parts) != 2:
        print(f"[Warning] Invalid format: {line.strip()}")
        return None

    opcode, addr_str = parts
    cmd = cmd_to_int(opcode)
    
    if cmd == 255:
        print(f"[Error] Unknown opcode '{opcode}' in line: {line.strip()}")
        return None

    try:
        addr = int(addr_str, 0)  # supports hex (0x...), dec
    except ValueError:
        print(f"[Error] Invalid address '{addr_str}' in line: {line.strip()}")
        return None

    return cmd, addr

# protobuf 패킷 생성
def make_packet(pkt_id, cmd, addr):
    pkt = Packet()
    pkt.tick = pkt_id
    pkt.cmd = cmd
    pkt.addr = addr
    pkt.size = 32
    pkt.flags = 0
    pkt.pkt_id = pkt_id
    pkt.pc = 0
    return pkt

# PacketHeader 생성
def create_packet_header():
    header = packet_pb2.PacketHeader()
    header.obj_id = "CPU_0"
    header.ver = 1
    header.tick_freq = 1000000000000  # 1 THz

    id_map = {
        1: "Load",
        4: "Store",
        60: "PimReadReq",
        61: "PimReadReqAP",
        62: "PimWriteReq",
        63: "PimWriteReqAP",
        64: "PimIvReadReqAP",
        65: "PimOvReadReqAP",
        66: "PimOvWriteReqAP",
        67: "PimMacPb8"
    }

    for key, value in id_map.items():
        entry = header.id_strings.add()
        entry.key = key
        entry.value = value
    return header

# trace 텍스트 → protobuf 바이너리 변환
def trace_to_proto_binary(input_txt_path, output_bin_path):
    MAGIC_NUMBER = 0x356D6567
    header = create_packet_header()
    serialized_header = header.SerializeToString()

    with open(input_txt_path) as trace_file, open(output_bin_path, "wb") as bin_file:
        bin_file.write(struct.pack("<I", MAGIC_NUMBER))
        bin_file.write(_VarintBytes(len(serialized_header)))
        bin_file.write(serialized_header)
        pkt_id = 0
        for line in trace_file:
            parsed = parse_line(line)
            if not parsed:
                continue
            cmd, addr = parsed
            pkt = make_packet(pkt_id, cmd, addr)
            pkt_id += 1
            serialized = pkt.SerializeToString()
            bin_file.write(_VarintBytes(len(serialized)))
            bin_file.write(serialized)

# CLI entry point
def main():
    parser = argparse.ArgumentParser(description="Convert trace file to protobuf binary format.")
    parser.add_argument("--input", type=str, default="sample.trace", help="Input trace text file")
    parser.add_argument("--output", type=str, default="trace.bin", help="Output protobuf binary file")
    args = parser.parse_args()
    trace_to_proto_binary(args.input, args.output)

if __name__ == "__main__":
    main()