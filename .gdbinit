set disassembly-flavor intel
set target-async 1
set pagination off
set non-stop on
set $pince_injection_failed = 1
set $pince_debugging_mode = 0

# PINCE usually can run commands without having need to stop but it's good to take precaution in case of failure
define hook-x
  if $pince_injection_failed == 1
    interrupt
  end
end
    
define hookpost-x
  if $pince_debugging_mode == 0
    c &
  end
end