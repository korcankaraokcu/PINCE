#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/user.h>
#include <wait.h>

#include "utils.h"
#include "ptrace.h"

/*
 * injectSharedLibrary()
 *
 * This is the code that will actually be injected into the target process.
 * This code is responsible for loading the shared library into the target
 * process' address space.  First, it calls malloc() to allocate a buffer to
 * hold the filename of the library to be loaded. Then, it calls
 * __libc_dlopen_mode(), libc's implementation of dlopen(), to load the desired
 * shared library. Finally, it calls free() to free the buffer containing the
 * library name. Each time it needs to give control back to the injector
 * process, it breaks back in by executing an "int $3" instruction. See the
 * comments below for more details on how this works.
 *
 */

void injectSharedLibrary(long mallocaddr, long freeaddr, long dlopenaddr)
{
	// here are the assumptions I'm making about what data will be located
	// where at the time the target executes this code:
	//
	//   ebx = address of malloc() in target process
	//   edi = address of __libc_dlopen_mode() in target process
	//   esi = address of free() in target process
	//   ecx = size of the path to the shared library we want to load

	// for some reason it's adding 1 to esi, so subtract 1 from it
	asm("dec %esi");

	// call malloc() from within the target process
	asm(
		// choose the amount of memory to allocate with malloc() based on the size
		// of the path to the shared library passed via ecx
		"push %ecx \n"
		// call malloc
		"call *%ebx \n"
		// copy malloc's return value (i.e. the address of the allocated buffer) into ebx
		"mov %eax, %ebx \n"
		// break back in so that the injector can get the return value
		"int $3"
	);

	// call __libc_dlopen_mode() to load the shared library
	asm(
		// 2nd argument to __libc_dlopen_mode(): flag = RTLD_LAZY
		"push $1 \n"
		// 1st argument to __libc_dlopen_mode(): filename = the buffer we allocated earlier
		"push %ebx \n"
		// call __libc_dlopen_mode()
		"call *%edi \n"
		// break back in so that the injector can check the return value
		"int $3"
	);

	// call free() on the previously malloc'd buffer
	asm(
		// 1st argument to free(): ptr = the buffer we allocated earlier
		"push %ebx \n"
		// call free()
		"call *%esi"
	);

	// we already overwrote the RET instruction at the end of this function
	// with an INT 3, so at this point the injector will regain control of
	// the target's execution.
}

/*
 * injectSharedLibrary_end()
 *
 * This function's only purpose is to be contiguous to injectSharedLibrary(),
 * so that we can use its address to more precisely figure out how long
 * injectSharedLibrary() is.
 *
 */

void injectSharedLibrary_end()
{
}

int main(int argc, char** argv)
{
	if(argc < 4)
	{
		usage(argv[0]);
		return 1;
	}

	char* command = argv[1];
	char* commandArg = argv[2];
	char* libname = argv[3];
	char* libPath = realpath(libname, NULL);

	char* processName = NULL;
	pid_t target = 0;

	if(!libPath)
	{
		fprintf(stderr, "can't find file \"%s\"\n", libname);
		return 1;
	}

	if(!strcmp(command, "-n"))
	{
		processName = commandArg;
		target = findProcessByName(processName);
		if(target == -1)
		{
			fprintf(stderr, "doesn't look like a process named \"%s\" is running right now\n", processName);
			return 1;
		}

		printf("targeting process \"%s\" with pid %d\n", processName, target);
	}
	else if(!strcmp(command, "-p"))
	{
		target = atoi(commandArg);
		printf("targeting process with pid %d\n", target);
	}
	else
	{
		usage(argv[0]);
		return 1;
	}

	int libPathLength = strlen(libPath) + 1;

	int mypid = getpid();
	long mylibcaddr = getlibcaddr(mypid);

	// find the addresses of the syscalls that we'd like to use inside the
	// target, as loaded inside THIS process (i.e. NOT the target process)
	long mallocAddr = getFunctionAddress("malloc");
	long freeAddr = getFunctionAddress("free");
	long dlopenAddr = getFunctionAddress("__libc_dlopen_mode");

	// use the base address of libc to calculate offsets for the syscalls
	// we want to use
	long mallocOffset = mallocAddr - mylibcaddr;
	long freeOffset = freeAddr - mylibcaddr;
	long dlopenOffset = dlopenAddr - mylibcaddr;

	// get the target process' libc address and use it to find the
	// addresses of the syscalls we want to use inside the target process
	long targetLibcAddr = getlibcaddr(target);
	long targetMallocAddr = targetLibcAddr + mallocOffset;
	long targetFreeAddr = targetLibcAddr + freeOffset;
	long targetDlopenAddr = targetLibcAddr + dlopenOffset;

	struct user_regs_struct oldregs, regs;
	memset(&oldregs, 0, sizeof(struct user_regs_struct));
	memset(&regs, 0, sizeof(struct user_regs_struct));

	ptrace_attach(target);

	ptrace_getregs(target, &oldregs);
	memcpy(&regs, &oldregs, sizeof(struct user_regs_struct));

	// find a good address to copy code to
	long addr = freespaceaddr(target) + sizeof(long);

	// now that we have an address to copy code to, set the target's eip to it.
	regs.eip = addr;

	// pass arguments to my function injectSharedLibrary() by loading them
	// into the right registers. see comments in injectSharedLibrary() for
	// more details.
	regs.ebx = targetMallocAddr;
	regs.edi = targetDlopenAddr;
	regs.esi = targetFreeAddr;
	regs.ecx = libPathLength;
	ptrace_setregs(target, &regs);

	// figure out the size of injectSharedLibrary() so we know how big of a buffer to allocate. 
	size_t injectSharedLibrary_size = (intptr_t)injectSharedLibrary_end - (intptr_t)injectSharedLibrary;

	// also figure out where the RET instruction at the end of
	// injectSharedLibrary() lies so that we can overwrite it with an INT 3
	// in order to break back into the target process. gcc and clang both
	// force function addresses to be word-aligned, which means that
	// functions are padded at the end after the RET instruction that ends
	// the function. as a result, even though in theory we've found the
	// length of the function, it is very likely padded with NOPs, so we
	// still need to do a bit of searching to find the RET.
	intptr_t injectSharedLibrary_ret = (intptr_t)findRet(injectSharedLibrary_end) - (intptr_t)injectSharedLibrary;

	// back up whatever data used to be at the address we want to modify.
	char* backup = malloc(injectSharedLibrary_size * sizeof(char));
	ptrace_read(target, addr, backup, injectSharedLibrary_size);

	// set up the buffer containing the code to inject into the target process.
	char* newcode = malloc(injectSharedLibrary_size * sizeof(char));
	memset(newcode, 0, injectSharedLibrary_size * sizeof(char));

	// copy the code of injectSharedLibrary() to a buffer.
	memcpy(newcode, injectSharedLibrary, injectSharedLibrary_size - 1);
	// overwrite the RET instruction with an INT 3.
	newcode[injectSharedLibrary_ret] = INTEL_INT3_INSTRUCTION;

	// copy injectSharedLibrary()'s code to the target address inside the
	// target process' address space.
	ptrace_write(target, addr, newcode, injectSharedLibrary_size);

	// now that the new code is in place, let the target run our injected code.
	ptrace_cont(target);

	// at this point, the target should have run malloc(). check its return
	// value to see if it succeeded, and bail out cleanly if it didn't.
	struct user_regs_struct malloc_regs;
	memset(&malloc_regs, 0, sizeof(struct user_regs_struct));
	ptrace_getregs(target, &malloc_regs);
	unsigned long targetBuf = malloc_regs.eax;
	if(targetBuf == 0)
	{
		fprintf(stderr, "malloc() failed to allocate memory\n");
		restoreStateAndDetach(target, addr, backup, injectSharedLibrary_size, oldregs);
		free(backup);
		free(newcode);
		return 1;
	}

	// if we get here, then malloc likely succeeded, so now we need to copy
	// the path to the shared library we want to inject into the buffer
	// that the target process just malloc'd. this is needed so that it can
	// be passed as an argument to __libc_dlopen_mode later on.

	// read the current value of eax, which contains malloc's return value,
	// and copy the name of our shared library to that address inside the
	// target process.
	ptrace_write(target, targetBuf, libPath, libPathLength);

	// now call __libc_dlopen_mode() to attempt to load the shared library.
	ptrace_cont(target);

	// check out what the registers look like after calling
	// __libc_dlopen_mode.
	struct user_regs_struct dlopen_regs;
	memset(&dlopen_regs, 0, sizeof(struct user_regs_struct));
	ptrace_getregs(target, &dlopen_regs);
	unsigned long long libAddr = dlopen_regs.eax;

	// if eax is 0 here, then dlopen failed, and we should bail out cleanly.
	if(libAddr == 0)
	{
		fprintf(stderr, "__libc_dlopen_mode() failed to load %s\n", libname);
		restoreStateAndDetach(target, addr, backup, injectSharedLibrary_size, oldregs);
		free(backup);
		free(newcode);
		return 1;
	}

	// now check /proc/pid/maps to see whether injection was successful.
	if(checkloaded(target, libname))
	{
		printf("\"%s\" successfully injected\n", libname);
	}
	else
	{
		fprintf(stderr, "could not inject \"%s\"\n", libname);
	}

	// as a courtesy, free the buffer that we allocated inside the target
	// process. we don't really care whether this succeeds, so don't
	// bother checking the return value.
	ptrace_cont(target);

	// at this point, if everything went according to plan, we've loaded
	// the shared library inside the target process, so we're done. restore
	// the old state and detach from the target.
	restoreStateAndDetach(target, addr, backup, injectSharedLibrary_size, oldregs);
	free(backup);
	free(newcode);

	return 0;
}
