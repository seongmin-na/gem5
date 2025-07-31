import argparse
import struct

import packet_pb2
from google.protobuf.internal.encoder import _VarintBytes
from packet_pb2 import Packet  # 이 파일은 protoc로 컴파일된 파일


# 명령어를 숫자로 매핑하는 함수
def cmd_to_int(opcode):
    opcode_map = {
        "LD": 1,  # readreq
        "ST": 4,  # writereq
        # 필요에 따라 계속 추가
    }
    return opcode_map.get(
        opcode.upper(), 255
    )  # 정의되지 않은 명령은 255 (에러 처리 목적)


# 한 줄을 파싱해서 (cmd, addr) 튜플로 반환
def parse_line(line):
    parts = line.strip().split()
    if len(parts) != 2:
        return None
    opcode, addr_str = parts
    cmd = cmd_to_int(opcode)
    addr = int(addr_str)
    return cmd, addr


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


def create_packet_header():
    header = packet_pb2.PacketHeader()
    header.obj_id = "CPU_0"
    header.ver = 1
    header.tick_freq = 1000000000000  # 1 THz
    entry1 = header.id_strings.add()
    entry1.key = 1
    entry1.value = "Load"

    entry2 = header.id_strings.add()
    entry2.key = 4
    entry2.value = "Store"

    return header


def trace_to_proto_binary(input_txt_path, output_bin_path):
    MAGIC_NUMBER = 0x356D6567
    # 2. Create and serialize PacketHeader
    header = create_packet_header()
    serialized_header = header.SerializeToString()

    with open(input_txt_path) as trace_file, open(
        output_bin_path, "wb"
    ) as bin_file:
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


def main():
    parser = argparse.ArgumentParser(
        description="Convert trace file to protobuf binary format."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="sample.trace",
        help="Input trace text file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="trace.bin",
        help="Output protobuf binary file",
    )

    args = parser.parse_args()
    trace_to_proto_binary(args.input, args.output)


if __name__ == "__main__":
    main()

    """enum Command
    {
        InvalidCmd,
        ReadReq,
        ReadResp,
        ReadRespWithInvalidate,
        WriteReq,
        WriteResp,
        WriteCompleteResp,
        WritebackDirty,
        WritebackClean,
        WriteClean,            // writes dirty data below without evicting
        CleanEvict,
        SoftPFReq,
        SoftPFExReq,
        HardPFReq,
        SoftPFResp,
        HardPFResp,
        WriteLineReq,
        UpgradeReq,
        SCUpgradeReq,           // Special "weak" upgrade for StoreCond
        UpgradeResp,
        SCUpgradeFailReq,       // Failed SCUpgradeReq in MSHR (never sent)
        UpgradeFailResp,        // Valid for SCUpgradeReq only
        ReadExReq,
        ReadExResp,
        ReadCleanReq,
        ReadSharedReq,
        LoadLockedReq,
        StoreCondReq,
        StoreCondFailReq,       // Failed StoreCondReq in MSHR (never sent)
        StoreCondResp,
        LockedRMWReadReq,
        LockedRMWReadResp,
        LockedRMWWriteReq,
        LockedRMWWriteResp,
        SwapReq,
        SwapResp,
        // MessageReq and MessageResp are deprecated.
        MemFenceReq = SwapResp + 3,
        MemSyncReq,  // memory synchronization request (e.g., cache invalidate)
        MemSyncResp, // memory synchronization response
        MemFenceResp,
        CleanSharedReq,
        CleanSharedResp,
        CleanInvalidReq,
        CleanInvalidResp,
        // Error responses
        // @TODO these should be classified as responses rather than
        // requests; coding them as requests initially for backwards
        // compatibility
        InvalidDestError,  // packet dest field invalid
        BadAddressError,   // memory address invalid
        ReadError,         // packet dest unable to fulfill read command
        WriteError,        // packet dest unable to fulfill write command
        FunctionalReadError, // unable to fulfill functional read
        FunctionalWriteError, // unable to fulfill functional write
        // Fake simulator-only commands
        PrintReq,       // Print state matching address
        FlushReq,      //request for a cache flush
        InvalidateReq,   // request for address to be invalidated
        InvalidateResp,
        // hardware transactional memory
        HTMReq,
        HTMReqResp,
        HTMAbort,
        // Tlb shootdown
        TlbiExtSync,
        NUM_MEM_CMDS
    };
    """
