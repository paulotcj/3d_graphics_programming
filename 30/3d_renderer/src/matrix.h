#ifndef MATRIX_H
#define MATRIX_H

#include "vector.h"

typedef struct {
    float m[4][4];
} mat4_t;

mat4_t mat4_identity(void);
mat4_t mat4_make_scale(float sx, float sy, float sz);
vec4_t mat4_mul_vec4(mat4_t m, vec4_t v);

#endif