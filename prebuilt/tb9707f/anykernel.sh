### AnyKernel3 Ramdisk Mod Script
## osm0sis @ xda-developers
##
## TB-9707F (Lenovo Legion Y700 gen1 / kona / SM8250)
##
## Kernel-only flash: Image.gz and the boot DTB are replaced, the stock
## ramdisk is kept byte-for-byte and the dtbo partition is never written.
## The panel (Novatek NT36523) and touch (NVT-ts over SPI) device tree nodes
## live in dtbo, so touching it would leave the device without a display.

### AnyKernel setup
# global properties
properties() { '
kernel.string=TB-9707F kona kernel (Legion Y700)
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=TB-9707F
device.name2=TB9707F
device.name3=
device.name4=
device.name5=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; } # end properties


### AnyKernel install
## boot shell variables
BLOCK=boot;
IS_SLOT_DEVICE=1;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;

# import functions/variables and setup patching - see for reference (DO NOT REMOVE)
. tools/ak3-core.sh;

# boot install
split_boot; # skip ramdisk unpack/repack: nothing in the ramdisk needs patching
flash_boot; # builds boot-new.img from Image.gz + dtb and flashes the active slot
## end boot install
