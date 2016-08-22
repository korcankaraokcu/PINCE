#PINCE  
PINCE is a gdb front-end/reverse engineering tool focused on games, but it can be used for any reverse-engineering related stuff. PINCE is an abbreviation for "PINCE is not Cheat Engine". PINCE's GUI is heavily "inspired(;D)" by Cheat Engine. PINCE is in development right now, read features part of the project to see what is planned and what is done for now. Also, please read [Wiki Page](https://github.com/korcankaraokcu/PINCE/wiki) of the project to understand how PINCE works.  
  
Pre-release screenshots:  
![](screenshots/pince.png)
![](screenshots/pince1.png)
![](screenshots/pince2.png)
![](screenshots/pince3.png)
#Features  
- **Memory searching** **[Planned]**  (The plan is to use libscanmem by wrapping it with a gdb python script)
- **Variable Inspection&Modification** **[Done/Basic]**
  * **CheatEngine-like value type support:** Byte to 8 Bytes, Float, Double, Strings(including utf-8 and zero-terminate strings), Array of Bytes **[Done]**
  * **Symbol Recognition:** Try typing any widely used library function(such as malloc, open, printf, scanf etc) to AddAddressManually dialog **[Done]**
  * **Automatic Variable Allocation:** In AddAddressManually dialog, if your input is in quotes it's treated as a string, if your input is in curly brackets, it's treated as an array of variables(for instance: "asdf"=string, {0x00ffba42}=integer(4byte), {0x00000023,0x00513245,..}=array of 2 integers. After pressing OK button PINCE will allocate memory for you to use that variable right away! **[Done]**
  * **Dynamic Address Table:** Drag&drop rows, ctrl+c&ctrl+v between independent PINCE processes, clipboard text analysis(PINCE will try to analyze the contents of the current clipboard and try to pick data from it to convert for address table) **[Planned]**
  * **Manual Address Table Update:** **[Done]**
  * **Smart casting:** PINCE lets you modify multiple different-type values together as long as the input is parsable. All parsing/memory errors are directed to the terminal **[Done]**
  * **Continuous Address Table Update:** You can adjust update timer or cancel updating by modifying settings. Non-stop version is Postponed\Quarterway Done **[Done\Only works when the inferior is stopped]**
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables **[Postponed\Quarterway Done]**
  * *Postpone reason:* These two features requires thread injection to the target or gdb and PINCE's injection methods are not perfect yet, I've already spent more(read:WAY MORE) time than I should on this, these features are not vital for now, also you have got the options to manually update the table and set the value manually already
- **Memory View** **[Done/Basic]**
  * **Infinite Scrolling:** PINCE automatically disassembles the next available instruction(s) on mouse wheel/scrollbar move. Instruction count can be changed from settings. Hex View also supports this feature **[Done]**
  * **Following:** If you press [space], PINCE automatically analyzes the selected instruction and if any location changing instruction is found, PINCE disassembles the address that's pointed by the instruction **[Done]**
  * **Travel History:** PINCE records your previous location when you jump to an address explicitly(e.g by pressing [space] or using "Go to expression" etc.). Right click->Back to go back to your previous location(s) **[Done]**
  * **Bookmarking:** Bookmark menu is dynamically created when right clicked in the disassemble screen. So unlike Cheat Engine, PINCE lets you set unlimited number of bookmarks. List of bookmarks can also be viewed from View->Bookmarks in the MemoryView window. Commenting on an address automatically bookmarks it. **[Done]**
  * **Modify on the fly:** PINCE lets you modify registers on the fly. Unlike CE, you can also change XMM and FPU registers. **[Done]**  
- **Debugging** **[Working on it]**
  * Can interrupt and continue the inferior, Check wiki for instructions
- **Code Injection** **[Working on it]**
  * **Pre-attach injection:** Only .so files are supported. Read Wiki **[Done]**
  * **Run-time injection:** PINCE can inject single line instructions or code caves **[Planned]**
- **GDB Console** **[Done]**
  * Is the power of PINCE not enough for you? Then you can use the gdb console provided by PINCE, it's on the top right in main window
- **Simplified/Optimized gdb command alternatives** **[Working on it]**
  * Custom scripts instead of using gdb's x command for reading memory **[Done]**
  * Custom scripts instead of using gdb's set command for modifying memory **[Done]**
- **libPINCE- A reusable python library** **[Current Status:*Reusable for FP* , *Refactoring for OOP*]**
  * PINCE provides a reusable python library. I'll write a fully-documented guide about how to use it as soon as the project finishes at basic level. Until that moment, I'll keep developing libPINCE as modular as possible  
- **Automatic Trainer Generation:** **[Planned]**  
  * PINCE provides a trainer auto-generated from current address table on demand by using libPINCE and PyQT5 together

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
#####*You can skip this part if you already have gdb 7.11.1 with python3 support, but it's strongly recommended to compile from source instead of downloading from repos because python version of gdb may mismatch with default interpreter and it usually causes ImportError within gdb scripts*  
Download the latest source from [here](http://ftp.gnu.org/gnu/gdb/gdb-7.11.1.tar.gz), then install packages required for gdb
```
sudo apt-get install python3-dev  
sudo apt-get install gcc  
```
Then ```cd``` to the source file you downloaded and run:  
```CC=gcc ./configure --prefix=/usr --with-python=python3 && make && sudo make -C gdb install```  
Note: If gdb says something about missing python files, move the contents of gdb/data-directory to /usr/share/gdb:  
```sudo cp -R gdb/data-directory/* /usr/share/gdb/```  
#####Relocating PINCE files  
Create the file ```.gdbinit``` in your home directory and add the line ```set auto-load safe-path /``` to it  
Then ```cd``` to PINCE/linux-inject directory and simply run ```make```(IMPORTANT: If you have a 32bit linux distro, run ```make x86``` instead)  
Finally, ```cd``` to PINCE directory and run ```sudo python3 PINCE.py```  
#####*Debian Only:*  
Run ```gksudo python3 PINCE.py``` instead

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
- 21/08/2016 : Memory View is finished
  


*my method's success ratio was around %70, ```linux-inject```'s ratio is very close to %100. Well... at least working on code injection by myself for 2 months taught me very valuable lessons about linux internals, gdb, some standard libraries and the most importantly, ptrace.  
[Update-18/05/2016 : ```linux-inject```'s ratio is close to %100 only when attaching to small processes, it dramatically decrases(around %30-40) when attaching to the bigger processes]  
[Update-24/05/2016 : Thread injection to gdb itself works %100 of the time with a small gdb script and it enables the automatic address table update but it might crash gdb later on, needs extra research]

#License
GPLv3. See COPYING file for details

#Contact Information
Korcan Karaokçu <korcankaraokcu@gmail.com>  
Çağrı Ulaş <cagriulas@gmail.com>  

#Supported platforms
- **Platforms tested so far:**
  * Kubuntu 14.04 & 16.04(Also tested on x86 variants)
  * Debian 8.5
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
