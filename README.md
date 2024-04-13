# PINCE
<!---
TODO: Include build status with the title when test coverage increases and Travis is maintained
[![Build Status](https://travis-ci.org/korcankaraokcu/PINCE.svg?branch=master)](https://travis-ci.org/korcankaraokcu/PINCE)
-->
PINCE is a front-end/reverse engineering tool for the GNU Project Debugger (GDB), focused on games. However, it can be used for any reverse-engineering related stuff. PINCE is an abbreviation for "PINCE is not Cheat Engine". PINCE is in development right now, read [Features](#features) part of the project to see what is done and [Roadmap](CONTRIBUTING.md#roadmap) part to see what is currently planned. Also, please read [Wiki Page](https://github.com/korcankaraokcu/PINCE/wiki) of the project to understand how PINCE works.  

### [Feel free to join our discord server!](https://discord.gg/jVt3BzTSpz)  

*Disclaimer: Do not trust to any source other than [Trusted Sources](#trusted-sources) that claims to have the source code or package for PINCE and remember to report them **immediately***

*Disclaimer: **YOU** are responsible for your actions. PINCE does **NOT** take any responsibility for the damage caused by the users*

Pre-release screenshots:

![pince0](https://user-images.githubusercontent.com/5638719/219640001-b99f96a2-bffb-4b61-99a1-b187713897e2.png)
![pince1](https://user-images.githubusercontent.com/5638719/219640254-40152be1-8e97-4d26-a313-62a56b9fe1a5.png)
![pince2](https://user-images.githubusercontent.com/5638719/219706426-56c233f5-b047-4a8f-b090-ab439b98ef3a.png)
![pince3](https://user-images.githubusercontent.com/5638719/219640353-bb733c19-9ce7-4baf-81ce-4306c658fbe6.png)
![pince4](https://user-images.githubusercontent.com/5638719/219640370-a73c1796-8d2b-4d31-a63c-aa0b41f9f608.png)
![pince5](https://user-images.githubusercontent.com/5638719/219640384-62a384c8-cc32-45ef-b975-e310674302c2.png)
![pince6](https://user-images.githubusercontent.com/5638719/219640402-e03768b3-4e88-4c75-9d73-29dfbb69b3c0.png)
![pince7](https://user-images.githubusercontent.com/5638719/219640469-8b496c67-b074-4c9a-9890-9e52227cf75d.png)
![pince8](https://user-images.githubusercontent.com/5638719/219640488-61a8df17-405b-45ae-9b29-f9d214eb8571.png)
![pince9](https://user-images.githubusercontent.com/5638719/219640522-85cac1a9-e425-4b4f-abeb-a61104caa618.png)

# Features  
- **Memory searching:** PINCE uses a specialized fork of [libscanmem](https://github.com/brkzlr/scanmem-PINCE) to search the memory efficiently
- **Background Execution:** PINCE uses background execution by default, allowing users to run GDB commands while process is running
- **Variable Inspection&Modification**
  * **CheatEngine-like value type support:** Currently supports all types of CE and scanmem along with extended strings(utf-8, utf-16, utf-32)
  * **Symbol Recognition:** See [here](https://github.com/korcankaraokcu/PINCE/wiki/GDB-Expressions)
  * **Automatic Variable Allocation:** See [here](https://github.com/korcankaraokcu/PINCE/wiki/GDB-Expressions)
  * **Dynamic Address Table:** Supports drag&drop, recursive copy&pasting&inserting and many more
  * **Smart casting:** PINCE lets you modify multiple different-type values together as long as the input is parsable. All parsing/memory errors are directed to the terminal
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables
- **Memory View**
  * **Assembler:** PINCE uses keystone engine to assemble code on the fly
  * **Dissect Code:** You can dissect desired memory regions to find referenced calls, jumps and strings. Disassemble screen will automatically handle the referenced data and show you if there's a referenced address in the current dissasemble view. It can be used from Tools->Dissect Code in the MemoryView window. Using its hotkey instead in the MemoryView window automatically dissects the currently viewed region. You can separately view referenced calls and strings after the search from View->Referenced Calls/Strings. *Note: If you decide to uncheck 'Discard invalid strings' before the search, PINCE will try to search for regular pointers as well*
  * **Bookmarking:** Bookmark menu is dynamically created when right clicked in the disassemble screen. So unlike Cheat Engine, PINCE lets you set unlimited number of bookmarks. List of bookmarks can also be viewed from View->Bookmarks in the MemoryView window. Commenting on an address automatically bookmarks it
  * **Modify on the fly:** PINCE lets you modify registers on the fly. Check [GDB expressions in the Wiki page](https://github.com/korcankaraokcu/PINCE/wiki/GDB-Expressions) for additional information
  * **Opcode Search:** You can search opcodes with python regular expressions. To use this feature, click Tools->Search Opcode in the MemoryView window
- **Debugging**
  * Has basic debugging features such as stepping, stepping over, execute till return, break, continue. Also has breakpoints, watchpoints and breakpoint conditions. Has advanced debugging utilities such as Watchpoint/Breakpoint Tracking and Tracing
  * **Chained Breakpoints:** Just like CE, PINCE allows you to set multiple, connected breakpoints at once. If an event(such as condition modification or deletion) happens in one of the breakpoints, other connected breakpoints will get affected as well
  * **Watchpoint Tracking:** Allows you to see which instructions have been accessing to the specified address, just like "What accesses/writes to this address" feature in CE
  * **Breakpoint Tracking:** Allows you to track down addresses calculated by the given register expressions at the specified instruction, just like "Find out what addresses this instruction accesses" feature in CE with a little addon, you can enter multiple register expressions, this allows you to check the value of "esi" even if the instruction is something irrelevant like "mov [eax],edx"
  * **Tracing:** Almost the same with CE. But unlike CE, you can stop tracing whenever you want. Created from scratch with shittons of custom features instead of using gdb's trace&collect commands because some people have too much time on their hands
  * **Collision Detection:** GDB normally permits setting unlimited watchpoints next to each other. But this behaviour leads to unexpected outcomes such as causing GDB or the inferior become completely inoperable. GDB also doesn't care about the number(max 4) or the size(x86->max 4, x64->max 8) of hardware breakpoints. Fortunately, PINCE checks for these problems whenever you set a new breakpoint and detects them before they happen and then inhibits them in a smart way. Lets say you want to set a breakpoint in the size of 32 bytes. But the maximum size for a breakpoint is 8! So, PINCE creates 4 different breakpoints with the size of 8 bytes and then chains them for future actions
- **Code Injection**
  * **Run-time injection:** Only .so injection is supported for now. In Memory View window, click Tools->Inject .so file to select the .so file. An example for creating .so file can be found in "libpince/Injection/". PINCE will be able to inject single line instructions or code caves in near future
- **GDB Console**
  * Is the power of PINCE not enough for you? Then you can use the gdb console provided by PINCE, it's on the top right in main window
- **Simplified/Optimized gdb command alternatives**
  * Custom scripts instead of using gdb's x command for reading memory
  * Custom scripts instead of using gdb's set command for modifying memory
- **libpince - A reusable python library**
  * PINCE provides a reusable python library. You can either read the code or check Reference Widget by clicking Help->libpince in Memory Viewer window to see docstrings. Contents of this widget is automatically generated by looking at the docstrings of the source files. PINCE has a unique parsing technique that allows parsing variables. Check the function get_variable_comments in utils for the details. This feature might be replaced with Sphinx in the future
- **Extendable with .so files at runtime**
  * See [here](https://github.com/korcankaraokcu/PINCE/wiki/Extending-PINCE-with-.so-files)

# Installing
```
git clone --recursive https://github.com/korcankaraokcu/PINCE
cd PINCE
sh install_pince.sh
```
~~For Archlinux, you can also use the [AUR package](https://aur.archlinux.org/packages/pince-git/) as an alternative~~ Currently outdated, use the installation script

If you like to uninstall PINCE, just delete this folder, almost everything is installed locally. Config and user files of PINCE can be found in "~/.config/PINCE", you can manually delete them if you want

***Notes:***
- If you are having problems with your default gdb version, you can use the `install_gdb.sh` script to install another version locally. Read the comments in it for more information
- Check https://github.com/korcankaraokcu/PINCE/issues/116 for a possible fix if you encounter `'GtkSettings' has no property named 'gtk-fallback-icon-theme'`

# Running PINCE  
Just run ```sh PINCE.sh``` in the PINCE directory

# Contributing
Want to help? Check out [CONTRIBUTING.md](CONTRIBUTING.md)

# License
GPLv3+. See [COPYING](COPYING) file for details

# Officially supported platforms
PINCE should technically run on any distro that comes with **Python 3.10+** and **PyQt 6.6+** installed or available in the package manager, but below is the list of distros that we officially support, as in we actively test on these and help with issues:
- Ubuntu 22.04+
- Debian 12+ (or Testing)
- Archlinux
- Fedora 35+

Should your distro not be officially supported, the installer can still try to install it for you by picking one of the base package managers appropriate for your distro but please **do not open an issue on GitHub** if it does not work for you.

If this happens and you can't figure out why, we might be able to guide you into making PINCE run in our Discord server, under the #issues channel, but remember that we only actively test the installer and PINCE on the distros listed above.

# Trusted Sources
  * [Official github page](https://github.com/korcankaraokcu/PINCE)
  * [AUR package for Archlinux](https://aur.archlinux.org/packages/pince-git/)
