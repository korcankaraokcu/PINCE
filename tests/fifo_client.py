import os
from time import sleep

os.mkfifo("asdf")
fifo = open("asdf", "r")
while True:
  sleep(1)
  fifo2=open("qwer", "w")
  fifo2.write("zxcv")
  fifo2.close()
  print(fifo.read())
fifo.close()