# linux-inject
**Tool for injecting a shared object into a Linux process**

* Provides the Linux equivalent of using `CreateRemoteThread()` on Windows to inject a DLL into a running process

* Performs injection using `ptrace()` rather than `LD_PRELOAD`, since the target process is already running at the time of injection

* Supports x86, x86_64, and ARM

* Does not require the target process to have been built with `-ldl` flag, because it loads the shared object using `__libc_dlopen_mode()` from libc rather than `dlopen()` from libdl

## Caveat about `ptrace()`

* On many Linux distributions, the kernel is configured by default to prevent any process from calling `ptrace()` on another process that it did not create (e.g. via `fork()`).

* This is a security feature meant to prevent exactly the kind of mischief that this tool causes.

* You can temporarily disable it until the next reboot using the following command:

        echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope

## Compiling

* Simply running `make` should automatically select and build for the correct architecture, but if this fails (or you would like to select the target manually), run one of the following make commands:

    * arm:

            make arm

    * x86:

            make x86

    * x86_64:

            make x86_64

## Usage

    ./inject [-n process-name] [-p pid] [library-to-inject]

## Sample

* In one terminal, start up the sample target app, which simply outputs "sleeping..." each second:

        ./sample-target

* In another terminal, inject sample-library.so into the target app:

        ./inject -n sample-target sample-library.so

*  The output should look something like this:

 * First terminal:

            $ ./sample-target
            sleeping...
            sleeping...
            I just got loaded
            sleeping...
            sleeping...

 * Second terminal:

            $ ./inject -n sample-target sample-library.so
            targeting process "sample-target" with pid 31490
            library "sample-library.so" successfully injected
            $

* If the injection fails, make sure your machine is configured to allow processes to `ptrace()` other processes that they did not create. See the "Caveat about `ptrace()`" section above.

* You can verify that the injection was successful by checking `/proc/[pid]/maps`:

        $ cat /proc/$(pgrep sample-target)/maps
        [...]
        7f37d5cc6000-7f37d5cc7000 r-xp 00000000 ca:01 267321                     /home/ubuntu/linux-inject/sample-library.so
        7f37d5cc7000-7f37d5ec6000 ---p 00001000 ca:01 267321                     /home/ubuntu/linux-inject/sample-library.so
        7f37d5ec6000-7f37d5ec7000 r--p 00000000 ca:01 267321                     /home/ubuntu/linux-inject/sample-library.so
        7f37d5ec7000-7f37d5ec8000 rw-p 00001000 ca:01 267321                     /home/ubuntu/linux-inject/sample-library.so
        [...]

* You can also attach `gdb` to the target app and run `info sharedlibrary` to see what shared libraries the process currently has loaded:

        $ gdb -p $(pgrep sample-target)
        [...]
        (gdb) info sharedlibrary
        From                To                  Syms Read   Shared Object Library
        0x00007f37d628ded0  0x00007f37d628e9ce  Yes         /lib/x86_64-linux-gnu/libdl.so.2
        0x00007f37d5ee74a0  0x00007f37d602c583  Yes         /lib/x86_64-linux-gnu/libc.so.6
        0x00007f37d6491ae0  0x00007f37d64ac4e0  Yes         /lib64/ld-linux-x86-64.so.2
        0x00007f37d5cc6670  0x00007f37d5cc67b9  Yes         /home/ubuntu/linux-inject/sample-library.so
        (gdb)

## Compatibility

* The x86 and x86_64 versions work on Ubuntu 14.04.02 x86_64.

* The x86 and x86_64 versions work on Arch x86_64.

* The ARM version works on Arch on both armv6 and armv7.

* None of the versions seem to work on Debian. `__libc_dlopen_mode()` in Debian's libc does not load shared libraries in the same manner as Arch's and Ubuntu's versions do. I tested this on both x86_64 and armv6.

## TODOs / Known Issues

* Better support for targeting multi-thread/multi-process apps
 * I seem to get crashes when trying to inject into larger applications
 * Needs further investigation

* Support both ARM and Thumb mode
 * Currently only supports ARM mode
 * Should just be a matter of checking LSB of PC and acting accordingly

* Do better checking to verify that the specified shared object has actually been injected into the target process
 * Check `/proc/[pid]/maps` rather than just looking at the return value of `__libc_dlopen_mode()`

* Support more distros
 * Currently only working on Ubuntu and Arch for certain architectures
 * See "Compatibility" section above

* Possibly support more architectures?
 * 64-bit ARM
 * MIPS
