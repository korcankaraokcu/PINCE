# PINCE
<!---
TODO: Include build status with the title when test coverage increases and a GitHub Actions test workflow is added
[![Release AppImage](https://github.com/korcankaraokcu/PINCE/actions/workflows/release_appimage.yml/badge.svg)](https://github.com/korcankaraokcu/PINCE/actions/workflows/release_appimage.yml)
-->
PINCE is a front-end/reverse engineering tool for the GNU Project Debugger (GDB), focused on games. However, it can be used for any reverse-engineering related stuff. PINCE is an abbreviation for "PINCE is not Cheat Engine".

Read [Features](#features) part of the project to see what is done and [Roadmap](CONTRIBUTING.md#roadmap) part to see what is currently planned. Also, please read [Wiki Page](https://github.com/korcankaraokcu/PINCE/wiki) of the project to understand how PINCE works.  

### [Feel free to join our discord server!](https://discord.gg/jVt3BzTSpz)  

*Disclaimer: Do not trust to any source other than this GitHub repo that claims to have the source code or package for PINCE and remember to report them **immediately***

*Disclaimer: **YOU** are responsible for your actions. PINCE does **NOT** take any responsibility for the damage caused by the users*

![pince1](https://github.com/user-attachments/assets/7344c33d-3ea7-408a-8a5b-793f0b4c78ec)
![pince2](https://github.com/user-attachments/assets/271cbbe7-b588-48e0-b939-f59e82f36812)
![pince3](https://github.com/user-attachments/assets/479b4f56-7b62-4100-a3d9-3f9cd11ff5b8)
![pince4](https://github.com/user-attachments/assets/08d8a6fe-6960-481b-9b55-aa550f860dc7)

# Features  
- **Memory and pointer scanning:** PINCE uses [libmemscan](https://github.com/brkzlr/libmemscan) to scan the memory efficiently
- **Speedhack:** Both Linux native and WINE/Proton compatible speedhack built-in. No **`LD_PRELOAD`** or other libraries necessary
- **Libpince Engine:** Powerful scripting engine built-in that allows you to perform advanced tasks such as code injection
- **Background Execution:** PINCE uses background execution by default, allowing users to run GDB commands while process is running
- **Variable Inspection&Modification**
  * **CheatEngine-like value type support:** Currently supports all types of CE and memscan along with extended strings(utf-8, utf-16, utf-32)
  * **Symbol Recognition:** See [here](https://github.com/korcankaraokcu/PINCE/wiki/GDB-Expressions)
  * **Automatic Variable Allocation:** See [here](https://github.com/korcankaraokcu/PINCE/wiki/GDB-Expressions#allocation-using-expressions)
  * **Dynamic Address Table:** Supports drag&drop, recursive copy&pasting&inserting and many more
  * **Smart casting:** PINCE lets you modify multiple different-type values together as long as the input is parsable. All parsing/memory errors are directed to the terminal
  * **Variable Locking:** PINCE lets you freeze(constantly write a value to memory cell) variables
- **Sessions:** Save and restore your work as a session file (**`.pct`**), including the address table, bookmarks, free-form session notes and structures
- **Memory View**
  * **Assembler:** PINCE uses keystone engine to assemble code on the fly
  * **Dissect Code:** You can dissect desired memory regions to find referenced calls, jumps and strings. Disassemble screen will automatically handle the referenced data and show you if there's a referenced address in the current dissasemble view. It can be used from **`Tools -> Dissect Code`** in the MemoryView window. Using its hotkey instead in the MemoryView window automatically dissects the currently viewed region. You can separately view referenced calls and strings after the search from **`View -> Referenced Calls/Strings`**. *Note: If you decide to uncheck 'Discard invalid strings' before the search, PINCE will try to search for regular pointers as well*
  * **Bookmarking:** Bookmark menu is dynamically created when right clicked in the disassemble screen. PINCE also lets you set an unlimited number of bookmarks. List of bookmarks can also be viewed from **`View -> Bookmarks`** in the MemoryView window. Commenting on an address automatically bookmarks it
  * **Modify on the fly:** PINCE lets you modify registers on the fly. Check [GDB expressions in the Wiki page](https://github.com/korcankaraokcu/PINCE/wiki/GDB-Expressions) for additional information
  * **Instructions Search:** You can search instructions with python regular expressions. To use this feature, click **`Tools -> Search Instructions`** in the MemoryView window
  * **Search Functions:** Search the target's defined functions and symbols with python regular expressions and jump straight to their addresses. Click **`View -> Functions`** in the MemoryView window
  * **Memory Regions:** View the target's memory map and jump to any of its regions. Click **`View -> Memory Regions`** in the MemoryView window
  * **Restore Instructions:** Revert instructions you've assembled over back to their original bytes. Click **`View -> Restore Instructions`** in the MemoryView window
  * **Call Function:** Call a function inside the target process with a GDB expression and inspect its return value. Click **`Tools -> Call Function`** in the MemoryView window
- **Mono/IL2CPP Dissection**
  * Dissect the managed runtime of Mono and IL2CPP games. Browse classes along with their fields and methods, read static and instance field values, and drill into nested types. Accessible from **`Tools -> Dissect Mono/IL2CPP`** in the MemoryView window. Works for both Linux native and WINE/Proton processes
  * **Find Instances:** Locate live instances of a class in the target process
  * **Invoke Methods:** Call methods directly on a chosen instance and inspect the returned value
  * **Export to Structures:** Turn a dissected class into a PINCE structure for reuse
- **Structures:** Define and view memory structures with named, typed members. Build them by hand or generate them automatically from a dissected Mono/IL2CPP class, then overlay them on any address to inspect memory through the structure
- **Debugging**
  * Has basic debugging features such as stepping, stepping over, execute till return, break, continue. Also has breakpoints, watchpoints and breakpoint conditions. Has advanced debugging utilities such as Watchpoint/Breakpoint Tracking and Tracing
  * **Chained Breakpoints:** Just like CE, PINCE allows you to set multiple, connected breakpoints at once. If an event(such as condition modification or deletion) happens in one of the breakpoints, other connected breakpoints will get affected as well
  * **Watchpoint Tracking:** Allows you to see which instructions have been accessing to the specified address, just like "What accesses/writes to this address" feature in CE
  * **Breakpoint Tracking:** Allows you to track down addresses calculated by the given register expressions at the specified instruction, just like "Find out what addresses this instruction accesses" feature in CE with a little addon, you can enter multiple register expressions, this allows you to check the value of "esi" even if the instruction is something irrelevant like "mov [eax],edx"
  * **Tracing:** Almost the same with CE. But unlike CE, you can stop tracing whenever you want. Created from scratch with custom features instead of using gdb's built-in trace commands, this allows tracing to be done without the need of a gdbserver
  * **Collision Detection:** GDB normally permits setting unlimited watchpoints next to each other. But this behaviour leads to unexpected outcomes such as causing GDB or the inferior become completely inoperable. GDB also doesn't care about the number(max 4) or the size(x86->max 4, x64->max 8) of hardware breakpoints. Fortunately, PINCE checks for these problems whenever you set a new breakpoint and detects them before they happen and then inhibits them in a smart way. Lets say you want to set a breakpoint in the size of 32 bytes. But the maximum size for a breakpoint is 8! So, PINCE creates 4 different breakpoints with the size of 8 bytes and then chains them for future actions
  * **Stack Trace:** View the call stack of the stopped thread along with the return and frame addresses of each frame. Click **`View -> StackTrace Info`** in the MemoryView window
  * **Signal Handling:** Configure how the inferior handles each signal, choosing whether GDB stops on it and whether it's passed on to the program, just like GDB's `handle` command. Accessible from PINCE's Settings
- **Code Injection**
  * **Run-time injection:** Both native `.so` injection and WINE/Proton DLL injection are supported. In the MemoryView window, click **`Tools -> Inject .so file`** or **`Tools -> Inject DLL file`** to select the file
- **GDB Console:** You can use the GDB Console to interact with GDB, it's on the top right in main window
- **libpince library:** PINCE provides a reusable python library. You can either read the code or check the [Github Pages](https://korcankaraokcu.github.io/PINCE/) for documentation. Additionally, libpince can be used via console by following [these instructions](https://github.com/korcankaraokcu/PINCE/issues/232#issuecomment-1872906700).

# Installing and running PINCE
### Users
No need to install anything. Just grab the latest AppImage over at [Releases](https://github.com/korcankaraokcu/PINCE/releases) and mark it as executable. You can then double click on the AppImage or run it through terminal, however you prefer.

To mark as executable, either:
- Run the following command in terminal in the same folder as the downloaded AppImage: `chmod +x PINCE-x86_64.AppImage`
- Or you can right-click on the AppImage, click on Properties and tick "Allow this file to run as a program" under "Permissions"
  - The last step might be different depending on your desktop environment, but most of them should have similar words so just make sure to edit permissions to allow running as executable.

### Developers and Contributors
- If you want to have a local install of PINCE so you can modify code or contribute with PRs, you'll have to use our installer script in the repo to setup a venv dev environment or do it yourself.
- To install local dev environment, run the following commands in a terminal anywhere you'd like to have the PINCE folder:
```bash
git clone --recursive https://github.com/korcankaraokcu/PINCE
sh PINCE/install.sh
```
- Make sure to check our [Officially supported platforms](#officially-supported-platforms) section below. Our installer might not work on distros that are not listed there, but it will still try to install using some package managers, just follow the on-screen instructions.
- If installer fails trying to install on an unsupported distro, you're on your own on trying to get the local dev environment up and running. Check `install.sh` to get an idea about what you might need.
- If you'd like to uninstall PINCE, just delete this folder, almost everything is installed locally. Config and user files of PINCE can be found in "~/.config/PINCE", you can manually delete them as well if you want.

### Notes
- Check https://github.com/korcankaraokcu/PINCE/issues/116 for a possible fix if you encounter `'GtkSettings' has no property named 'gtk-fallback-icon-theme'`

# Officially supported platforms
### AppImage
Our AppImage should run on any distro that is as new or newer than Ubuntu 22.04. Anything older than this might not work and is not officially supported.

### Local dev
Local dev installs of PINCE should technically run on any distro that comes with **Python 3.11+** and **PyQt 6.11+** installed or available in the package manager, but below is the list of distros that we officially support, as in we actively test on these and help with issues:
- Kubuntu 22.04+
- Arch Linux (**Not AUR**)

Additionally the distros below are "partially" supported as our installer will try to install on them but ***they're not actively tested***:
- Debian 12+ (or Testing)
- Fedora 35+
- OpenSUSE

### Notes
- If you encounter issues installing local dev and you're on one of these distros, feel free to open a PR fixing the installation process for your platform.
- If your distro has any of the above as its base, you can still try to use the installer anyway and pick the relevant package manager. If this still does not work then sorry, you're on your own.
- ***DO NOT open issues if you cannot repro using a local dev build on a supported distro from above or AppImage!***
  - **This includes AUR or NIXPKGS. We don't care about the issues present on these packaged versions unless you can repro them on AppImage (or also local dev if you're on Arch).**

# Contributing
Want to help? Check out [CONTRIBUTING.md](CONTRIBUTING.md)

# License
GPLv3+. See [COPYING](COPYING) file for details
