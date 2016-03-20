#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>

void *infinite_thread(void *a);

//Injects a thread that runs forever at the background, PINCE will switch to that thread when attached
void inject_infinite_thread()
{
	int *a=1;
	pthread_t* threadinf=(pthread_t*) malloc(sizeof(pthread_t));
	pthread_create(threadinf, NULL, infinite_thread, (void*) a);
}

void *infinite_thread(void *a)
{
	while(1)
	{
		sleep(100000);
	}
}
