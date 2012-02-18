# Copyright (c) 2012, Harry Bock <bock.harryw@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Freescale i.MX ATK RAM kernel protocol implementation
"""
import struct
import binascii

HEADER_MAGIC = 0x0606

## RKL NAND flash commands
CMD_FLASH_INITIAL      = 0x0001
CMD_FLASH_ERASE        = 0x0002
CMD_FLASH_DUMP         = 0x0003
CMD_FLASH_PROGRAM      = 0x0004
CMD_FLASH_PROGRAM_UB   = 0x0005
CMD_FLASH_GET_CAPACITY = 0x0006

## RKL eFUSE commands
CMD_FUSE_READ     = 0x0101
CMD_FUSE_SENSE    = 0x0102
CMD_FUSE_OVERRIDE = 0x0103
CMD_FUSE_PROGRAM  = 0x0104

## RKL common commands
CMD_RESET    = 0x0201
CMD_DOWNLOAD = 0x0202
CMD_EXECUTE  = 0x0203
CMD_GETVER   = 0x0204

## Extended commands
CMD_COM2USB  = 0x0301
CMD_SWAP_BI  = 0x0302
CMD_FL_BBT   = 0x0303
CMD_FL_INTLV = 0x0304
CMD_FL_LBA   = 0x0305

ACK_SUCCESS = 0x0000
ACK_FAILED  = 0xffff

class CommandResponseError(Exception):
    def __init__(self, command, ackcode):
        super(CommandResponseError, self).__init__()
        #: Command code that generated this error.
        self.command = command
        #: Response code from the device.
        self.ack = ackcode

    def __str__(self):
        return "Command 0x%04X failed: ack code 0x%04X" % (self.command, self.ack)

class RAMKernelProtocol(object):
    def __init__(self, channel):
        self.channel = channel

    def _send_command(self, command,
                      address = 0x00000000,
                      param1  = 0x00000000,
                      param2  = 0x00000000,
                      wait_for_response = True):
        rawcmd = struct.pack(">HHIII", HEADER_MAGIC, command, address, param1, param2)
        self.channel.write(rawcmd)

        if wait_for_response:
            response = self.channel.read(8)
            ack, checksum, length = struct.unpack(">HHI", response)
            if length > 0:
                payload = self.channel.read(length)
            else:
                payload = ""

            if ack != ACK_SUCCESS:
                raise CommandResponseError(command, ack)

            return checksum, payload

    def getver(self):
        imx_type, flash_model = self._send_command(CMD_GETVER)
        print "imx, flash model =", imx_type, repr(flash_model)

    def reset(self):
        self._send_command(CMD_RESET, wait_for_response = False)
