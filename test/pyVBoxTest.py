"""Base class for all pyVBox unittests."""

import unittest

from pyVBox.HardDisk import HardDisk
from pyVBox.VirtualBox import VirtualBox
from pyVBox.VirtualMachine import VirtualMachine

class pyVBoxTest(unittest.TestCase):
    """Base class for all pyVBox unittests."""
    testHDpath = "appliances/TestHD.vdi"
    bogusHDpath = "/bogus/path"
    testVMpath = "appliances/TestVM.xml"
    bogusVMpath = "/bogus/path"

    def setUp(self):
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        """Unregister test HD and VM if they are registered."""
        # Do machine first to detach any HDs
        machine = VirtualMachine.open(self.testVMpath)
        if machine.registered():
            machine.openSession()
            machine.detachAllDevices()
            machine.closeSession()
            machine.unregister()
        if HardDisk.isOpen(self.testHDpath):
            harddisk = HardDisk.find(self.testHDpath)
            harddisk.close()

    
def main():
    """Run tests."""
    unittest.main()
