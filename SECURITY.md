# Security policy

## Scope

This is a local analysis tool. No server, no authentication, no network
listener, no credentials. It makes exactly one outbound connection: an HTTPS
GET to `cricsheet.org` for a public archive of cricket scores, and only when
you run `scorebook fetch`.

There is no personal data anywhere in this project. The input is published
match data — the same numbers printed in a newspaper.

## Credentials

None. Cricsheet requires no account, no API key, and no token. If a future
change to this project introduces one, that change should be rejected: the
zero-credential property is why a fresh clone works for anyone.

`.gitignore` covers `.env` files regardless, so an unrelated secret dropped in
the working tree cannot be committed by accident.

## The realistic risks

**A hostile archive.** `scorebook fetch` downloads a zip and reads one member
out of it. The reader uses `ZipFile.open()` to stream a named member and never
calls `extractall()`, so a crafted archive cannot write outside the cache
directory — the [zip-slip](https://security.snyk.io/research/zip-slip-vulnerability)
class of bug does not apply. The download is size-checked before parsing.

**A malicious CSV.** Files are parsed with pandas as text and never evaluated.
Note that pandas is not a security boundary: do not point the loader at
untrusted input.

**Dependency vulnerabilities.** Dependencies are pinned exactly, so a fix
requires moving a pin here. Report the vulnerability upstream, then open an
issue on this repo so the pin can be moved.

## Reporting a vulnerability

Open a [security advisory](https://github.com/Surge77/scorebook/security/advisories/new)
rather than a public issue. Include reproduction steps and the commit affected.
Expect an initial response within seven days.
