# Thalos Prime Governed Runtime (Phase 1 prototype)

This isolated Rust crate wraps ONNX Runtime with SHA3-256 identities for the exact model bytes, canonical tensor inputs, numeric outputs, and a versioned pipeline digest. The pipeline digest binds the crate version, declared runtime policy, ONNX Runtime build identity, host OS/architecture, and model/input/output digests. These hashes provide content identity, not a digital signature or a trusted attestation. It establishes a measurable baseline for the Phase 1 and Phase 2 milestones; it is not yet the complete Thalos Prime control plane, a general ONNX server, or a security sandbox.

## Run

Install Rust 1.92 or later, then from this directory run:

1. `python tools/materialize_identity_fixture.py`
2. `cargo test`
3. `cargo run --release -- --model tests/fixtures/identity_f32_1x4.onnx --inputs tests/fixtures/identity_inputs.json --runs 1000 --warmup 20 --output identity-benchmark.json`

Set `THALOS_HOST_LABEL` to record a human-provided machine label in the JSON result.

## Contract

The runtime loads the exact model bytes it hashes, using an in-memory ONNX session. It currently requires a single-file ONNX model, supports named f32 and i64 input tensors, and hashes CPU-accessible f32 or i64 output tensors. Unsupported output types fail closed rather than producing an incomplete digest.

The comparison uses the default CPU provider, sequential execution, one intra-op thread, one inter-op thread, and Level1 graph optimizations. The baseline timer covers `Session::run` only. The governed timer covers per-call input hashing, `Session::run`, output hashing, and pipeline-hash creation. Tensor construction is excluded from both timers. Baseline output hashing happens after its timer. Paired alternating samples and warmups reduce but do not eliminate host noise.

The report records exact timing samples summarized as minimum, median, nearest-rank p95, and maximum. It also records session initialization time, model-read-and-hash time, input-hash time (digest computation only; JSON loading and parsing are excluded), model/input/output/pipeline SHA3-256 digests, host OS/architecture, and ONNX Runtime build information. Measured pairs alternate baseline-first and governed-first order to reduce systematic ordering bias. The baseline timer covers `Session::run` only; the governed timer covers input hashing, `Session::run`, output hashing, and pipeline-digest computation. Tensor construction is excluded from both timers.

## Determinism boundary

The executable exits with code 2 if output hashes differ between repeated runs or between baseline and governed paths; it writes the JSON report first for diagnosis. Use `--allow-nondeterminism` only when intentionally collecting failure data. Repeatability here means bitwise output identity within the measured runtime/model/input/provider configuration. SHA3 hashing does not make nondeterministic operations deterministic and does not prove repeatability across CPU architectures, accelerators, drivers, or ONNX Runtime builds.

The pinned `ort = 2.0.0-rc.15` package is a release candidate binding to ONNX Runtime 1.31. Treat that pin as a prototype dependency, not a production guarantee. Before commercial release, commit a Cargo.lock, validate a wider set of standard models and dtypes, capture CPU/compiler/provider metadata, and run benchmarks on named hardware. The two-page technical whitepaper must be generated from actual benchmark JSON, never illustrative timing values.

## JSON input schema

```json
{
  "schema_version": 1,
  "tensors": [
    {
      "name": "X",
      "dtype": "f32",
      "shape": [1, 4],
      "data": [1.25, -2.5, 0.0, 3.75]
    }
  ]
}
```

Input tensor names must be unique. Element count must match the shape. Input float values must be finite JSON numbers.
