# Testes e desenvolvimento

Como compilar e testar o SDK para Lua a partir da fonte. O contrato fixado e a versão estão descritos em [INTEGRATION.md](INTEGRATION.md).

As suítes em [tests](../tests) (scripts Lua, programas C e drivers Python) usam HTTP/TLS loopback com fixtures sintéticas; os certificados em [tests/fixtures/tls](../tests/fixtures/tls) são exclusivos de teste.
