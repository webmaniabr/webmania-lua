rockspec_format = "3.0"
package = "webmania"
version = "0.1.0alpha5-1"
source = { url = "file://webmania-lua-0.1.0-alpha.5.tar.gz", dir = "webmania-lua-0.1.0-alpha.5" }
description = {
  summary = "Webmania Emissor Fiscal and Monitor Fiscal nominal Lua facade",
  homepage = "https://webmania.com.br/",
  license = "Proprietary; Webmania Terms of Use"
}
supported_platforms = { "linux" }
dependencies = { "lua >= 5.4, < 5.5" }
build = {
  type = "cmake",
  variables = {
    CMAKE_BUILD_TYPE = "Release",
    CMAKE_INSTALL_PREFIX = "$(PREFIX)",
    CMAKE_PREFIX_PATH = "$(WEBMANIA_DIR);$(LUA_BINDIR)/..",
    LUA_INCLUDE_DIR = "$(LUA_INCDIR)",
    LUA_LIBDIR = "$(LIBDIR)",
    LUA_LUADIR = "$(LUADIR)"
  }
}
