# PINCE
<!---
TODO: Include build status with the title when test coverage increases and Travis is maintained
[![Build Status](https://travis-ci.org/korcankaraokcu/PINCE.svg?branch=master)](https://travis-ci.org/korcankaraokcu/PINCE)
-->
PINCE is a front-end/reverse engineering tool for the GNU Project Debugger (GDB), focused on games. However, it can be used for any reverse-engineering related stuff. PINCE is an abbreviation for "PINCE is not Cheat Engine". PINCE is in development right now, read [Features](#features) part of the project to see what is done and [Roadmap](CONTRIBUTING.md#roadmap) part to see what is currently planned. Also, please read [Wiki Page](https://github.com/korcankaraokcu/PINCE/wiki) of the project to understand how PINCE works.  

### [Feel free to join our discord server!](https://discord.gg/jVt3BzTSpz)  

*Disclaimer: Do not trust to any source other than [Trusted Sources](#trusted-sources) that claims to have the source code or package for PINCE and remember to report them **immediately***

*Disclaimer: **YOU** are responsible for your actions. PINCE does **NOT** take any responsibility for the damage caused by the users*

![pince1](https://github.com/user-attachments/assets/7344c33d-3ea7-408a-8a5b-793f0b4c78ec)
![pince2](https://github.com/user-attachments/assets/271cbbe7-b588-48e0-b939-f59e82f36812)
![pince3](https://github.com/user-attachments/assets/479b4f56-7b62-4100-a3d9-3f9cd11ff5b8)
![pince4](https://github.com/user-attachments/assets/08d8a6fe-6960-481b-9b55-aa550f860dc7)

# Features  
- **Memory scanning:** PINCE uses a specialized fork of [libscanmem](https://github.com/brkzlr/scanmem-PINCE) to scan the memory efficiently
- **Pointer scanning:** PINCE uses [PointerScanner-X](https://github.com/kekeimiku/PointerSearcher-X/) to scan pointers efficiently
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
  * **Tracing:** Almost the same with CE. But unlike CE, you can stop tracing whenever you want. Created from scratch with custom features instead of using gdb's built-in trace commands, this allows tracing to be done without the need of a gdbserver
  * **Collision Detection:** GDB normally permits setting unlimited watchpoints next to each other. But this behaviour leads to unexpected outcomes such as causing GDB or the inferior become completely inoperable. GDB also doesn't care about the number(max 4) or the size(x86->max 4, x64->max 8) of hardware breakpoints. Fortunately, PINCE checks for these problems whenever you set a new breakpoint and detects them before they happen and then inhibits them in a smart way. Lets say you want to set a breakpoint in the size of 32 bytes. But the maximum size for a breakpoint is 8! So, PINCE creates 4 different breakpoints with the size of 8 bytes and then chains them for future actions
- **Code Injection**
  * **Run-time injection:** Only .so injection is supported for now. In Memory View window, click Tools->Inject .so file to select the .so file. An example for creating .so file can be found in "libpince/Injection/". PINCE will be able to inject single line instructions or code caves in near future
- **GDB Console:** You can use the GDB Console to interact with GDB, it's on the top right in main window
- **libpince:** PINCE provides a reusable python library. You can either read the code or check the [Github Pages](https://korcankaraokcu.github.io/PINCE/) for documentation. Currently, libpince can be used via console by following [these instructions](https://github.com/korcankaraokcu/PINCE/issues/232#issuecomment-1872906700). In the future, it'll be directly integrated into PINCE when we develop the scripting engine (IDE for PINCE)
- **Extendable with .so files at runtime:** See [here](https://github.com/korcankaraokcu/PINCE/wiki/Extending-PINCE-with-.so-files)

# Installing and running PINCE
### Users:
- No need to install. Just grab the latest AppImage over at [Releases](https://github.com/korcankaraokcu/PINCE/releases) and run the following commands in the same folder:
```bash
chmod +x PINCE-x86_64.AppImage
sudo -E ./PINCE-x86_64.AppImage
```
- For Arch users, there's also an [AUR package](https://aur.archlinux.org/packages/pince-git/) but please bear in mind that **we're not the maintainers of the AUR package and it's not officially supported by us**.
  - Please do not open an Issue unless you can reproduce the issue you're experiencing on our AppImages or local install.

### Developers and Contributors:
- If you want to have a local install of PINCE so you can modify code or contribute with PRs, you'll have to use our installer script in the repo to setup a venv dev environment or do it yourself.
- To install local dev environment, run the following commands in a terminal anywhere you'd like to have the PINCE folder:
```bash
git clone --recursive https://github.com/korcankaraokcu/PINCE
sh PINCE/install.sh
```
- Make sure to check our [Officially supported platforms](#officially-supported-platforms) section below. Our installer might not work on distros that are not listed there, but it will still try to install using some package managers, just follow the on-screen instructions.
- If installer fails trying to install on an unsupported distro, you're on your own on trying to get the local dev environment up and running. Check `install.sh` to get an idea about what you might need.
- If you'd like to uninstall PINCE, just delete this folder, almost everything is installed locally. Config and user files of PINCE can be found in "~/.config/PINCE", you can manually delete them as well if you want.

***Notes:***
- If you are having problems with your default gdb version, you can use the `compile_gdb.sh` script to compile another version locally. Read the comments in it for more information
- Check https://github.com/korcankaraokcu/PINCE/issues/116 for a possible fix if you encounter `'GtkSettings' has no property named 'gtk-fallback-icon-theme'`

# Officially supported platforms
### AppImage
Our AppImage should run on any distro that is as new or newer than Ubuntu 22.04. Anything older than this might not work and is not officially supported.

### Local dev
Local dev installs of PINCE should technically run on any distro that comes with **Python 3.10+** and **PyQt 6.6+** installed or available in the package manager, but below is the list of distros that we officially support, as in we actively test on these and help with issues:
- Kubuntu 22.04+
- Arch Linux

Additionally the distros below are "partially" supported as our installer will try to install on them but ***they're not actively tested***:
- Debian 12+ (or Testing)
- Fedora 35+
- OpenSUSE

If you encounter issues installing and you're on one of these distros, feel free to open a PR fixing the installation process for your platform.

***Anything not listed here is not officially supported at all so you're on your own!*** If your distro has any of the above as its base, try to use the installer anyway and pick the relevant package manager. If this still does not work, sorry, you're on your own.

# Contributing
Want to help? Check out [CONTRIBUTING.md](CONTRIBUTING.md)

# License
GPLv3+. See [COPYING](COPYING) file for details

# Trusted Sources
  * [Official github page](https://github.com/korcankaraokcu/PINCE)
