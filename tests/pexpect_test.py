import pexpect

child=pexpect.spawnu('gdb --interpreter=mi', cwd="/home/azginporsuk/PINCE/")
child.setecho(False)
#child.cwd="/home/azginporsuk/Pictues/"
child.expect("(gdb)")
child.sendline("pwd")
child.expect("(gdb)")
child.expect("(gdb)")
child.expect("(gdb)")
child.expect("(gdb)")
print(child.before)
child.close()
