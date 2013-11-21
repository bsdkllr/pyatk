``mx-flashtool`` - i.MX Processor Bootstrap Toolkit
===================================================

``mx-flashtool`` is command line program aimed at replacing the
Advanced Toolkit (ATK) program distributed by Freescale
Semiconductor for their i.MX series processors.

This project is in no way affiliated with or supported by Freescale
Semiconductor.  For official support, you must use their officially
supplied tool.  Do not contact Freescale about this program.

See the README.rst file for more information on supported processors,
background, etc.

BSP Configuration - Initialization files, RAM kernels, etc.
-----------------------------------------------------------

``mx-flashtool`` understands a BSP (Board Support Package) configuration
file.  The default file is "bspinfo.conf" in the directory containing
"mx-flashtool.py" and is in INI format.

The BSP configuration file pulls together several pieces of information
required to bootstrap a given board or i.MX processor family:

 * Start address of SDRAM
 * End address of SDRAM (inclusive)
 * Origin (start address) of RAM kernel
 * USB VID and PID for the bootstrap mode of the i.MX processor

The SDRAM range and USB VID/PID generally will not change from board
to board with the same i.MX processor family (e.g., i.MX258).  However,
you are free to compile the ATK RAM kernel to start at any address.
To create a new BSP type 'fnop5643' based on the i.MX25, create a
new entry at the end of your "bspinfo.conf"::

 [fnob5643]
 description = Frob Your NOPs
 sdram_start = 0x80000000
 sdram_end = 0x8FFFFFFF
 ram_kernel_origin = 0x82005643
 usb_vid = 0x15a2
 usb_pid = 0x003a

In this example, the 'fnob5643' BSP uses a RAM kernel that was compiled
to start at 0x82005643 in SDRAM. It uses the standard USB VID and PID for
the i.MX25 bootstrap ROM.

Running ``mx-flashtool``
------------------------

The examples below assume you are running on Linux, but they should run fine
on Windows and Mac OS X assuming you substitute in the proper path structure
for your operating system.   It also assumes the "mx-flashtool.py" script is
in your PATH.

All invocations of ``mx-flashtool`` must include the BSP name of your board
in "bspinfo.conf" with the ``-b`` option::

 local:~/project $ mx-flashtool.py -b mx25


If you wish to specify a memory initialization file manually,
add the path to this file with the ``-i`` switch::

 local:~/project $ mx-flashtool.py -b mx25 -i mDDR_init.txt

The memory initialization file must contain a memory initialization
sequence in the same format as the ATK tool; one memory address per
line, with the value and access width in bits::

 # Start of mDDR initialization
 # Write a 32-bit quantity 0x00000004 to address 0xb8001010
 0xB8001010 0x00000004 32
 0xB8001004 0x002ddb3a 32
 0xb8001000 0x93210080 32
 # Write a 16-bit quantity 0x1234 to 0x80000400 in SDRAM
 0x80000400 0x1234 16
 # Write an 8-bit quantity 0xa3 to 0xb8001000
 0xb8001000 0xa3 8
 0x80000000 0x12344321 32

The contents of this file will vary from board to board depending on your
SDRAM banks, timing, and i.MX processor.  Consult your local EE for help.

Loading applications into SRAM or SDRAM
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``mx-flashtool`` can load and execute applications directly in memory
without the need for a RAM kernel.  This is useful for trivial bringup
tasks and for debugging a new RAM kernel flash implementation, for example.

To write and execute an application binary to memory address 0x80001234,
run the following command, substituting your board's initialization file
for 'init.txt'::

  local:~/project $ mx-flashtool.py -b mx25 -i init.txt -f APPL.BIN -a 0x80001234


Writing application into flash memory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``mx-flashtool`` can also work with flash memory, including the ability to
program flash memory from an arbitrary address.  To do this, you must provide
the tool with a RAM kernel binary that supports your board and flash memory
device.  If you do not already have an appropriate RAM kernel binary,
please refer to Freescale's manual and source code for building
a RAM kernel for your i.MX processor family.

It is important to note that for some flash parts (NAND comes to mind),
``mx-flashtool`` will likely only work if you are writing to the start
of a block.  This is because you must erase the flash part before you
program it, and the erase option generally only operates at the block
level (e.g., 128kB at a time).

To program your flash part starting at block 0 with file "APPLICATION.ROM",
run the following command, substituting your board's initialization file
for 'init.txt' and RAM kernel for 'rkl.bin'::

  local:~/project $ mx-flashtool.py -b mx25 -i init.txt -k rkl.bin --flash-file APPLICATION.ROM --flash-address 0

Depending on the speed of your flash part and the size of APPLICATION.ROM,
this make take some time.  ``mx-flashtool`` will erase, program, and verify
each block of flash until it has written all of APPLICATION.ROM.

``mx-flashtool`` provides no confirmation of its actions and will happily
erase your device with reckless abandon.  Please take care!

Reading/dumping flash memory
----------------------------

``mx-flashtool`` can also leverage the RAM kernel to dump flash memory.
The following command will dump 1 kB of a flash device, starting at address
0x20000 (block 1 of a part with 128 kB blocks)::

  local:~/project $ mx-flashtool.py -b mx25 -i init.txt -k rkl.bin --flash-dump 1024 --flash-address 0x20000

The command will dump the block to the screen in combined hex+ASCII format,
and also dump the data directly to "dump.bin".