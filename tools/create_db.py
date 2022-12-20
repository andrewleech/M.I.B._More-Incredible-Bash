import os
import re
import logging
import hashlib
import argparse
from pathlib import Path
from pprint import pp

from decode_eeprom import parse_eeprom
from decode_ifs_header import parse_ifs

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.basicConfig(
    encoding='utf-8', 
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s',
    handlers=[logging.FileHandler("create_db.log", mode='w'),
    stream_handler]
)

db_file = Path("unit_db.csv")

#add change Headings to change output order or fields
HEADINGS = "MU", "Train", "Train_Region", "Train_Brand", "PN_model", "PN_Ident", "PN_INDEX", "Hardware Number", "Unit Type", "Unit Type_HEX", "Unit class", "Unit class_HEX", "Feat:Tel", "Feat:NAV", "Feat:DAB", "Feat:Sirius", "Feat:LTE", "Feature byte", "Variant2", "Region", "Region_HEX", "Brand", "Brand_HEX", "Platform", "Platform_HEX", "LC:byte_17_Skinning", "LC:byte_18_Screenings", "LC:Model ID", "Long Coding LC", "Dataset Number", "ifs_header_checksum", "ifs_SHA1", "ifs_header_checksum_patch", "ifs_file_name_checksum_patch", "RCC_offset", "SHA1_patch", "FAZIT ID", "MIB SN"

# adjust to equired output format. ',' = rest of the world ';' for Germany
# adding \t in front of the delimiter will prevent conversion to date/number in Excel
FIELD_SEP = "\t;" 

def assemble_db(backup_details, patch_details):
    csv = [
        FIELD_SEP.join(HEADINGS)
    ]
    for detail in backup_details:
        train = detail["Train"]
        train_brand, train_region = train_split(train)
        detail["Train_Brand"] = train_brand
        detail["Train_Region"] = train_region
        pt = {t:d for t, d in patch_details.items() if t.startswith(train)}
        if not pt:
            logging.warning(f"No patch for: {train}")
        elif len(pt) > 1:
            logging.warning(f"can't match patch from {list(pt.keys())} patches for: {train}")
        else:
            ifs, ifs_sha, ifs_patch, offset, ifs_checksum = list(pt.values())[0]
            detail["SHA1_patch"] = ifs_sha
            detail["ifs_header_checksum_patch"] = ifs_patch
            detail["RCC_offset"] = offset
            detail["ifs_file_name_checksum_patch"] = ifs_checksum
            #print(ifs_patch)
        
        detail["PN_model"], detail["PN_INDEX"], detail["PN_Ident"] = PN1_split(detail["PN1"])
        
        row = FIELD_SEP.join([b2s(detail.get(f, "")) for f in HEADINGS])
        csv.append(row)
        
    logging.info(f"database written: {db_file}")
    db_file.write_text("\n".join(csv))


def b2s(b):
    return str(b, "utf8") if isinstance(b, bytes) else str(b)


def train_split(train):
    hdr, brand, region, *vers = train.upper().split("_")
    return region, brand

def ifs_name_split(file_name):
    MU, ifs1, ifs2, ifs3, offset, ifs_checksum = file_name.lower().split("-")
    return offset, ifs_checksum

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
    for eeprom in backups_dir.glob("*/*-EEProm.bin"): # Change to "**/*-EEProm.bin" to enable scan of sub directories
        backup = eeprom.parent
        logging.info(f"Backup: {backup.name}")
        if os.path.getsize(eeprom) != 8192:
            logging.warning(f"Unexpected eeprom size: {os.path.getsize(eeprom)}")
        with eeprom.open("rb") as data:
            details = parse_eeprom(data)
        for ifs in backup.glob("*-ifs-root-part2*.ifs"):
            details["ifs_SHA1"] = sha1sum(ifs)
        for ifs_header in backup.glob("*-ifs-root-part2*.ifs"):
            with ifs_header.open("rb") as data:
                ifs_details = parse_ifs(data)
                details.update(ifs_details)

        backup_details.append(details)

    return backup_details

def parse_patches(patches_dir: Path):
    logging.info("Scanning patches")
    patch_details = dict()
    ifs_patch_details = list()
    for ifs in patches_dir.glob("*/*.ifs"):
        patches = ifs.parent
        train = ifs.parent.name.replace("_PATCH", "")
        logging.warning(f"{train}: {ifs}")
        sha1 = sha1sum(ifs)
        for ifs_header in patches.glob("*-ifs-root-part2*.ifs"):
            #print(ifs_header.name)
            offset, ifs_checksum = ifs_name_split(ifs_header.name.replace(".ifs", ""))
            #print(offset)
            #print(ifs_checksum)
            with ifs_header.open("rb") as data:
                ifs_patch_details = parse_ifs(data, "_patch")
                #print(ifs_patch_details)

        patch_details[train] = (ifs, sha1, ifs_patch_details["ifs_header_checksum_patch"], offset, ifs_checksum)

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
    #logging.warning(patch_details)
    assemble_db(backup_details, patch_details)


if __name__ == "__main__":
    main()
