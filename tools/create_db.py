import os
import logging
import argparse
from pathlib import Path
from pprint import pp

from decode_eeprom import parse_eeprom

logging.basicConfig(filename='create_db.log', encoding='utf-8', level=logging.INFO)

HEADINGS = "MU", "Train", "Region_ASCII", "Train_Brand", "PN_model", "PN_INDEX", "PN_Ident", "Hardware Number", "Unit Type", "Unit class", "Tel", "NAV", "DAB", "Sirius", "LTE", "Feature byte", "Region", "Brand", "Platform", "byte_17", "byte_18", "Model ID", "Dataset Number", "ifs_header_checksum", "ifs_SHA1", "ifs_header_checksum_patch", "RCC_address", "SHA1_patch"


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