import os, sys, logging, pathlib

def convert_eeprom(filename):
    logging.info('Converting: ' + str(filename))
    print(f"Filename: {filename}")
    with filename.open('r') as txt_file:
        lines = txt_file.readlines()
    bin_file = filename.with_suffix('.bin')
    logging.info('Writing to: ' + str(bin_file))
    with bin_file.open('wb') as f:
        for line in lines:
            if line.find('0x') > -1:
                f.write(bytearray.fromhex(line.strip().split('\t')[1].replace(' ','')))
    logging.info('Conversion complete.')

match len(sys.argv):
    case 2:
        #convert('.\\' + os.path.splitext(sys.argv[1])[0])
        convert_eeprom(pathlib.Path(sys.argv[1]))
    case 1:
        for root, dirs, files in os.walk("."):
            path = root.split(os.sep)
            for file in files:
                if (root+file).endswith('.txt'):
                        convert(root+'\\'+file)
    case _:
        print("Usage: eeprom2bin.py <filename>")
        print("   or: eeprom2bin.py")
        input("\nPress Enter to exit...")
        sys.exit(1)

# input("\nPress Enter to exit...")
sys.exit(1)