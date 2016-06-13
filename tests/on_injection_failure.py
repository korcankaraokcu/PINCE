class IgnoreErrors(gdb.Command):
    def __init__(self):
      super(IgnoreErrors, self).__init__("ignore-errors", gdb.COMMAND_USER)
    
    def invoke (self, arg, from_tty):
        try:
            gdb.execute ("interrupt", from_tty)
        except:
            pass
        try:
            gdb.execute (arg, from_tty)
        except:
            pass
        try:
            gdb.execute ("c &", from_tty)
        except:
            pass

IgnoreErrors()