import gdb
from time import time
i=0
t0=time()
while i<20:
	try:
		gdb.execute('x/4b 0x00400000')
	except:
		gdb.execute('echo ??')
	i=i+1
t1=time()
print(t1-t0)
