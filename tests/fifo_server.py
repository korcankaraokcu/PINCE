import os
from time import sleep

fifo = open("asdf", "w").close()
os.mkfifo("qwer")
fifo2 = open("qwer", "r")
while True:
  print(fifo2.read())
  sleep(1)
  fifo = open("asdf", "w")
  fifo.write("keks")
  fifo.close()
fifo2.close()