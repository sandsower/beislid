# setup section pr-host v1

In verbose mode, emit `✓ setup/section-pr-host v1 loaded` immediately after reading this file.

## PR host override

Configure `pr_host.*` only when the derived remote is wrong.
Ask for owner and repo; ask for remote only if it is not `origin`.

```beislid:pr_host.owner
my-org
```

```beislid:pr_host.repo
my-repo
```

```beislid:pr_host.remote
upstream
```

`pr_host` is pure address/config data.
Setup does not probe it.
