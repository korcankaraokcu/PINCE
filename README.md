#PINCE  
PINCE is a gdb front-end/reverse engineering tool written in python3, C and pyqt5. PINCE is an abbreviation for "PINCE is not Cheat Engine". PINCE's GUI is heavily "inspired(;D)" by Cheat Engine.  
#Features   
- **NO BRAKES ON THIS TRAIN:** PINCE can run **ANY** gdb command without having to pause the inferior **[Postponed\Done]**
  * *Postpone reason:* Check wiki
- **Memory searching** **[Planned]**  (The plan is to use libscanmem by wrapping it with a gdb python script)
- **Variable Inspection&Modifcation** **[Done]**
  * **CheatEngine-like value type support:** Byte to 8 Bytes, Float, Double, Strings(including utf-8 and zero-terminate strings), Array of Bytes **[Done]**
  * **Symbol Recognition:** Try typing any widely used library function(such as malloc, open, printf, scanf etc) to AddAddressManually dialog **[Done]**
  * **Automatic Variable Allocation:** In AddAddressManually dialog, if your input is in quotes it's treated as a string, if your input is in curly brackets, it's treated as an array of variables(for instance: "asdf"=string, {0x00ffba42}=integer(4byte), {0x00000023,0x00513245,..}=array of 2 integers. After pressing OK button PINCE will allocate memory for you to use that variable right away! **[Done]**
  * **Dynamic Address Table:** Drag&drop rows, ctrl+c&ctrl+v between independent PINCE processes, clipboard text analysis(PINCE will try to analyze the contents of the current clipboard and try to pick data from it to convert for address table) **[Planned]**
  * **Manual Address Table Update:** **[Done]**
  * **Smart casting:** PINCE lets you modify multiple different-type values together as long as the input is parsable. All parsing/memory errors are directed to the terminal **[Done]**
  * **Continuous Address Table Update:** You can adjust update timer or cancel updating by modifying settings. Non-stop version is Postponed\Quarterway Done **[Done\Only works when the inferior is stopped]**
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables **[Postponed\Quarterway Done]**
  * *Postpone reason:* These two features requires thread injection to the target or gdb and PINCE's injection methods are not perfect yet, I've already spent more(read:WAY MORE) time than I should on this, these features are not vital for now, also you have got the options to manually update the table and set the value manually already
- **Disassemble** **[Planned]**
- **Debugging** **[Working on it]**
  * Can interrupt and continue the inferior, Check wiki for instructions
- **Code Injection** **[Done?]**
  * Check wiki
- **GDB Console** **[Done]**
  * Is the power of PINCE not enough for you? Then you can use the gdb console provided by PINCE, it's on the top right in main window
- **Simplified/Optimized gdb command alternatives** **[Working on it]**
  * Custom scripts instead of using gdb's x command for reading memory **[Done]**
  * Custom scripts instead of using gdb's set command for modifying memory **[Done]**

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
#####*You can skip this part if you already have gdb 7.11.1 with python3 support and libcc1.so from gcc-6 is correctly located*  
Download the latest source from [here](http://ftp.gnu.org/gnu/gdb/gdb-7.11.1.tar.gz), then install packages required for gdb
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
sudo cp libcc1.so.0.0.0 libcc1.so
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
- 18/06/2016 : PINCE now supports all-stop mode instead of non-stop mode
- 21/06/2016 : Variable Inspection&Modification is finished
  


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
  * Torchlight 2
  * Skullgirls
  * Steam
  * Firefox
  * WINE Games
    * FTL
    * Undertale
    * Hearthstone(It interrupts itself with SIGUSR1 whenever continued, implementing signal passing on PINCE might be very useful in future)
