import gdb


# This function is used to avoid errors in gdb scripts, because gdb scripts stop working when encountered an error
def issue_command(command):
    try:
        gdb.execute(command)
    except:
        gdb.execute('echo ??\n')
