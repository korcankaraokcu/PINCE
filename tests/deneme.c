#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
void _gdb_expr()
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