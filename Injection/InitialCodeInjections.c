#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <fcntl.h>

void *infinite_thread(void *a);
void *table_update_thread(void *a);

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

//Injects a thread that updates the address table constantly
void inject_table_update_thread()
{
	int *a=1;
	pthread_t* threadinf=(pthread_t*) malloc(sizeof(pthread_t));
	pthread_create(threadinf, NULL, table_update_thread, (void*) a);
}

void *table_update_thread(void *a)
{
	int selfpid=getpid();
	int fd_recv;
	int fd_send;
	char status_word[]="1";
	char recv_fifo[100];
	char send_fifo[100];
	sprintf(recv_fifo, "/tmp/PINCE/%d/PINCE-to-Inferior", selfpid);
	sprintf(send_fifo, "/tmp/PINCE/%d/Inferior-to-PINCE", selfpid);
	mkfifo(recv_fifo, 0666);
   	fd_recv = open(recv_fifo, O_RDONLY);
	fd_send = open(send_fifo, O_WRONLY);
	while (strcmp(status_word,"0")!=0){
		read(fd_recv, status_word, 1);
	}
   	close(fd_recv);
	close(fd_send);
}
