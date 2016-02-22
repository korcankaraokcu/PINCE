#PINCE  
PINCE is a reverse engineering tool written in python3 and pyqt5. It can do  
  
- Memory searching(planned)
- Variable Inspection(working on it)
- Disassemble(planned)
- Debugging(planned)
- Code Injection(planned)
  
PINCE is a abbreviation for "PINCE is not Cheat Engine". PINCE's GUI is heavily "inspired(;D)" by Cheat Engine.  

#Building  
To run PINCE, simply run this command chain:  
  
```
sudo pip3 install psutil  
sudo pip3 install pexpect  
sudo apt-get install gdb  
sudo apt-get install python3-pyqt5  
sudo apt-get install pyqt5-dev-tools  
```  
  
Then ```cd``` to PINCE directory and run ```sudo python3 PINCE.py```
  
#History
- A few weeks till 17/01/2016 : Learned GDB, process of analysis
- 17/01/2016-22/01/2016 : Basic design, grasping of Python3 and Pyqt5, proof-testing
- 22/01/2016 : First commit
- 19/02/2016 : Moved to Github from Bitbucket
