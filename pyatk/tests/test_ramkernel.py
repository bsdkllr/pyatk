import unittest

from pyatk.channel.mock import MockChannel
from pyatk import ramkernel

class RAMKernelTests(unittest.TestCase):
    def setUp(self):
        self.channel = MockChannel()
        self.rkl = ramkernel.RAMKernelProtocol(self.channel)

    def test_flash_init_error(self):
        self.channel.queue_rkl_response(ramkernel.FLASH_ERROR_INIT, 0, 0)
        with self.assertRaises(ramkernel.CommandResponseError) as cm:
            self.rkl.flash_initial()

        self.assertEqual(cm.exception.ack, ramkernel.FLASH_ERROR_INIT)
        self.assertEqual(cm.exception.command, ramkernel.CMD_FLASH_INITIAL)
        self.assertEqual(cm.exception.length, 0)

    def test_flash_get_capacity(self):
        self.channel.queue_rkl_response(ramkernel.ACK_SUCCESS, 0xbeef, 2057)
        self.assertEqual(self.rkl.flash_get_capacity(), 2057)
        self.channel.queue_rkl_response(ramkernel.ACK_SUCCESS, 0xbeef, 0x1FFFF)
        self.assertEqual(self.rkl.flash_get_capacity(), 0x1FFFF)

    def test_getver(self):
        # Test CMD_GETVER responses of various shapes and sizes, including
        # with payloads containing non-ASCII data.
        for imx_version, flash_model in (
            (0xface, "HAL 9000"),
            (0xbeef, "Taste the biscuit"),
            (0x2057, "Silly rabbit Freescale's for kids"),
            (0xfeed, "So I should \x1bprobably sleep\xAF\x99 at some point \x00tonight"),
        ):
            self.channel.queue_rkl_response(ramkernel.ACK_SUCCESS, imx_version,
                                            len(flash_model), flash_model)

            ver, flash = self.rkl.getver()
            self.assertEqual(ver, imx_version)
            self.assertEqual(flash, flash_model)

    def test_erase(self):
        """ Test the flash_erase API with no callback specified. """
        block_size = 0x20000

        for block_index in xrange(50):
            self.channel.queue_rkl_response(ramkernel.ACK_FLASH_ERASE, block_index, block_size)
        self.channel.queue_rkl_response(ramkernel.ACK_SUCCESS, 0, 0)

        self.rkl.flash_erase(0x0, 1)

    def test_erase_callback(self):
        """ Test flash_erase with erase_callback specified. """
        callback_data = []
        block_size = 0x20000

        # Queue 50 block erase responses, each with a different block size.
        # Generally the block size returned by RKL is fixed, but if it is not,
        # we should be sending the right value.
        for block_index in xrange(50):
            self.channel.queue_rkl_response(ramkernel.ACK_FLASH_ERASE,
                                            block_index,
                                            block_size + block_index)
        self.channel.queue_rkl_response(ramkernel.ACK_SUCCESS, 0, 0)

        # Close over callback_data to make sure it is called correctly.
        def erase_cb(block_idx, block_sz):
            callback_data.append((block_idx, block_sz))

        # Flash erase doesn't care how many bytes you specify, or the start address.
        # We're just testing how it handles RKL proto responses.
        self.rkl.flash_erase(0x0, 1, erase_callback=erase_cb)

        self.assertEqual(len(callback_data), 50)
        for index, (cb_block_idx, cb_block_sz) in zip(xrange(50), callback_data):
            self.assertEqual(cb_block_idx, index)
            self.assertEqual(cb_block_sz, block_size + index)

    def test_erase_partial_error(self):
        """ Test flash_erase error handling - partial erase """
        callback_data = []
        block_size = 0x20000

        # queue up 25 good partial responses followed by an error.
        # The callback should be called for each of the 25 good responses.
        for block_index in xrange(25):
            self.channel.queue_rkl_response(ramkernel.ACK_FLASH_ERASE,
                                            block_index,
                                            block_size + block_index)
        self.channel.queue_rkl_response(ramkernel.FLASH_ERROR_PART_ERASE, 0, 0)

        # Close over callback_data to make sure it is called correctly.
        def erase_cb(block_idx, block_sz):
            callback_data.append((block_idx, block_sz))

        # Ensure an exception is raised
        with self.assertRaises(ramkernel.CommandResponseError) as cm:
            self.rkl.flash_erase(0x0, 1, erase_callback=erase_cb)
        self.assertEqual(cm.exception.ack, ramkernel.FLASH_ERROR_PART_ERASE)
        self.assertEqual(cm.exception.command, ramkernel.CMD_FLASH_ERASE)

        self.assertEqual(len(callback_data), 25)
        for index, (cb_block_idx, cb_block_sz) in zip(xrange(25), callback_data):
            self.assertEqual(cb_block_idx, index)
            self.assertEqual(cb_block_sz, block_size + index)

    def test_erase_initial_error(self):
        """ Test flash_erase error handling - no blocks erased """
        callback_data = []
        self.channel.queue_rkl_response(ramkernel.FLASH_ERROR_OVER_ADDR, 0, 0)

        # Close over callback_data to make sure it is called correctly.
        def erase_cb(block_idx, block_sz):
            callback_data.append((block_idx, block_sz))

        # Ensure an exception is raised
        with self.assertRaises(ramkernel.CommandResponseError) as cm:
            self.rkl.flash_erase(0x0, 1, erase_callback=erase_cb)
        self.assertEqual(cm.exception.ack, ramkernel.FLASH_ERROR_OVER_ADDR)
        self.assertEqual(cm.exception.command, ramkernel.CMD_FLASH_ERASE)

        # The callback should never have been called.
        self.assertEqual(len(callback_data), 0)

    def test_flash_dump(self):
        """
        Ensure flash_dump in normal operation works correctly - multiple FLASH_PARTLY responses,
        checksum validation, etc.
        """
        data = "testing random \x00 data 1 2 \x03"
        cksum = ramkernel.calculate_checksum(data)
        self.channel.queue_rkl_response(ramkernel.ACK_FLASH_PARTLY, cksum, len(data), data)
        # NOTE: the RKL main() never sends ACK_SUCCESS for CMD_FLASH_DUMP - only
        # a sequence of ACK_FLASH_PARTLY responses.

        # Don't care about the address or requested size, we're mocking it
        dump_data = self.rkl.flash_dump(0x0000, len(data))

        self.assertEqual(data, dump_data)

        test_data =  (
            "testing random \x00 data 1 2 \x03",
            "cold wind to valhalla",
            "\xff" * 1024,
            "\x00" * 2048
        )
        # Multipart
        for data_chunk in test_data:
             cksum = ramkernel.calculate_checksum(data_chunk)
             self.channel.queue_rkl_response(ramkernel.ACK_FLASH_PARTLY, cksum, len(data_chunk), data_chunk)

        total_test_data = "".join(test_data)
        # Don't care about the address.
        dump_data = self.rkl.flash_dump(0x0000, len(total_test_data))

        self.assertEqual("".join(test_data), dump_data)

    def test_flash_dump_checksum_error(self):
        """
        Ensure flash_dump handles checksum errors correctly, by raising ramkernel.ChecksumError.
        flash_dump should set ChecksumError internal values correctly.
        """
        data = "testing random \x00 data 1 2 \x03"
        real_cksum = ramkernel.calculate_checksum(data)
        fake_cksum = (real_cksum + 1) & 0xFFFF
        self.channel.queue_rkl_response(ramkernel.ACK_FLASH_PARTLY, fake_cksum, len(data), data)

        with self.assertRaises(ramkernel.ChecksumError) as cm:
            # Don't care about the address or requested size, we're mocking it
            self.rkl.flash_dump(0x0000, len(data))
        self.assertEqual(cm.exception.expected_checksum, fake_cksum)
        self.assertEqual(cm.exception.checksum, real_cksum)

        ## Test with initial successes, then a failed checksum
        test_data =  (
            "testing random \x00 data 1 2 \x03",
            "cold wind to valhalla",
            "\xff" * 1024,
            "\x00" * 2048
        )
        for data_chunk in test_data:
            # Calculate the real checksum for these chunks
             cksum = ramkernel.calculate_checksum(data_chunk)
             self.channel.queue_rkl_response(ramkernel.ACK_FLASH_PARTLY, cksum, len(data_chunk), data_chunk)
        # Now for the bad checksum...
        data = "testing random \x00 data 1 2 \x03"
        real_cksum = ramkernel.calculate_checksum(data)
        fake_cksum = (real_cksum + 1) & 0xFFFF
        self.channel.queue_rkl_response(ramkernel.ACK_FLASH_PARTLY, fake_cksum, len(data), data)
        self.channel.queue_rkl_response(ramkernel.ACK_SUCCESS, 0, 0)

        total_data_length = len("".join(test_data + (data,)))
        with self.assertRaises(ramkernel.ChecksumError) as cm:
            self.rkl.flash_dump(0x0000, total_data_length)

        self.assertEqual(cm.exception.expected_checksum, fake_cksum)
        self.assertEqual(cm.exception.checksum, real_cksum)

    def test_flash_dump_partial_error(self):
        """
        Ensure flash_dump handles partial read errors correctly.
        """
        data = "testing random \x00 data 1 2 \x03"
        cksum = ramkernel.calculate_checksum(data)
        self.channel.queue_rkl_response(ramkernel.ACK_FLASH_PARTLY, cksum, len(data), data)
        self.channel.queue_rkl_response(ramkernel.FLASH_ERROR_READ, 0, 0)

        with self.assertRaises(ramkernel.CommandResponseError) as cm:
            # We ask for more size than the first response gives, so we try to read again
            # and encounter the FLASH_ERROR_READ.
            self.rkl.flash_dump(0x0000, len(data) * 2)
        self.assertEqual(cm.exception.ack, ramkernel.FLASH_ERROR_READ)
        self.assertEqual(cm.exception.command, ramkernel.CMD_FLASH_DUMP)

    def test_flash_dump_initial_error(self):
        """
        Ensure flash_dump handles initial read error correctly.
        """
        self.channel.queue_rkl_response(ramkernel.FLASH_ERROR_OVER_ADDR, 0, 0)

        with self.assertRaises(ramkernel.CommandResponseError) as cm:
            # Don't care about the address or requested size, we're mocking it
            self.rkl.flash_dump(0x0000, 0x400)
        self.assertEqual(cm.exception.ack, ramkernel.FLASH_ERROR_OVER_ADDR)
        self.assertEqual(cm.exception.command, ramkernel.CMD_FLASH_DUMP)

    def test_flash_program_arguments(self):
        """ Test sanity checks on flash_program """
        class AVeryLargeObject(object):
            def __init__(self, length):
                self.length = length
            def __len__(self):
                return self.length

        self.assertRaises(ValueError, self.rkl.flash_program, -1, "asdf")
        self.assertRaises(ValueError, self.rkl.flash_program, 0,
                          AVeryLargeObject(ramkernel.FLASH_PROGRAM_MAX_WRITE_SIZE + 1))
        self.assertRaises(ValueError, self.rkl.flash_program, 0, "")
        self.assertRaises(ValueError, self.rkl.flash_program, 0, "asdf", file_format = -1)
