#include <stdio.h>

int hello_world(int count);

int hello_world(int count)
{
  int a;
  for(a=1;a<count+1;a=a+1){
    printf("Hello World! for %d times\n", a);
  }
  return a;
}