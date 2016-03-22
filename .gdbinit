set disassembly-flavor intel
set target-async 1
set pagination off
set non-stop on
define keks
	set $lel=0
	while($lel<10)
		x/x 0x00400000
		set $lel = $lel+1
