#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef void *(*malloc_fn)(size_t);
typedef void (*free_fn)(void *);
typedef void *(*realloc_fn)(void *, size_t);
typedef void *(*calloc_fn)(size_t, size_t);

static malloc_fn real_malloc;
static free_fn real_free;
static realloc_fn real_realloc;
static calloc_fn real_calloc;
static FILE *log_file;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static int in_init;

static void init_hooks(void) {
    if (real_malloc) return;
    in_init = 1;
    real_malloc = (malloc_fn)dlsym(RTLD_NEXT, "malloc");
    real_free = (free_fn)dlsym(RTLD_NEXT, "free");
    real_realloc = (realloc_fn)dlsym(RTLD_NEXT, "realloc");
    real_calloc = (calloc_fn)dlsym(RTLD_NEXT, "calloc");
    char path[256];
    snprintf(path, sizeof(path), "/tmp/pince_heap_%d.log", (int)getpid());
    log_file = fopen(path, "a");
    in_init = 0;
}

static void log_event(char type, void *ptr, size_t size, void *ptr2) {
    if (!log_file || in_init) return;
    pthread_mutex_lock(&lock);
    if (type == 'R')
        fprintf(log_file, "R %p %zu %p\n", ptr2, size, ptr);
    else
        fprintf(log_file, "%c %p %zu\n", type, ptr, size);
    fflush(log_file);
    pthread_mutex_unlock(&lock);
}

void *malloc(size_t size) {
    if (!real_malloc) init_hooks();
    void *p = real_malloc ? real_malloc(size) : NULL;
    if (p) log_event('M', p, size, NULL);
    return p;
}

void free(void *ptr) {
    if (!ptr) return;
    if (!real_free) init_hooks();
    log_event('F', ptr, 0, NULL);
    if (real_free) real_free(ptr);
}

void *realloc(void *ptr, size_t size) {
    if (!real_realloc) init_hooks();
    void *p = real_realloc ? real_realloc(ptr, size) : NULL;
    if (p || size == 0) log_event('R', p, size, ptr);
    return p;
}

void *calloc(size_t nmemb, size_t size) {
    if (!real_calloc) init_hooks();
    size_t total = nmemb * size;
    void *p = real_calloc ? real_calloc(nmemb, size) : NULL;
    if (p) log_event('C', p, total, NULL);
    return p;
}
