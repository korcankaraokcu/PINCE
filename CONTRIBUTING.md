# Code Structure
- [PINCE.py](./PINCE.py) - The main file, it contains everything from GUI logic to libpince communication. A chonky boi, will be trimmed in the future
- [PINCE.sh](./PINCE.sh) - Launch script
- [install_pince.sh](./install_pince.sh) - Installation script
- [compile_ts.sh](./compile_ts.sh) - Gathers translation information from various sources and compiles them into ts files
- [fix_ts.py](./fix_ts.py) - Fixes line information issue, used within [compile_ts.sh](./compile_ts.sh)
- [install_gdb.sh](./install_gdb.sh) - PINCE normally uses system GDB but in cases where system GDB is unavailable, this script is used to compile GDB locally
- [GUI](./GUI) - Contains Qt Designer forms and their respective codes along with utility functions and custom Qt classes
- [media](./media) - Contains media files such as logos and icons
- [tr](./tr) - Contains translation constants
- [i18n](./i18n) - Contains translation files. `ts` files are created with Qt Linguist and [compile_ts.sh](./compile_ts.sh), `qm` files are created within the last section of [install_pince.sh](./install_pince.sh)
- ### **[libpince](./libpince)**
  - [debugcore.py](./libpince/debugcore.py) - Everything related to communicating with GDB and debugging
  - [utils.py](./libpince/utils.py) - Contains generic utility functions such as parsing, file creation, documentation etc
  - [typedefs.py](./libpince/typedefs.py) - Contains all constants and variable definitions
  - [regexes.py](./libpince/regexes.py) - Contains regexes for parsing GDB output and other things
  - [injection](./libpince/injection) - An example for injecting .so files
  - ### **[gdb_python_scripts](./libpince/gdb_python_scripts)**
    - [gdbextensions.py](./libpince/gdb_python_scripts/gdbextensions.py) - Contains custom GDB commands
    - [gdbutils.py](./libpince/gdb_python_scripts/gdbutils.py) - Contains utility functions for GDB commands
    - [tests](./libpince/gdb_python_scripts/tests) - An example for .so extension, read more [here](https://github.com/korcankaraokcu/PINCE/wiki/Extending-PINCE-with-.so-files)

# Code Style
The rules are about the same with PEP-8, with some changes. While they are not strict, I'd like you to follow them for consistency
- Max characters per line: 120
- Variable naming for libpince:
  - Classes: PascalCase
  - Class members: snake_case
  - Variables: snake_case
  - Functions: snake_case
  - Constants: SCREAMING_SNAKE_CASE
  - Modules: flatcase
  - Standalone scripts: snake_case
- Variable naming for Qt:
  - Classes: PascalCase
  - Class members:
    - non-Qt: snake_case
    - Qt: objectType + PascalCase
    For example: `keySequenceEdit_Hotkey` in [PINCE.py](./PINCE.py)
  - Variables: snake_case
  - Functions:
    - non-Qt: snake_case
    - Qt: objectName + snake_case
    Here's an example: `keySequenceEdit_Hotkey_key_sequence_changed` in [PINCE.py](./PINCE.py)
  - Constants: SCREAMING_SNAKE_CASE
  - Modules: PascalCase
  - Standalone scripts: snake_case

For convenience, I'm using auto-format tool of vscode. Any modern IDE will most likely have an auto-formatting tool.
Readability and being clear is the most important aspect, so if you decide to not follow the rules, make sure that your code still reads nice and plays well with others.
If you feel unsure to which naming convention you should use, try to check out similar patterns in the code or just ask away in the PINCE discord server!

The reason behind Qt class member naming convention is that when this project first started, supported python version didn't have type hints.
So, to have an idea about the type of the variable we are working with, I've come up with that naming idea. It's an old habit if anything.
It could maybe replaced with something else after a refactorization

About the max characters per line, I used to use PyCharm when I first started this project years ago. 120 characters is a limit brought by PyCharm,
I've quit using PyCharm eventually but I think the limit makes the code look quite nice. PEP-8 suggests a limit of 79 characters, which is a bit too short to be frank.
So I think it's good to keep this old habit. This limit however, is not strict at all. A few characters passing the limit is ok, sometimes going for a newline
messes up the readability, trust your guts and decide for yourself

# UI Files
You need to have [Qt6 Designer](https://pkgs.org/search/?q=designer&on=files) and [pyuic6](https://pkgs.org/search/?q=pyuic6&on=files) installed. Here are the steps:
- Edit or create ui files with the designer and then save them
- After saving the files, use pyuic6 to convert them into py files: `pyuic6 SomeDialog.ui -o SomeDialog.py`

The py files that contains the same name with the ui files are auto-generated, please edit the ui files with designer instead of messing with the py files

# Translation
You need to have [Qt6 Linguist](https://pkgs.org/search/?q=linguist&on=files) and [pylupdate6](https://pkgs.org/search/?q=pylupdate6&on=files) installed. Here are the steps:
- To create a new translation file, use [compile_ts.sh](./compile_ts.sh) with the locale as the parameter, such as `sh compile.sh ja_JP`. This will create a ts file with the locale you entered.
You can skip this step if you only want to edit already existing files
- Edit ts files in [/i18n/ts](./i18n/ts) with the linguist and then save them. After saving the files, run the [compile_ts.sh](./compile_ts.sh) script.
This script fixes inconsistencies between Qt6 Linguist and pylupdate6, also removes line information so the git history stays cleaner
- To test your translations, use [install_pince.sh](./install_pince.sh). The last part of the installation script also compiles ts files to qm files so PINCE can process them.
When asked to recompile libscanmem, enter no

Make sure that you read the comments in [tr.py](./tr/tr.py). Some of the translations have caveats that might interest you

About the untranslated parts of the code, such as context menus of libpince reference widget. You'll see that some of the code serves as a placeholder that'll be
removed or replaced in the future. These are not marked as translatable as translating them would be a waste of time

**ATTENTION:** Make sure you read this part even if you aren't a translator:  
If you create or delete any Qt related string (for example, ui forms or translation constants in [tr.py](./tr/tr.py)), you must run [compile_ts.sh](./compile_ts.sh) so it updates the translations.
Not every string has to be translatable, if it's only printed on console, it can stay as is, in English. If it's shown to the user within a form, it should be translatable

# Logo
All logo requests should be posted in `/media/logo/your_username`. Instead of opening a new issue, pull request your logo files to that folder.
Your PR must include at least one png file named pince_small, pince_medium or pince_big, according to its size. So, a minimal PR will look like this:

`/media/logo/your_username/pince_big.png`

pince_big is interchangeable with pince_medium and pince_small
A full PR will look like this:
```
/media/logo/your_username/pince_big.png
/media/logo/your_username/pince_medium.png
/media/logo/your_username/pince_small.png
```

# Notes
Here are some notes that explains some of the caveats and hacks, they also include a timestamp. As we upgrade the libraries and the methods we are working with,
some of these notes might become obsolete. You are free to test and provide solutions to these tricks

- 27/3/2017 - All GUI classes that will be instanced multiple times must contain these code blocks to prevent getting removed by garbage collector:
```python
    global instances
    instances.append(self)

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)
```
If you need to only create one instance of a GUI class, use this instead to create the instance:
```python
    try:
        self.window.show()
    except AttributeError:
        self.window = WindowForm(self)  # self parameter is optional
        self.window.show()
    self.window.activateWindow()
```
If you need to pass self as a parameter, please don't use `super().__init__(parent=parent)` in the child class, it makes Qt hide the child window. Use this in the child instead:
```python
    super().__init__()
    self.parent = lambda: parent  # A quick hack to make other functions see the correct parent(). But Qt won't see it, so there'll be no bugs
```

- 28/8/2018 - All QMessageBoxes that's called from outside of their classes(via parent() etc.) must use 'QApplication.focusWidget()' instead of 'self' in their first parameter.
Refer to issue #57 for more information

- 23/11/2018 - Don't use get_current_item or get_current_row within currentItemChanged or currentChanged signals.
Qt doesn't update selected rows on first currentChanged or currentItemChanged calls

- 22/05/2023 - For QTableWidget and QTableView, disabling wordWrap and using ScrollPerPixel as the horizontal scroll mode can help the user experience.
Consider doing these when creating a new QTableWidget or QTableView

- 2/9/2018 - All functions with docstrings should have their subfunctions written after their docstrings. For instance:
```python
    def test():
        """documentation for test"""
        def subtest():
            return
        return
```
If test is declared like above, `test.__doc__` will return "documentation for test" correctly. This is the correct documentation
```python
    def test():
        def subtest():
            return
        """documentation for test"""
        return
```
If test is declared like above, `test.__doc__` will return a null string because subtest blocks the docstring. This is the wrong documentation
All functions that has a subfunction can be found with the regex `def.*:.*\s+def`

- 2/9/2018 - Seek methods of all file handles that read directly from the memory(/proc/pid/mem etc.) should be wrapped in a try/except block that catches both
OSError and ValueError exceptions. For instance:
```python
    try:
        self.memory.seek(start_addr)
    except (OSError, ValueError):
        break
```
OSError handles I/O related errors and ValueError handles the off_t limit error that prints "cannot fit 'int' into an offset-sized integer"

- 12/9/2018 - All namedtuples must have the same field name with their variable names. This makes the namedtuple transferable via pickle. For instance:
```python
    tuple_examine_expression = collections.namedtuple("tuple_examine_expression", "all address symbol")
```
- 6/10/2016 - HexView section of MemoryViewerWindow.ui: Changed listWidget_HexView_Address to tableWidget_HexView_Address in order to prevent possible future visual bugs.
Logically, it should stay as a listwidget considering it's functionality. But it doesn't play nice with the other neighboring tablewidgets in different pyqt versions,
forcing me to use magic numbers for adjusting, which is a bit hackish

# Roadmap
So, after learning how to contribute, you are wondering where to start now. You can either search for `TODO` within the code or pick up any task from the roadmap below.
These tasks are ordered by importance but feel free to pick any of them. Further details can be discussed in the PINCE discord server
- Implement libpince engine
- Implement multi-line code injection, this will also help with previously dropped inject_with_advanced_injection
- Migrate to Sphinx documentation from the custom libpince documentation
- Move GUI classes of PINCE.py to their own files
- Extend documentation to GUI parts. Libpince has 100% documentation coverage but GUI doesn't
- Use type hints(py 3.5) and variable annotations(py 3.6) when support drops for older systems
- Arrows for jump instructions based on disassembled output
- Flowcharts based on disassembled output
- Consider implementing a GUI for catching signals and syscalls. This is currently done via GDB Console
- Implement speedhack
- Implement unrandomizer
- Implement pointer-scan
- Automatic function bypassing(make it return the desired value, hook specific parts etc.)
- Implement auto-ESP&aimbot
- Implement thread info widget
- Implement multi selection for HexView
- Write at least one test for each function in libpince
- Refactorize memory write/read functions
- - ReferencedStringsWidgetForm refreshes the cache everytime the comboBox_ValueType changes, this creates serious performance issues if total results are more than 800k.
  Only update the visible rows to prevent this(check ```disassemble_check_viewport``` for an example)
- - Implement same system for the TrackBreakpointWidgetForm if necessary. Do performance tests
- - Consider using a class instead of primitive return types to store the raw bytes. This class should also include a method to display None type as red '??' text for Qt
- - Provide an option to cut BOM bytes when writing to memory with the types UTF-16 and UTF-32
- - Put a warning for users about replacement bytes for non UTF-8 types
- - Extend string types with LE and BE variants of UTF-16 and UTF-32
- - Change comboBox_ValueType string order to be ... String_UTF-8 String_Others if necessary
- - Implement a custom combobox class for comboBox_ValueType and create a context menu for String_Others, if it gets implemented
- Implement "Investigate Registers" button to gather information about the addresses registers point to
- Add the ability to track down registers and addresses in tracer(unsure)
- Implement CE's Ultimap-like feature for tracing data, dissect code data and raw instruction list.
Search for calls and store their hit counts to filter out the functions that haven't or have executed specific number of times.
Implement a flexible input field for the execution count. For instance, 2^x only searches for hit counts 2, 4, 8 and so on, 3x only searches for 3, 6, 9 etc.
([CE#358](https://github.com/cheat-engine/cheat-engine/issues/358))
- Extend search_referenced_strings with relative search
- Consider adding type guessing for the StackView
- Implement a psuedo-terminal for the inferior like edb does(idk if necessary, we don't usually target CLI games, up to debate)
- Try to optimize TrackBreakpoint and TrackWatchpoint return data structures further, adding an id field might simplify traversing of the tree, performance tests are required
- Implement extra MemoryViewerWindow tabs(not really critical right now, up to debate)
- ~~Consider removing the command file layer of IPC system for debugcore.send_command to speed up things~~
[Update-29/04/2018 : Delaying this until GDB/MI implements a native multiline command feature or improves ```interpreter-exec``` command to cover every single multiline command type(including ```define``` commands)]
- Implement developer mode in settings. Developer mode will include features like dissection of GUI elements on events such as mouse-over
- Add ability to include non-absolute calls for dissect code feature(i.e call rax). Should be considered after the first version release. Might be useful for multi-breakpoint related features
- Provide information about absolute addresses in disassemble screen
- All tables that hold large amount of data should only update the visible rows(check ```disassemble_check_viewport``` for an example)
