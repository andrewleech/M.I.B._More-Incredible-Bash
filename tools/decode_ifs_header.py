from binascii import hexlify as hexlify_bytes

def parse_ifs(data, suffix=""):
    ifs_header = (
        # Name,                        Offset, Length, Converter
        ("CHECK1",                       0x00,      2,     hexlify), # 0xEB7EFF to identify ifs partition
        ("ifs_header_checksum",          0x24,      4,     hexlify),
        ("CHECK2",                      0x140,     16,     str_stripped), # /bin/flashunlock to identify ifs-root-stage2 partition
    )

    details = {}
    for name, offset, length, converter in ifs_header:
        data.seek(offset)
        details[name+suffix] = converter(data.read(length))

    return details


# converter functions

def bytes_stripped(b):
    return bytes(b).strip()
    
def str_stripped(b):
    return string(bytes_stripped(b))
    
def string(b):
    return str(b, "utf8") if isinstance(b, bytes) else str(b)


def bit(offset):
    def ret_bit(value):
        return 1 if ord(value) & (1 << offset) else 0
    return ret_bit


def bin(byte):
    return f'{ord(byte):0>8b}'


def hexlify(value):
    if len(value) == 1:
        return f"0x{ord(value):02x}"
    else:
        return str(hexlify_bytes(value), "utf-8")

