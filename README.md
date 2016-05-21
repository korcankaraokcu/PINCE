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
  * **Manual Address Table Update:** **[Done]**
  * **Continuous Address Table Update:** **[Working on it]**
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables **[Working on it]**
- **Disassemble** **[Planned]**
- **Debugging** **[Planned]**
- **Code Injection** **[Working on it]**
  * PINCE can inject any code to a running process without pausing it

#Building  
To run PINCE, simply run this command chain:  
  
```
sudo apt-get install python3-setuptools  
sudo apt-get install python3-pip  
sudo apt-get install gdb  
sudo apt-get install python3-pyqt5  
sudo pip3 install psutil  
sudo pip3 install pexpect  
sudo apt-get install clang  
sudo apt-get install g++-multilib  
```  
Then create the file ```.gdbinit``` in your home directory and add the line ```set auto-load safe-path /``` to it  
Then ```cd``` to PINCE/linux-inject directory and simply run ```make```  
Then copy the file ```PINCE/gdb-python-scripts/ScriptUtils.py``` to your home directory (blame gdb for this unnecessary step, not me)  
Finally, ```cd``` to PINCE directory and run ```sudo python3 PINCE.py```  

For developers:  
```
sudo apt-get install qttools5-dev-tools (qt5 form designer)
sudo apt-get install pyqt5-dev-tools (pyuic5)
```
  
#History
- A few weeks till 17/01/2016 : Learned GDB, process of analysis
- 17/01/2016-22/01/2016 : Basic design, grasping of Python3 and Pyqt5, proof-testing
- 22/01/2016 : First commit
- 19/02/2016 : Moved to Github from Bitbucket
- 25/02/2016 : First successful implementation of thread injection(A new age dawns!)[Update-08/05/2016 : PINCE now uses ```linux-inject``` instead of injection method of mine]*  
  


*my method's success ratio was around %70, ```linux-inject```'s ratio is very close to %100. Well... at least working on code injection by myself for 2 months taught me very valuable lessons about linux internals, gdb, some standard libraries and the most importantly, ptrace. [Update-18/05/2016 : ```linux-inject```'s ratio is close to %100 only when attaching to small processes, it dramatically decrases(around %30-40) when attaching to the bigger processes]

#License
GPLv3
