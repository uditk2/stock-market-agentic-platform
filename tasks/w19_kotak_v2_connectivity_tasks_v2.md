# W19 Tasks v2 (Refined)

1. Connector foundation
- Introduce endpoint candidates and operation-specific URL builders.
- Add shared request runner with per-attempt metadata.

2. Credential verification path
- Replace single-path verification with candidate fallback.
- Distinguish upstream timeout/unreachable vs invalid credentials.

3. Market fetch path
- Apply fallback to scrip-master path discovery.
- Apply fallback to quote endpoint selection.

4. Test coverage
- Add unit tests for successful fallback when first endpoint fails.
- Add tests for auth-failure mapping and timeout mapping.

5. Validation
- Run targeted and full service tests.
- Record outcome and residual blockers.
