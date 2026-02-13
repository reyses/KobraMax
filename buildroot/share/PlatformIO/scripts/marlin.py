#
# marlin.py
# Helper module with some commonly-used functions
#
import shutil
from pathlib import Path

from SCons.Script import DefaultEnvironment
env = DefaultEnvironment()

def copytree(src, dst, symlinks=False, ignore=None):
    for item in src.iterdir():
        if item.is_dir():
            shutil.copytree(item, dst / item.name, symlinks, ignore)
        else:
            shutil.copy2(item, dst / item.name)

def replace_define(field, value):
    envdefs = env['CPPDEFINES'].copy()
    for define in envdefs:
        if define[0] == field:
            env['CPPDEFINES'].remove(define)
    env['CPPDEFINES'].append((field, value))

# Relocate the firmware to a new address, such as "0x08005000"
def relocate_firmware(address):
    replace_define("VECT_TAB_ADDR", address)

# Relocate the vector table with a new offset
def relocate_vtab(address):
    replace_define("VECT_TAB_OFFSET", address)

# Replace the existing -Wl,-T with the given ldscript path
def custom_ld_script(ldname):
    apath = str(Path("buildroot/share/PlatformIO/ldscripts", ldname).resolve())
    for i, flag in enumerate(env["LINKFLAGS"]):
        if "-Wl,-T" in flag:
            env["LINKFLAGS"][i] = "-Wl,-T" + apath
        elif flag == "-T":
            env["LINKFLAGS"][i + 1] = apath

# Encrypt ${PROGNAME}.bin and save it with a new name. This applies (mostly) to MKS boards
# This PostAction is set up by offset_and_rename.py for envs with 'build.encrypt_mks'.
def encrypt_mks(source, target, env, new_name):
    key = [0xA3, 0xBD, 0xAD, 0x0D, 0x41, 0x11, 0xBB, 0x8D, 0xDC, 0x80, 0x2D, 0xD0, 0xD2, 0xC4, 0x9B, 0x1E, 0x26, 0xEB, 0xE3, 0x33, 0x4A, 0x15, 0xE4, 0x0A, 0xB3, 0xB1, 0x3C, 0x93, 0xBB, 0xAF, 0xF7, 0x3E]

    # If FIRMWARE_BIN is defined by config, override all
    mf = env["MARLIN_FEATURES"]
    if "FIRMWARE_BIN" in mf: new_name = mf["FIRMWARE_BIN"]

    fwpath = Path(target[0].path)
    fwfile = fwpath.open("rb")
    enfile = Path(target[0].dir.path, new_name).open("wb")

    try:
        # 1. Copy the unencrypted header (0-320)
        chunk1 = fwfile.read(320)
        enfile.write(chunk1)

        if len(chunk1) == 320:
            # 2. Encrypt the protected range (320-31040)
            # The key alignment works perfectly because 320 % 32 == 0
            chunk2 = bytearray(fwfile.read(30720))
            for i in range(len(chunk2)):
                chunk2[i] ^= key[i % 32]
            enfile.write(chunk2)

            # 3. Copy the rest of the file efficiently
            shutil.copyfileobj(fwfile, enfile)

    finally:
        fwfile.close()
        enfile.close()
        fwpath.unlink()

def add_post_action(action):
    env.AddPostAction(str(Path("$BUILD_DIR", "${PROGNAME}.bin")), action)
