#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/ptrace.h>

/*
 * sleepfunc()
 *
 * The only purpose of this function is to output the message "sleeping..."
 * once a second to provide a more concrete idea of when the sample library
 * gets injected.
 *
 */

void sleepfunc()
{
	struct timespec* sleeptime = malloc(sizeof(struct timespec));

	sleeptime->tv_sec = 1;
	sleeptime->tv_nsec = 0;

	while(1)
	{
		printf("sleeping...\n");
		nanosleep(sleeptime, NULL);
	}

	free(sleeptime);
}

/*
 * main()
 *
 * Call sleepfunc(), which loops forever.
 *
 */

int main()
{
	sleepfunc();
	return 0;
}
