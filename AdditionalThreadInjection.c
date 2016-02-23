#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>

void *infinite(void *a);

void injection()
{
	int *a=1;
	pthread_t threadinf;
	pthread_create(&threadinf, NULL, infinite, (void*) a);
}

void *infinite(void *a)
{
	while(1)
	{
		sleep(100000);
	}
}
