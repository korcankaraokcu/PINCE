#PINCE  
PINCE is a gdb front-end/reverse engineering tool written in python3, C and pyqt5. PINCE is an abbreviation for "PINCE is not Cheat Engine". PINCE's GUI is heavily "inspired(;D)" by Cheat Engine.  
#Features   
- **NO BRAKES ON THIS TRAIN:** PINCE can run **ANY** gdb command without having to pause the inferior **[Done]**
- **Memory searching** **[Planned]**
- **Variable Inspection** **[Working on it]**
  * **CheatEngine-like value type support:** Byte to 8 Bytes, Float, Double, Strings(including utf-8 and zero-terminate strings), Array of Bytes **[Done]**
  * **Symbol Recognition:**Try typing any widely used library function(such as malloc, open, printf, scanf etc) to AddAddressManually dialog **[Done]**
  * **Automatic String Conversion:**If you type a string in quotes to AddAddressManually dialog, PINCE can convert it to any other type and after pressing OK button PINCE will allocate memory for you to use that string right away! **[Done]**
  * **Dynamic Address Table:** **[Done]**
  * **Continuous Address Table Update:** **[Working on it]**
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables **[Working on it]**
- **Disassemble** **[Planned]**
- **Debugging** **[Planned]**
- **Code Injection** **[Working on it]**
  * PINCE can inject any code to a running process without pausing it

#Building  
To run PINCE, simply run this command chain:  
  
```
sudo apt-get install python3-pip  
sudo apt-get install gdb  
sudo apt-get install python3-pyqt5  
sudo apt-get install pyqt5-dev-tools
sudo pip3 install psutil  
sudo pip3 install pexpect
```  
  
Then create the file ```.gdbinit``` in your home directory and add the line ```set auto-load safe-path /``` to it  
Finally, ```cd``` to PINCE directory and run ```sudo python3 PINCE.py```
  
#History
- A few weeks till 17/01/2016 : Learned GDB, process of analysis
- 17/01/2016-22/01/2016 : Basic design, grasping of Python3 and Pyqt5, proof-testing
- 22/01/2016 : First commit
- 19/02/2016 : Moved to Github from Bitbucket
- 25/02/2016 : First successful implementation of thread injection(A new age dawns!)
