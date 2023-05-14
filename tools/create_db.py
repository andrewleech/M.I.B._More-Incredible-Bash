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

# change Headings to change output order or fields
HEADINGS = "MU", "Train", "Train_Region", "Train_Brand", "PN1", "PN_model", "PN_Ident", "PN_INDEX", "Hardware Number", "Unit Type", "Unit Type_HEX", "Unit class", "Unit class_HEX", "Feat:Tel", "Feat:NAV", "Feat:DAB", "Feat:Sirius", "Feat:LTE", "Feature byte", "Variant2", "Region", "Region_HEX", "Brand", "Brand_HEX", "Platform", "Platform_HEX", "LC:byte_17_Skinning", "LC:byte_18_Screenings", "LC:Model ID", "Long Coding LC", "Dataset Number", "ifs_header_checksum", "ifs_file_name_checksum_patch", "ifs_SHA1", "ifs_header_checksum_patch", "RCC_offset", "SHA1_patch", "FAZIT ID", "MIB SN"

# adjust to required output format. ',' = rest of the world ';' for Germany
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
        logging.warning(f"Detail train: {train}")
        pt = {t:d for t, d in patch_details.items() if t.startswith(train)}
        logging.info(f"patch details: {pt}")
        #checksum = detail["ifs_header_checksum"]
        if not pt:
            logging.warning(f"No patch for: {train}")
            #logging.info(f"Header checksum: {checksum}")
            # add patch creation here
            # get ifs_header_checksum from patch_details
            # use this to create patch and add ifs_header_checksum to file name
        elif len(pt) > 1:
            logging.warning(f"can't match patch from {list(pt.keys())} patches for: {train}")
        else:
            ifs, ifs_sha, ifs_patch, offset, ifs_checksum = list(pt.values())[0]
            detail["SHA1_patch"] = ifs_sha
            detail["ifs_header_checksum_patch"] = ifs_patch
            detail["RCC_offset"] = offset
            detail["ifs_file_name_checksum_patch"] = ifs_checksum
        
        detail["PN_model"], detail["PN_INDEX"], detail["PN_Ident"] = PN1_split(detail["PN1"])
        
        row = FIELD_SEP.join([b2s(detail.get(f, "")) for f in HEADINGS])
        csv.append(row)
        
    logging.info(f"database written: {db_file}")
    db_file.write_text("\n".join(csv))


def b2s(b):
    return str(b, "utf8") if isinstance(b, bytes) else str(b)


def train_split(train):
    logging.info(f"Train: {train}")
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

def convert_eeprom(filename):
    logging.info('Converting: ' + str(filename))
    with filename.open('r') as txt_file:
        lines = txt_file.readlines()
    bin_file = filename.with_suffix('.bin')
    logging.info('Writing to: ' + str(bin_file))
    with bin_file.open('wb') as f:
        for line in lines:
            if line.find('0x') > -1:
                f.write(bytearray.fromhex(line.strip().split('\t')[1].replace(' ','')))
    logging.info('Conversion complete.')

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
    for eeprom in backups_dir.glob("*/*-EEProm.txt"): # Change to "**/*-EEProm.bin" to enable scan of sub directories
        backup = eeprom.parent
        logging.info(f"Backup: {backup.name}")
        #logging.info(f"{eeprom.stem}.bin")
        if not (backup / f"{eeprom.stem}.bin").exists() or os.path.getsize(backup / f"{eeprom.stem}.bin") != 8192:
            if not (backup / f"{eeprom.stem}.bin").exists():
                logging.warning(f"*.bin not found")
            else:
                logging.warning(f"*.bin size is not equal to 8192 bytes")
            txt_file = backup / f"{eeprom.stem}.txt"
            if not txt_file.exists():
                logging.error(f"No corresponding .txt file found for: {eeprom}")
                continue
            convert_eeprom(txt_file)
            eeprom = backup / f"{eeprom.stem}.bin"
            if not eeprom.exists():
                logging.error(f"Conversion failed for: {txt_file}")
                continue
        else:
            eeprom = backup / f"{eeprom.stem}.bin"
        with eeprom.open("rb") as data:
            details = parse_eeprom(data)
        for ifs in backup.glob("*-ifs-root-part2*.ifs"):
            details["ifs_SHA1"] = sha1sum(ifs)
            with ifs.open("rb") as data:
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
        logging.info(f"{train}: {ifs}")
        sha1 = sha1sum(ifs)
        offset, ifs_checksum = ifs_name_split(ifs.name.replace(".ifs", ""))
        with ifs.open("rb") as data:
            ifs_patch_details = parse_ifs(data, "_patch")

        patch_details[train] = (ifs, sha1, ifs_patch_details["ifs_header_checksum_patch"], offset, ifs_checksum)
        pt = {t:d for t, d in patch_details.items() if t.startswith(train)}
        logging.info(f"Patch details parsed: {pt}")

    logging.info(f"Output compiled patch details: {patch_details}")

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
