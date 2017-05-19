import unittest, argparse
from libPINCE import GDB_Engine, SysUtils

desc = 'Runs all unit tests by creating or attaching to a process'
ex = 'Example of Usage:' \
     + '\n\tsudo python3 run_tests.py -a kmines' \
     + '\n\tsudo python3 run_tests.py -c /usr/games/kmines -o="-v"'

parser = argparse.ArgumentParser(description=desc, epilog=ex, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-a", metavar="process_name", type=str, help="Attaches to the process with given name")
parser.add_argument("-c", metavar="file_path", type=str, help="Creates a new process with given path")
parser.add_argument("-o", metavar="options", type=str, default="",
                    help="Arguments that'll be passed to the inferior, only can be used with -c, optional")
parser.add_argument("-l", metavar="ld_preload_path", type=str, default="",
                    help="Path of the preloaded .so file, only can be used with -c, optional")

args = parser.parse_args()
if args.a:
    pid = SysUtils.process_name_to_pid(args.a)
    if pid == -1:
        parser.error("There's no process with the name " + args.a)
    if not GDB_Engine.can_attach(pid):
        parser.error("Failed to attach to the process with pid " + str(pid))
    GDB_Engine.attach(pid)
elif args.c:
    if not GDB_Engine.create_process(args.c, args.o, args.l):
        parser.error("Couldn't create the process with current args")
else:
    parser.error("Provide at least one of these arguments: -a or -c")
import sys

print(sys.argv)
unittest.main(module="tests.GDB_Engine_tests", exit=False, argv=[""])
unittest.main(module="tests.SysUtils_tests", exit=False, argv=[""])
unittest.main(module="tests.GuiUtils_tests", exit=False, argv=[""])
GDB_Engine.detach()
