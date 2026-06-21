"""Pure core: domain logic that never touches the filesystem or network.

The only modules here that do I/O are `store` (files) — and even it holds no domain
rules — and the use-case layer in `loop`, which orchestrates the pure functions and the
injected ports. Everything else (`classify`, `status`, `fold`, `patterns`, `recap`,
`issues`) is a total function over plain data.
"""
