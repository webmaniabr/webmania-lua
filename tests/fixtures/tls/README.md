# Synthetic TLS fixtures (tests only)

Generated on 2026-10-27 with OpenSSL 3.0.13 for loopback tests of `webmania-sdk`.
They are not trusted by any system, are excluded from the published crate and
must never be used outside these tests.

- `ca.pem`: synthetic CA (EC P-256), valid 2026-10-01 to 2036-10-01; its private key was discarded after signing.
- `leaf.pem`/`leaf.key`: `localhost`, `127.0.0.1`, `::1`, serverAuth, signed by `ca.pem`.
- `other.pem`/`other.key`: `other.invalid` only (hostname mismatch control), signed by `ca.pem`.
- `unknown-ca.pem`, `unknown-leaf.pem`/`unknown-leaf.key`: chain from a CA the tests never trust.
