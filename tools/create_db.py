import os
import re
import logging
import hashlib
import argparse
from pathlib import Path
from pprint import pp

from decode_eeprom import parse_eeprom

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.basicConfig(
    encoding='utf-8', 
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s',
    handlers=[logging.FileHandler("create_db.log", mode='w'),
    stream_handler]
)

HEADINGS = "MU", "Train", "Region_ASCII", "Train_Brand", "PN_model", "PN_INDEX", "PN_Ident", "Hardware Number", "Unit Type", "Unit class", "Tel", "NAV", "DAB", "Sirius", "LTE", "Feature byte", "Region", "Brand", "Platform", "byte_17", "byte_18", "Model ID", "Dataset Number", "ifs_header_checksum", "ifs_SHA1", "ifs_header_checksum_patch", "RCC_address", "SHA1_patch"
db_file = Path("unit_db")

def assemble_db(backup_details, patch_details):
    csv = [
        ";".join(HEADINGS)
    ]
    for detail in backup_details:
        train = detail["Train"]
        pt = {t:d for t, d in patch_details.items() if t.startswith(train)}
        if not pt:
            logging.warning(f"No patch for: {train}")
        elif len(pt) > 1:
            logging.warning(f"can't match patch from {list(pt.keys())} patches for: {train}")
        else:
            ifs, ifs_sha = list(pt.values())[0]
            detail["SHA1_patch"] = ifs_sha
        
        detail["PN_model"], detail["PN_INDEX"], detail["PN_Ident"] = PN1_split(detail["PN1"])
        
        #detail["Region_ASCII"] = detail["Region"]
        row = ";".join([b2s(detail.get(f, "")) for f in HEADINGS])
        csv.append(row)
        
    logging.info(f"database written: {db_file}")
    db_file.write_text("\n".join(csv))


def b2s(b):
    return str(b, "utf8") if isinstance(b, bytes) else str(b)

def PN1_split(pn1):
    PN_model = pn1[0:6]
    PN_Ident = pn1[6:9]
    try:
        PN_INDEX = pn1[9]
    except IndexError:
        PN_INDEX = ''
    return PN_model, PN_INDEX, PN_Ident


def sha1sum(filename):
    h  = hashlib.sha1()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def parse_backups(backups_dir: Path):
    logging.info(f"Parsing backups in: {backups_dir} ({backups_dir.exists()})")
    backup_details = list()
    for eeprom in backups_dir.glob("**/*-EEProm.bin"):
        backup = eeprom.parent
        logging.info(f"Backup: {backup.name}")
        if os.path.getsize(eeprom) != 8192:
            logging.warning(f"Unexpected eeprom size: {os.path.getsize(eeprom)}")
        with eeprom.open("rb") as data:
            details = parse_eeprom(data)
        for ifs in backup.glob("*.ifs"): # todo make more explicit
            details["ifs_SHA1"] = sha1sum(ifs)
        backup_details.append(details)
        
    return backup_details


def parse_patches(patches_dir: Path):
    logging.info("Scanning patches")
    patch_details = dict()
    for ifs in patches_dir.glob("**/*.ifs"):
        train = ifs.parent.name.replace("_PATCH", "")
        logging.warning(f"{train}: {ifs}")
        sha1 = sha1sum(ifs)
        patch_details[train] = (ifs, sha1)

    return patch_details


def main():
    logging.info("M.I.B. Create Database")
    parser = argparse.ArgumentParser()
    parser.add_argument('--backups', type=Path, required=True)
    parser.add_argument('--patches', type=Path, required=True)
    args = parser.parse_args()
    
    patch_details = parse_patches(args.patches.expanduser())
    backup_details = parse_backups(args.backups.expanduser())
    #logging.warning(backup_details)
    assemble_db(backup_details, patch_details)


if __name__ == "__main__":
    main()
