import os
import logging
import argparse
from pathlib import Path
from binascii import hexlify as hexlify_bytes
from pprint import pp

logging.basicConfig(filename='create_db.log', encoding='utf-8', level=logging.INFO)



def parse_eeprom(data):
    EEPROM = (
        # Name,                 Offset, Length, Converter
        ("PN1",                 0x80,   10,     bytes_stripped), 
        ("PN2",                 0x8B,   10,     bytes_stripped), 
        ("Hardware Number",     0x96,    3,     bytes), 
        ("Variant2",            0xBA,   13,     bytes_stripped), 
        ("Train",               0x3A0,  19,     bytes_stripped), 
        ("MU",                  0x3B9,   4,     bytes), 
        ("Unit Type",           0xDD, 	 1,     lookup(unit_type)),
        ("Unit class",          0xDE, 	 1,     lookup(unit_class)),
        ("Feature byte",        0xDF,    1,     bin),
        ("Feat:Tel",            0xDF,    1,     bit(0)),
        ("Feat:NAV",            0xDF,    1,     bit(1)),
        ("Feat:DAB",            0xDF,    1,     bit(2)),
        ("Feat:Sirius",         0xDF,    1,     bit(3)),
        ("Feat:LTE",            0xDF,    1,     bit(4)),
        ("Feat:2DNAv",          0xDF,    1,     bit(5)),
        ("Feat:MMI Radio",      0xDF,    1,     bit(6)),  
        ("Region",              0xE0,    1,     lookup(region)),
        ("Brand",               0xE1,    1,     lookup(brand)),
        ("Platform",            0xE2,    1,	    lookup(platform)),
        ("Long Coding LC",      0xF1,   25,     hexlify),
        ("Model ID",            0xF1+0,  3,     hexlify),
        ("byte_3_Country_Navigation",0xF1+3, 1, hexlify),
        ("External Sound",      0xF1+11, 1,     hexlify),
        ("byte_17_Skinning",    0xF1+17, 1,     hexlify),
        ("byte_18_Screenings",  0xF1+18, 1,     hexlify),
        ("Dataset Number",      0x12e,  15,     bytes),
    )

    details = {}
    for name, offset, length, converter in EEPROM:
        data.seek(offset)
        details[name] = converter(data.read(length))
    return details


# converter functions

def bytes_stripped(b):
    return bytes(b).strip()
    

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


def lookup(table):
    """ 
    Used to lookup the dict tables below, 
    or return the raw hex value if missing from table
    """
    def get(value):
        ival = ord(value)
        return table.get(ival, f"0x{ival:02x}")
    return get


unit_type = {
    0x04: "FM2",
    0x07: "FMQ",
    0x06: "EM2",
}

brand = {
    0x01: "VW",
    0x02: "AU",
    0x03: "SK",
    0x04: "SE",
    0x05: "POG",
    0x06: "BYG",
}

unit_class = {
    0x01: "High",
    0x04: "Premium",
}

region = {
    0x01: "ER",
    0x02: "EU",
    0x03: "US",
    0x04: "RW",
    0x05: "CN",
    0x06: "JP",
    0x07: "KR",
    0x08: "Asia",
    0x09: "TW",
}

platform = {
    0x01: "MQB",
    0x02: "MQT",
    0x03: "MLB",
    0x04: "MLE",
    0x05: "MLP",
}


def parse_backups(backups_dir: Path):
    logging.info(f"Parsing backups in: {backups_dir}")
    for eeprom in backups_dir.glob("**/*-EEProm.bin"):
        backup = eeprom.parent
        logging.info(f"Backup: {backup.name}")
        if os.path.getsize(eeprom) != 8192:
            logging.warning(f"Unexpected eeprom size: {os.path.getsize(eeprom)}")
        with eeprom.open("rb") as data:
            details = parse_eeprom(data)
            pp(details)


def parse_patches(patches_dir: Path):
    pass



def main():
    logging.info("M.I.B. Create Database")
    parser = argparse.ArgumentParser()
    parser.add_argument('--backups', type=Path, required=True)
    parser.add_argument('--patches', type=Path, required=True)
    args = parser.parse_args()
    parse_backups(args.backups)
    parse_patches(args.patches)


if __name__ == "__main__":
    main()