/*
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
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