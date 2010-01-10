#!/usr/bin/env python
"""pyVBox utility to control VirtualBox VMs.
"""

import pyVBox.VirtualBoxException
from pyVBox.HardDisk import HardDisk
from pyVBox.VirtualMachine import VirtualMachine

import atexit
import optparse
import os.path
import sys
import traceback

#----------------------------------------------------------------------
#
# Output functions
#

# Default = 1, 0 = quiet, 2 = verbose
verbosityLevel = 1

def errorMsg(msg):
    sys.stderr.write(msg + "\n")

def handle_exception(e, msg=None):
    sys.stderr.write("Error: ")
    if msg is not None:
        sys.stderr.write(msg + ": ")
    sys.stderr.write(str(e) + "\n")
    if verbosityLevel > 1:
        traceback.print_exc()

def message(msg):
    if verbosityLevel > 0:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

def verboseMsg(msg):
    if verbosityLevel > 1:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

#----------------------------------------------------------------------
#
# Commands

class Command:
    """Base class for all commands."""
    usage = "<command> <arguments"

    @classmethod
    def invoke(cls, args):
        """Invoke the command.

        Should return exit code for program.
        Should be overriden by child class."""
        pass

    registered_commands = {}

    @classmethod
    def register_command(cls, name, command):
        """Register the binding between name and command class"""
        cls.registered_commands[name] = command

    @classmethod
    def lookup_command_by_name(cls, name):
        """Given a name, return associated registered command class"""
        return cls.registered_commands[name]

    @classmethod
    def string_to_size(cls, string):
        """Given a string representing a size return size as long.

        Size is in MB by default. Supported suffixes: MB, GB, TB, PB"""
        import re

        match = re.match("(\d+)(\w\w)?\Z", string)
        if not match:
            raise Exception("Could not parse size \"%s\"" % string)
        number = long(match.group(1))
        suffix = match.group(2)
        if suffix:
            suffix = suffix.lower()
            suffixes = {
                "mb" : 1,
                "gb" : 1024,
                "tb" : 1048576,
                "pb" : 1073741824,
                }
            if not suffixes.has_key(suffix):
                raise Exception("Unrecognized suffix \"%s\"" % suffix)
            number *= suffixes[suffix]
        return number

class AttachCommand(Command):
    """Attach hard disks to a virtual machine"""
    usage = "attach <VM name> <HD files>"
  
    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        if len(args) < 1:
            raise Exception("Missing virtual machine argument")
        vm = VirtualMachine.find(args.pop(0))
        if len(args) < 1:
            raise Exception("Missing hard disk filenames")
        for hd in args:
            if HardDisk.isRegistered(hd):
                hd = HardDisk.find(hd)
            else:
                hd = HardDisk.open(hd)
            verboseMsg("Attaching %s" % hd)
            vm.attachDevice(hd)
        return 0

Command.register_command("attach", AttachCommand)
    
class BootVMCommand(Command):
    """Boot a virtual machine and eject it after power down"""
    usage = "boot <VM settings file> [<HD files>]"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        mode = "gui" # or "vrdp"
        if len(args) < 1:
            raise Exception("Missing virtual machine argument")
        vm = VirtualMachine.open(args.pop(0))
        atexit.register(vm.eject)
        if not vm.isRegistered():
            vm.register()
        for hd in args:
            hd = HardDisk.find(hd)
            vm.attachDevice(hd)
        verboseMsg("Starting VM in %s mode" % mode)
        vm.powerOn(type=mode)
        # Wait until machine is running or we have a race condition
        # where it still might be down when we call waitUntilDown()
        vm.waitUntilRunning()
        verboseMsg("VM started. Waiting until power down...")
        vm.waitUntilDown()
        verboseMsg("VM powered down.")
        # Let atexit clean up
        return 0

Command.register_command("boot", BootVMCommand)

class CreateHDCommand(Command):
    """Create a hard disk"""
    usage = "createhd <size> <path>"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        if len(args) < 1:
            raise Exception("Missing size argument")
        size = cls.string_to_size(args.pop(0))
        if len(args) < 1:
            raise Exception("Missing path argument")
        path = args.pop(0)
        verboseMsg("Creating Hard Disk at %s with size %d" % (path, size))
        HardDisk.createWithStorage(path, size)
        return 0

Command.register_command("createhd", CreateHDCommand)

class EjectCommand(Command):
    """Eject a virtual machine"""
    usage = "boot <VM name>"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        if len(args) == 0:
            raise Exception("Missing virtual machine name argument");
        for name in args:
            vm = VirtualMachine.find(name)
            verboseMsg("Ejecting %s" % vm)
            vm.eject()
        return 0

Command.register_command("eject", EjectCommand)

class HelpCommand(Command):
    """Provide help"""
    usage = "help [<commands>]"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        if len(args) > 0:
            for name in args:
                cmd = Command.lookup_command_by_name(name)
                message("%10s: %s" % (name, cmd.__doc__))
                message("%10s  usage: %s" % ("", cmd.usage))
        else:
            message("Available commands:")
            for name in Command.registered_commands:
                cmd = Command.lookup_command_by_name(name)
                message("%10s: %s" % (name, cmd.__doc__))

Command.register_command("help", HelpCommand)

class PauseCommand(Command):
    """Pause a running VM"""
    usage = "pause [<VM settings filenames>]"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        mode = "gui"
        if len(args) == 0:
            raise Exception("Missing virtual machine name argument");
        vm = VirtualMachine.find(args.pop(0))
        vm.pause()
        return 0

Command.register_command("pause", PauseCommand)

class RegisterCommand(Command):
    """Register a VM"""
    usage = "register [<VM settings filenames>]"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        if len(args) == 0:
            raise Exception("Missing virtual machine name argument");
        for filename in args:
            vm = VirtualMachine.open(args.pop(0))
            if vm.isRegistered():
                errorMsg("VM \"%s\" is already registered." % vm)
            else:
                verboseMsg("Registering VM %s" % vm)
                vm.register()
        return 0

Command.register_command("register", RegisterCommand)

class ResumeCommand(Command):
    """Resume a paused VM"""
    usage = "resume [<VM settings filenames>]"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        mode = "gui"
        if len(args) == 0:
            raise Exception("Missing virtual machine name argument");
        vm = VirtualMachine.find(args.pop(0))
        vm.resume()
        return 0

Command.register_command("resume", ResumeCommand)

class StartCommand(Command):
    """Start a VM"""
    usage = "start <VM name>"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        mode = "gui"
        if len(args) == 0:
            raise Exception("Missing virtual machine name argument");
        vm = VirtualMachine.find(args.pop(0))
        vm.powerOn(type=mode)

Command.register_command("start", StartCommand)

class UnregisterCommand(Command):
    """Unregister a VM"""
    usage = "unregister [<VM settings filenames>]"

    @classmethod
    def invoke(cls, args):
        """Invoke the command. Return exit code for program."""
        if len(args) == 0:
            raise Exception("Missing virtual machine name argument");
        for filename in args:
            vm = VirtualMachine.find(args.pop(0))
            if vm.isRegistered():
                verboseMsg("Unregistering VM %s" % vm)
                vm.unregister()
            else:
                errorMsg("VM \"%s\" is not registered." % vm)
        return 0

Command.register_command("unregister", UnregisterCommand)

#----------------------------------------------------------------------

def main(argv=None):
    global verbosityLevel

    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] <command> [<arguments>]"
    version= "%prog 1.0"
    parser = optparse.OptionParser(usage=usage, version=version)
    parser.add_option("-q", "--quiet", dest="verbosityLevel",
                      action="store_const", const=0,
                      help="surpress all messages")
    parser.add_option("-v", "--verbose", dest="verbosityLevel",
                      action="store_const", const=2,
                      help="be verbose")
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("missing command")

    if options.verbosityLevel != None:
        verbosityLevel = options.verbosityLevel
        verboseMsg("Setting verbosity level to %d" % verbosityLevel)

    try:
        command = Command.lookup_command_by_name(args.pop(0))
        status = command.invoke(args)
    except Exception, e:
        handle_exception(e)
        return 1
    return status

if __name__ == "__main__":
    sys.exit(main())
