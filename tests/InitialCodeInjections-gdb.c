#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>

void *infinite_thread(void *a);
void *table_update_thread(void *a);

//Injects a thread that runs forever at the background, PINCE will switch to that thread when attached
//__attribute__((constructor))
void _gdb_expr()
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

//Injects a thread that updates the address table constantly
void inject_table_update_thread()
{
	int *a=1;
	pthread_t* threadinf=(pthread_t*) malloc(sizeof(pthread_t));
	pthread_create(threadinf, NULL, table_update_thread, (void*) a);
}

void *table_update_thread(void *a)
{
	int milliseconds=10;
	struct timespec ts;
	ts.tv_sec = milliseconds / 1000;
	ts.tv_nsec = (milliseconds % 1000) * 1000000;
	int selfpid=getpid();
	char directory_path[100];
	char status_file[100];
	char recv_file[100];
	char send_file[100];
	char abort_file[100];
	sprintf(directory_path, "/tmp/PINCE-connection/%d", selfpid);
	sprintf(recv_file, "%s/PINCE-to-Inferior.txt", directory_path);
	sprintf(send_file, "%s/Inferior-to-PINCE.txt", directory_path);
	sprintf(status_file, "%s/status.txt", directory_path);
	sprintf(abort_file, "%s/abort.txt", directory_path);
	DIR* PINCE_dir;	
	FILE *fp;
	FILE *status;
	FILE *exit;
	FILE *initialize;
	//char buff[255]="";
	char status_word[100]="";
	char PINCE_pid[10]="";
	char PINCE_proc_directory[100];
	while(!strcmp(PINCE_pid, "")){
		nanosleep(&ts, NULL);
		initialize = fopen(status_file, "r");
		if (initialize!=NULL){
			fscanf(initialize, "%s", PINCE_pid);
			fclose(initialize);
		}
	}
	sprintf(PINCE_proc_directory, "/proc/%s/", PINCE_pid);
	milliseconds=400;
	ts.tv_sec = milliseconds / 1000;
	ts.tv_nsec = (milliseconds % 1000) * 1000000;
	while(1){
		status = fopen(status_file, "w");
		fputs("sync-request-recieve", status);
		fclose(status);
		nanosleep(&ts, NULL);

		//abort.txt is created by PINCE to tell the inferior to quit
		exit = fopen(abort_file, "r");
		if(exit!=NULL){
			fclose(exit);
			return 0;
		}

		//check if PINCE is still alive
		PINCE_dir = opendir(PINCE_proc_directory);
		if(PINCE_dir){
			closedir(PINCE_dir);
		}
		else{
			exit = fopen(abort_file, "w");
			fclose(exit);
			return 0;
		}
		fp = fopen(recv_file, "r");
		//fscanf(fp, "%s", buff);
		//printf("%s\n", buff );
		fclose(fp);
		fp = fopen(send_file, "w");
		fputs(PINCE_pid, fp);
		fclose(fp);
	}
}
/*
void _gdb_expr() {
     inject_infinite_thread();
     return 0;
}
*/