import gdb
import threading
from time import sleep
import os


# a thread that updates the address table constantly
def table_update_thread():
    inferior = gdb.selected_inferior()
    pid = inferior.pid
    directory_path = "/tmp/PINCE-connection/" + str(pid)
    recv_file = directory_path + "/PINCE-to-GDB.txt"
    send_file = directory_path + "/GDB-to-PINCE.txt"
    status_file = directory_path + "/status.txt"
    abort_file = directory_path + "/abort.txt"
    PINCE_pid = ""
    while PINCE_pid is "":
        try:
            initialize = open(status_file, "r")
            PINCE_pid = initialize.read()
            initialize.close()
        except:
            sleep(0.001)
    PINCE_dir = "/proc/" + PINCE_pid
    while True:
        status = open(status_file, "w")
        status.write("sync-request-recieve")
        status.close()
        sleep(0.4)

        # abort.txt is created by PINCE to tell the GDB to quit
        try:
            exit = open(abort_file)
            exit.close()
            return
        except:
            pass

        # check if PINCE is still alive
        if not os.path.exists(PINCE_dir):
            return

        recv = open(recv_file, "r")
        # readed=recv.read()
        recv.close()
        send = open(send_file, "w")
        send.write(PINCE_pid)
        send.close()


t1 = threading.Thread(target=table_update_thread)
t1.setDaemon(True)
t1.start()
