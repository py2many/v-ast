#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <limits.h>
#include <stdio.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#else
#include <dlfcn.h>
#endif

#if defined(_WIN32)
#define V_AST_SHARED_LIB_NAME "v_ast_parser.dll"
#elif defined(__APPLE__)
#define V_AST_SHARED_LIB_NAME "libv_ast_parser.dylib"
#else
#define V_AST_SHARED_LIB_NAME "libv_ast_parser.so"
#endif

typedef const char* (*v_ast_parse_fn)(const char* source);
typedef const char* (*v_ast_last_error_fn)(void);

static v_ast_parse_fn g_parse_module = NULL;
static v_ast_parse_fn g_parse_expr = NULL;
static v_ast_last_error_fn g_last_error = NULL;

#if defined(_WIN32)
static HMODULE g_lib_handle = NULL;
#else
static void* g_lib_handle = NULL;
#endif

static int ensure_v_lib_loaded(const char* package_dir) {
    if (g_parse_module != NULL && g_parse_expr != NULL && g_last_error != NULL) {
        return 0;
    }
    if (package_dir == NULL || package_dir[0] == '\0') {
        PyErr_SetString(PyExc_ImportError, "package_dir is required to load native parser library");
        return -1;
    }
    char lib_path[PATH_MAX];
#if defined(_WIN32)
    _snprintf(lib_path, sizeof(lib_path), "%s\\%s", package_dir, V_AST_SHARED_LIB_NAME);
    g_lib_handle = LoadLibraryA(lib_path);
    if (g_lib_handle == NULL) {
        PyErr_Format(PyExc_ImportError, "failed to load shared library: %s", lib_path);
        return -1;
    }
    g_parse_module = (v_ast_parse_fn)GetProcAddress(g_lib_handle, "v_ast_parse_module_json");
    g_parse_expr = (v_ast_parse_fn)GetProcAddress(g_lib_handle, "v_ast_parse_expression_json");
    g_last_error = (v_ast_last_error_fn)GetProcAddress(g_lib_handle, "v_ast_last_error");
#else
    snprintf(lib_path, sizeof(lib_path), "%s/%s", package_dir, V_AST_SHARED_LIB_NAME);
    g_lib_handle = dlopen(lib_path, RTLD_NOW | RTLD_LOCAL);
    if (g_lib_handle == NULL) {
        const char* err = dlerror();
        PyErr_Format(PyExc_ImportError, "failed to load shared library %s: %s", lib_path, err ? err : "unknown");
        return -1;
    }
    g_parse_module = (v_ast_parse_fn)dlsym(g_lib_handle, "v_ast_parse_module_json");
    g_parse_expr = (v_ast_parse_fn)dlsym(g_lib_handle, "v_ast_parse_expression_json");
    g_last_error = (v_ast_last_error_fn)dlsym(g_lib_handle, "v_ast_last_error");
#endif

    if (g_parse_module == NULL || g_parse_expr == NULL || g_last_error == NULL) {
        PyErr_SetString(PyExc_ImportError, "missing required symbols in V shared library");
        return -1;
    }
    return 0;
}

static PyObject* py_parse_json(PyObject* self, PyObject* args) {
    const char* mode = NULL;
    const char* source = NULL;
    const char* package_dir = NULL;
    v_ast_parse_fn fn = NULL;

    (void)self;

    if (!PyArg_ParseTuple(args, "sss", &mode, &source, &package_dir)) {
        return NULL;
    }
    if (ensure_v_lib_loaded(package_dir) != 0) {
        return NULL;
    }
    if (strcmp(mode, "--json") == 0) {
        fn = g_parse_module;
    } else if (strcmp(mode, "--json-expr") == 0) {
        fn = g_parse_expr;
    } else {
        PyErr_SetString(PyExc_ValueError, "mode must be --json or --json-expr");
        return NULL;
    }

    const char* out = fn(source);
    if (out == NULL) {
        const char* err = g_last_error ? g_last_error() : NULL;
        if (err == NULL || err[0] == '\0') {
            err = "unknown parser failure";
        }
        PyErr_SetString(PyExc_ValueError, err);
        return NULL;
    }
    return PyUnicode_FromString(out);
}

static PyMethodDef methods[] = {
    {"parse_json", py_parse_json, METH_VARARGS, "Parse source and return JSON string."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module_def = {
    PyModuleDef_HEAD_INIT,
    "_vext",
    "Native extension for v-ast parser.",
    -1,
    methods,
};

PyMODINIT_FUNC PyInit__vext(void) {
    return PyModule_Create(&module_def);
}
