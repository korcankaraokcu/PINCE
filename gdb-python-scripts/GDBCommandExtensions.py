import gdb
class ReadSingleAddress (gdb.Command):
       """Greet the whole world."""
     
       def __init__ (self):
         super (ReadSingleAddress, self).__init__ ("pince-read-single-address", gdb.COMMAND_USER)
     
       def invoke (self, arg, from_tty):
         print ("Hello, World!")
         print(arg)
         print(arg.split(","))

ReadSingleAddress()
