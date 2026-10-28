use serde_json::Value;
use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
    time::{SystemTime, UNIX_EPOCH},
};

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(name)
}

fn unique_path(suffix: &str) -> PathBuf {
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock should be after UNIX epoch")
        .as_nanos();
    std::env::temp_dir().join(format!("thalos-{stamp}-{suffix}"))
}

fn run_fixture(report_path: &Path, model_path: &Path) -> Value {
    let input_path = fixture("identity_inputs.json");
    let output = Command::new(env!("CARGO_BIN_EXE_thalos-governed-runtime"))
        .arg("--model")
        .arg(model_path)
        .arg("--inputs")
        .arg(input_path)
        .args(["--runs", "5", "--warmup", "2", "--output"])
        .arg(report_path)
        .output()
        .expect("runtime process should start");

    assert!(
        output.status.success(),
        "runtime failed\nstdout: {}\nstderr: {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(
        &fs::read(report_path).expect("runtime should write the benchmark report"),
    )
    .expect("benchmark report should be valid JSON")
}

fn materialize_model(path: &Path) {
    let encoded = fs::read_to_string(fixture("identity_f32_1x4.onnx.hex"))
        .expect("identity model hex fixture should exist");
    let bytes = hex::decode(encoded.trim()).expect("identity model hex fixture should decode");
    fs::write(path, bytes).expect("identity model should be materialized");
}

#[test]
fn identity_model_passes_in_process_reproducibility_gate() {
    let model = unique_path("identity.onnx");
    let report_path = unique_path("single.json");
    materialize_model(&model);
    let report = run_fixture(&report_path, &model);

    assert_eq!(report["exact_output_reproducibility_verified"], true);
    assert_eq!(report["baseline_output_hashes_stable"], true);
    assert_eq!(report["governed_output_hashes_stable"], true);
    assert_eq!(report["baseline_and_governed_outputs_match"], true);
    assert_eq!(report["pipeline_digests_stable"], true);
    assert_eq!(report["measured_runs"], 5);
    assert_eq!(
        report["model_sha3_256"],
        "b653f9b6f60434ba560019e5a102c698d456b47cbb9c90b9a52c33515c54d9cb"
    );

    let _ = fs::remove_file(report_path);
    let _ = fs::remove_file(model);
}

#[test]
fn pipeline_digest_is_stable_across_processes() {
    let model = unique_path("identity-cross-process.onnx");
    let report_a = unique_path("report-a.json");
    let report_b = unique_path("report-b.json");
    materialize_model(&model);

    let a = run_fixture(&report_a, &model);
    let b = run_fixture(&report_b, &model);

    assert_eq!(a["model_sha3_256"], b["model_sha3_256"]);
    assert_eq!(a["input_sha3_256"], b["input_sha3_256"]);
    assert_eq!(a["output_sha3_256"], b["output_sha3_256"]);
    assert_eq!(a["pipeline_sha3_256"], b["pipeline_sha3_256"]);
    assert_eq!(a["pipeline_digests_stable"], true);
    assert_eq!(b["pipeline_digests_stable"], true);

    let _ = fs::remove_file(report_a);
    let _ = fs::remove_file(report_b);
    let _ = fs::remove_file(model);
}
