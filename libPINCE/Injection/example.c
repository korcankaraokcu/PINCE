#include <stdlib.h>

void *infinite_thread(void *a);

//Injects a thread that runs forever at the background
__attribute__((constructor))
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
		sleep(1);
	}
}