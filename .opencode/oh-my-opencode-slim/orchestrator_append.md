## Project routing override: fixer-agy

- In THIS project, for bounded implementation/fixer-style work, delegate to @fixer-agy instead of @fixer. This overrides fixer-agy's default "only when explicitly asked for agy" rule.
- fixer-agy executes through the `agy` CLI and verifies the result; do not also dispatch @fixer for the same task.
- Keep @fixer for verification-only or when @fixer-agy fails.
