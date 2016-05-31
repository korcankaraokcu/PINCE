#PINCE  
PINCE is a gdb front-end/reverse engineering tool written in python3, C and pyqt5. PINCE is an abbreviation for "PINCE is not Cheat Engine". PINCE's GUI is heavily "inspired(;D)" by Cheat Engine.  
#Features   
- **NO BRAKES ON THIS TRAIN:** PINCE can run **ANY** gdb command without having to pause the inferior **[Done]**
- **Memory searching** **[Planned]**  (The plan is to use libscanmem by wrapping it with a gdb python script)
- **Variable Inspection** **[Working on it]**
  * **CheatEngine-like value type support:** Byte to 8 Bytes, Float, Double, Strings(including utf-8 and zero-terminate strings), Array of Bytes **[Done]**
  * **Symbol Recognition:**Try typing any widely used library function(such as malloc, open, printf, scanf etc) to AddAddressManually dialog **[Done]**
  * **Automatic String Conversion:**If you type a string in quotes to AddAddressManually dialog, PINCE can convert it to any other type and after pressing OK button PINCE will allocate memory for you to use that string right away! **[Done]**
  * **Dynamic Address Table:** **[Working on it]**
  * **Manual Address Table Update:** **[Done]**
  * **Continuous Address Table Update:** **[Working on it]**
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables **[Working on it]**
- **Disassemble** **[Planned]**
- **Debugging** **[Planned]**
- **Code Injection** **[Working on it]**
  * PINCE can inject any code to a running process without pausing it
- **Simplified/Optimized gdb command alternatives** **[Working on it]**
  * Custom scripts instead of using gdb's x command for reading memory **[Done]**

#Building  
To run PINCE, run this command chain then compile gdb if necessary:  
  
```
sudo apt-get install python3-setuptools  
sudo apt-get install python3-pip  
sudo apt-get install python3-pyqt5  
sudo pip3 install psutil  
sudo pip3 install pexpect  
sudo apt-get install clang  
sudo apt-get install g++-multilib  
```  
###**Compiling the most recent gdb version with python support**  
#####*You can skip this part if you already have gdb 7.1.1 with python3 support and libcc1.so from gcc-6 is correctly located*  
Download the latest source from [here](http://ftp.gnu.org/gnu/gdb/gdb-7.11.tar.gz), then install packages required for gdb
```
sudo apt-get install libreadline-dev  
sudo add-apt-repository ppa:ubuntu-toolchain-r/test  
sudo apt-get update  
sudo apt-get install gcc-6  
```
Then ```cd``` to the source file you downloaded and run:  
```CC=gcc-6 ./configure --prefix=/usr --with-system-readline --with-python=python3 && make && sudo make -C gdb install```  
Then move the contents of gdb/data-directory to /usr/share/gdb by doing:  
```sudo cp -R gdb/data-directory/* /usr/share/gdb/```  
Finally relocate libcc1.so by doing:
```
cd /usr/lib/x86_64-linux-gnu/
cp libcc1.so.0.0.0 libcc1.so
```
#####Relocating PINCE files  
Create the file ```.gdbinit``` in your home directory and add the line ```set auto-load safe-path /``` to it  
Then ```cd``` to PINCE/linux-inject directory and simply run ```make```  
Finally, ```cd``` to PINCE directory and run ```sudo python3 PINCE.py```  

###For developers:  
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
  


*my method's success ratio was around %70, ```linux-inject```'s ratio is very close to %100. Well... at least working on code injection by myself for 2 months taught me very valuable lessons about linux internals, gdb, some standard libraries and the most importantly, ptrace.  
[Update-18/05/2016 : ```linux-inject```'s ratio is close to %100 only when attaching to small processes, it dramatically decrases(around %30-40) when attaching to the bigger processes]  
[Update-24/05/2016 : Thread injection to gdb itself works %100 of the time with a small gdb script and it enables the automatic address table update but it might crash gdb later on, needs extra research]

#License
GPLv3

#Supported platforms
- **Platforms tested so far:**
  * Kubuntu 14.04 & 16.04
  * Archlinux
- **Games&Applications tested so far:**
  * KMines
  * Torchlight 2(linux-inject fucks this up time to time, researching alternatives)
  * Steam
  * Firefox(PINCE crashes it after detach time to time, blame gdb for it, not me)
