"""
Portable ATK communications channel implementation - base interface
"""
# Copyright (c) 2012-2013 Harry Bock <bock.harryw@gmail.com>
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

CHANNEL_TYPE_UART = 0
CHANNEL_TYPE_USB  = 1

class ATKChannelI(object):
    # The RAM kernel expects channels to be identified by the following
    # enumeration:
    # enum ChannelType {
    #   UART,
    #   USB,
    # };
    # Default to UART.  The implementor of this interface is responsible
    # for setting it to USB if required.
    def __init__(self):
        self._ramkernel_channel_type = CHANNEL_TYPE_UART

    @property
    def chantype(self):
        """ Return the RAM kernel channel type, as an integer. """
        return self._ramkernel_channel_type

    def open(self):
        """
        Open the communication channel.
        """
        raise NotImplementedError()

    def close(self):
        """
        Close the communication channel.
        """
        raise NotImplementedError()

    def read(self, length):
        """
        Read exactly ``length`` bytes from underlying ATK communication
        channel.  :exc:`ChannelReadTimeout` is raised if ``length`` bytes
        could not be read.
        """
        raise NotImplementedError()

    def write(self, data):
        """
        Write ``data`` binary string to underlying ATK communication
        channel.

        :exc:`ChannelWriteTimeout` is raised if ``data`` could not be written
        in its entirety.
        """
        raise NotImplementedError()

class ChannelTimeout(Exception):
    """ Exception indicating a timeout reading from or writing to the channel occurred. """
    pass

class ChannelReadTimeout(ChannelTimeout):
    """ Exception indicating a timeout reading from the channel occurred. """
    def __init__(self, read_attempt_length, actual_data_read = ""):
        #: The actual data that was able to be read from the channel.
        self.actual_data_read = actual_data_read
        #: The amount of data requested to be read from the channel.
        self.read_attempt_length = read_attempt_length

    def __str__(self):
        return ("Read request of length %u bytes timed out; "
                "received %u bytes." % (self.read_attempt_length, len(self.actual_data_read)))

class ChannelWriteTimeout(ChannelTimeout):
    """ Exception indicating a timeout writing to the channel occurred. """
    pass
