#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>

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
	int milliseconds=500;
	struct timespec ts;
	ts.tv_sec = milliseconds / 1000;
	ts.tv_nsec = (milliseconds % 1000) * 1000000;
	int selfpid=getpid();
	char abort_file[100];
	sprintf(abort_file, "/tmp/PINCE-connection/%d/abort.txt", selfpid);
	FILE *exit;
	while(1)
	{
		nanosleep(&ts, NULL);
		exit = fopen(abort_file, "r");
		if(exit!=NULL){
			fclose(exit);
			return 0;
		}
	}
}