set disassembly-flavor intel
define hook-stop
  echo <--STOPPED-->
end
define hook-continue
  echo <--RUNNING-->
end