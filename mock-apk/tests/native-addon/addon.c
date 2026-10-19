/*
 * Minimal Node-API native addon for testing Android standalone Node binaries.
 * Headers come from the pinned official Node v24.21.0 source archive.
 * The addon is compiled separately for armv7a and arm64 using Android NDK.
 */
#define NAPI_VERSION 8
#include <node_api.h>
#include <stdint.h>

static napi_value add(napi_env env, napi_callback_info info) {
    size_t argc = 2;
    napi_value argv[2];
    int32_t a = 0;
    int32_t b = 0;
    napi_value answer;

    if (napi_get_cb_info(env, info, &argc, argv, NULL, NULL) != napi_ok ||
        argc != 2 ||
        napi_get_value_int32(env, argv[0], &a) != napi_ok ||
        napi_get_value_int32(env, argv[1], &b) != napi_ok ||
        napi_create_int32(env, a + b, &answer) != napi_ok) {
        napi_throw_type_error(env, NULL, "Expected two 32-bit integer arguments");
        return NULL;
    }
    return answer;
}

NAPI_MODULE_INIT() {
    napi_value fn;
    napi_value version;
    if (napi_create_function(env, "add", NAPI_AUTO_LENGTH, add, NULL, &fn) != napi_ok ||
        napi_set_named_property(env, exports, "add", fn) != napi_ok ||
        napi_create_uint32(env, NAPI_VERSION, &version) != napi_ok ||
        napi_set_named_property(env, exports, "apiVersion", version) != napi_ok) {
        napi_throw_error(env, NULL, "Unable to initialize N-API smoke module");
        return NULL;
    }
    return exports;
}
