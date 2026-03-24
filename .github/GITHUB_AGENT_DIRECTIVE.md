Implement the deterministic hashing, environment signature, and side-effect memoization layers as defined in `docs/EXECUTION_SUBSTRATE_SPEC.md`.
Implement the Library reconstruction pipeline and constraints as defined in `docs/THALOS_LIBRARY_DIRECTIVE.md`.
Wire new graph-native and library endpoints and back them with real code.
Ensure all UI for the new tab uses those endpoints.

## Issue Translation
- Create `execution_ir.hash` and `execution_ir.signature` modules.
- Implement Merkle-style `graph_hash` for `ExecutionGraph`.
- Add memoization store and mark side-effect nodes.
- Create `thalos_prime/library/{artifacts,store,index,reconstruct,search}.py`.
- Implement `/library/reconstruct` and `/library/search` endpoints.
- Add new main tab in web UI pointing at Library + substrate; move old UI to `Classic` tab.
