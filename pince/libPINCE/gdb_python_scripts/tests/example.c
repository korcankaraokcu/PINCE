#include <stdio.h>

int hello_world(int count);

int hello_world(int count)
{
  int a;
  for(a=42;a<count+42;a++){
    printf("Hello World! for %d times\n", a-41);
  }
  return a-41;
}