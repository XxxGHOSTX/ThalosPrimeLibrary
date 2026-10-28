use anyhow::{bail, Context, Result};
use ort::{
    session::{builder::GraphOptimizationLevel, Session},
    value::{DynTensor, Tensor},
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha3::{Digest, Sha3_256};
use std::{
    collections::HashSet,
    env, fs,
    path::PathBuf,
    process,
    time::Instant,
};

const POLICY: &str = "cpu-default;sequential;intra-op=1;inter-op=1;graph-optimization=Level1";

#[derive(Debug)]
struct Args {
    model: PathBuf,
    inputs: PathBuf,
    runs: usize,
    warmup: usize,
    output: PathBuf,
    allow_nondeterminism: bool,
}

#[derive(Debug, Deserialize)]
struct InputFile {
    #[serde(default = "schema_v1")]
    schema_version: u32,
    tensors: Vec<RawTensor>,
}
fn schema_v1() -> u32 { 1 }

#[derive(Debug, Deserialize)]
struct RawTensor {
    name: String,
    dtype: DType,
    shape: Vec<usize>,
    data: Value,
}

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
enum DType { F32, I64 }

#[derive(Clone, Debug)]
enum TensorData { F32(Vec<f32>), I64(Vec<i64>) }

#[derive(Clone, Debug)]
struct InputTensor {
    name: String,
    shape: Vec<usize>,
    data: TensorData,
}

#[derive(Debug, Serialize)]
struct TimingStats {
    samples: usize,
    min_ns: u64,
    median_ns: f64,
    p95_ns: u64,
    max_ns: u64,
}

#[derive(Debug, Serialize)]
struct Report {
    schema_version: u32,
    model_file_name: String,
    model_size_bytes: usize,
    model_sha3_256: String,
    input_sha3_256: String,
    runtime_policy: String,
    onnx_runtime_build: String,
    host_os: String,
    host_arch: String,
    host_label: Option<String>,
    model_read_and_hash_ms: f64,
    input_hash_ms: f64,
    session_initialization_ms: f64,
    warmup_runs: usize,
    measured_runs: usize,
    baseline_inference: TimingStats,
    governed_inference: TimingStats,
    median_added_governance_ns: f64,
    median_added_governance_percent: f64,
    baseline_output_hashes_stable: bool,
    governed_output_hashes_stable: bool,
    baseline_and_governed_outputs_match: bool,
    pipeline_digests_stable: bool,
    exact_output_reproducibility_verified: bool,
    output_sha3_256: String,
    pipeline_sha3_256: String,
}

fn next_value(args: &mut impl Iterator<Item = String>, flag: &str) -> Result<String> {
    args.next().with_context(|| format!("missing value after {flag}"))
}

fn parse_args() -> Result<Args> {
    let mut model = None;
    let mut inputs = None;
    let mut runs = 100usize;
    let mut warmup = 10usize;
    let mut output = PathBuf::from("thalos-benchmark.json");
    let mut allow_nondeterminism = false;
    let mut it = env::args().skip(1);
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--help" | "-h" => {
                println!("Usage: thalos-governed-runtime --model MODEL.onnx --inputs INPUTS.json [--runs N] [--warmup N] [--output REPORT.json] [--allow-nondeterminism]");
                process::exit(0);
            }
            "--model" => model = Some(PathBuf::from(next_value(&mut it, "--model")?)),
            "--inputs" => inputs = Some(PathBuf::from(next_value(&mut it, "--inputs")?)),
            "--runs" => runs = next_value(&mut it, "--runs")?.parse().context("--runs must be an integer")?,
            "--warmup" => warmup = next_value(&mut it, "--warmup")?.parse().context("--warmup must be an integer")?,
            "--output" => output = PathBuf::from(next_value(&mut it, "--output")?),
            "--allow-nondeterminism" => allow_nondeterminism = true,
            other => bail!("unknown option {other:?}; use --help"),
        }
    }
    let model = model.context("missing --model")?;
    let inputs = inputs.context("missing --inputs")?;
    if !(1..=1_000_000).contains(&runs) { bail!("--runs must be between 1 and 1,000,000"); }
    if warmup > 100_000 { bail!("--warmup must be at most 100,000"); }
    Ok(Args { model, inputs, runs, warmup, output, allow_nondeterminism })
}

fn element_count(shape: &[usize], name: &str) -> Result<usize> {
    shape.iter().try_fold(1usize, |n, &d| {
        if d > i64::MAX as usize { bail!("tensor {name:?} dimension exceeds ONNX range"); }
        n.checked_mul(d).context("tensor shape product overflow")
    })
}

fn load_inputs(path: &PathBuf) -> Result<Vec<InputTensor>> {
    let raw: InputFile = serde_json::from_slice(
        &fs::read(path).with_context(|| format!("reading {}", path.display()))?,
    ).with_context(|| format!("parsing {} as input JSON", path.display()))?;
    if raw.schema_version != 1 { bail!("input schema_version must be 1"); }
    if raw.tensors.is_empty() { bail!("input tensor list must not be empty"); }
    let mut names = HashSet::new();
    let mut out = Vec::with_capacity(raw.tensors.len());
    for raw_tensor in raw.tensors {
        if raw_tensor.name.trim().is_empty() { bail!("tensor name must not be empty"); }
        if !names.insert(raw_tensor.name.clone()) { bail!("duplicate tensor name {:?}", raw_tensor.name); }
        let expected = element_count(&raw_tensor.shape, &raw_tensor.name)?;
        let data = match raw_tensor.dtype {
            DType::F32 => {
                let values: Vec<f32> = serde_json::from_value(raw_tensor.data)
                    .with_context(|| format!("tensor {:?} requires an f32 numeric array", raw_tensor.name))?;
                if values.iter().any(|v| !v.is_finite()) { bail!("tensor {:?} contains non-finite f32", raw_tensor.name); }
                if values.len() != expected { bail!("tensor {:?}: shape needs {expected} elements; received {}", raw_tensor.name, values.len()); }
                TensorData::F32(values)
            }
            DType::I64 => {
                let values: Vec<i64> = serde_json::from_value(raw_tensor.data)
                    .with_context(|| format!("tensor {:?} requires an i64 integer array", raw_tensor.name))?;
                if values.len() != expected { bail!("tensor {:?}: shape needs {expected} elements; received {}", raw_tensor.name, values.len()); }
                TensorData::I64(values)
            }
        };
        out.push(InputTensor { name: raw_tensor.name, shape: raw_tensor.shape, data });
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(out)
}

fn hash_len(hasher: &mut Sha3_256, bytes: &[u8]) {
    hasher.update((bytes.len() as u64).to_le_bytes());
    hasher.update(bytes);
}

fn input_hash(tensors: &[InputTensor]) -> String {
    let mut sorted: Vec<&InputTensor> = tensors.iter().collect();
    sorted.sort_by(|a, b| a.name.cmp(&b.name));
    let mut h = Sha3_256::new();
    h.update(b"THALOS:INPUT:v1\0");
    h.update((sorted.len() as u64).to_le_bytes());
    for tensor in sorted {
        hash_len(&mut h, tensor.name.as_bytes());
        h.update((tensor.shape.len() as u64).to_le_bytes());
        for dim in &tensor.shape { h.update((*dim as u64).to_le_bytes()); }
        match &tensor.data {
            TensorData::F32(values) => {
                h.update([1u8]);
                h.update((values.len() as u64).to_le_bytes());
                for v in values { h.update(v.to_bits().to_le_bytes()); }
            }
            TensorData::I64(values) => {
                h.update([2u8]);
                h.update((values.len() as u64).to_le_bytes());
                for v in values { h.update(v.to_le_bytes()); }
            }
        }
    }
    hex::encode(h.finalize())
}

fn ort_inputs(tensors: &[InputTensor]) -> Result<Vec<(String, DynTensor)>> {
    tensors.iter().map(|t| {
        let value: DynTensor = match &t.data {
            TensorData::F32(v) => Tensor::<f32>::from_array((t.shape.clone(), v.clone()))?.upcast(),
            TensorData::I64(v) => Tensor::<i64>::from_array((t.shape.clone(), v.clone()))?.upcast(),
        };
        Ok((t.name.clone(), value))
    }).collect()
}

fn hash_shape(h: &mut Sha3_256, shape: &[i64]) {
    h.update((shape.len() as u64).to_le_bytes());
    for d in shape { h.update(d.to_le_bytes()); }
}

fn output_hash(outputs: &ort::session::SessionOutputs<'_>) -> Result<String> {
    let mut names: Vec<&str> = outputs.keys().collect();
    names.sort_unstable();
    if names.is_empty() { bail!("model returned no output tensors"); }
    let mut h = Sha3_256::new();
    h.update(b"THALOS:OUTPUT:v1\0");
    h.update((names.len() as u64).to_le_bytes());
    for name in names {
        hash_len(&mut h, name.as_bytes());
        let output = outputs.get(name).with_context(|| format!("missing output {name:?}"))?;
        if let Ok((shape, values)) = output.try_extract_tensor::<f32>() {
            h.update([1u8]);
            hash_shape(&mut h, shape);
            h.update((values.len() as u64).to_le_bytes());
            for v in values { h.update(v.to_bits().to_le_bytes()); }
        } else if let Ok((shape, values)) = output.try_extract_tensor::<i64>() {
            h.update([2u8]);
            hash_shape(&mut h, shape);
            h.update((values.len() as u64).to_le_bytes());
            for v in values { h.update(v.to_le_bytes()); }
        } else {
            bail!("output {name:?} uses an unsupported element type; supported output types are f32 and i64");
        }
    }
    Ok(hex::encode(h.finalize()))
}

fn pipeline_hash(
    model: &str,
    input: &str,
    output: &str,
    runtime_build: &str,
    host_os: &str,
    host_arch: &str,
) -> String {
    let mut h = Sha3_256::new();
    h.update(b"THALOS:PIPELINE:v1\0");
    hash_len(&mut h, env!("CARGO_PKG_VERSION").as_bytes());
    hash_len(&mut h, POLICY.as_bytes());
    hash_len(&mut h, runtime_build.as_bytes());
    hash_len(&mut h, host_os.as_bytes());
    hash_len(&mut h, host_arch.as_bytes());
    hash_len(&mut h, model.as_bytes());
    hash_len(&mut h, input.as_bytes());
    hash_len(&mut h, output.as_bytes());
    hex::encode(h.finalize())
}

fn elapsed_ns(start: Instant) -> u64 { start.elapsed().as_nanos().min(u64::MAX as u128) as u64 }

fn stats(samples: &[u64]) -> Result<TimingStats> {
    if samples.is_empty() { bail!("cannot summarize an empty timing list"); }
    let mut v = samples.to_vec();
    v.sort_unstable();
    let m = v.len() / 2;
    let median = if v.len() % 2 == 0 { (v[m - 1] as f64 + v[m] as f64) / 2.0 } else { v[m] as f64 };
    let p95 = ((v.len() as f64 * 0.95).ceil() as usize).saturating_sub(1).min(v.len() - 1);
    Ok(TimingStats { samples: v.len(), min_ns: v[0], median_ns: median, p95_ns: v[p95], max_ns: *v.last().unwrap_or(&v[0]) })
}

fn hashes_stable(values: &[String]) -> bool {
    values.first().is_some_and(|first| values.iter().all(|v| v == first))
}

fn run_baseline_sample(session: &mut Session, inputs: &[InputTensor]) -> Result<(u64, String)> {
    let inference_inputs = ort_inputs(inputs)?;
    let started = Instant::now();
    let outputs = session.run(inference_inputs).context("baseline inference failed")?;
    let elapsed = elapsed_ns(started);
    let digest = output_hash(&outputs)?;
    Ok((elapsed, digest))
}

fn run_governed_sample(
    session: &mut Session,
    inputs: &[InputTensor],
    model_hash: &str,
    runtime_build: &str,
    host_os: &str,
    host_arch: &str,
) -> Result<(u64, String, String)> {
    let inference_inputs = ort_inputs(inputs)?;
    let started = Instant::now();
    let input_digest = input_hash(inputs);
    let outputs = session.run(inference_inputs).context("governed inference failed")?;
    let output_digest = output_hash(&outputs)?;
    let pipeline_digest = pipeline_hash(
        model_hash, &input_digest, &output_digest, runtime_build, host_os, host_arch,
    );
    let elapsed = elapsed_ns(started);
    Ok((elapsed, output_digest, pipeline_digest))
}

fn run() -> Result<(Report, bool)> {
    let args = parse_args()?;
    let model_started = Instant::now();
    let model_bytes = fs::read(&args.model).with_context(|| format!("reading model {}", args.model.display()))?;
    if model_bytes.is_empty() { bail!("model file is empty"); }
    let model_hash = hex::encode(Sha3_256::digest(&model_bytes));
    let model_read_and_hash_ms = model_started.elapsed().as_secs_f64() * 1000.0;

    let inputs = load_inputs(&args.inputs)?;
    let input_started = Instant::now();
    let input_digest = input_hash(&inputs);
    let input_hash_ms = input_started.elapsed().as_secs_f64() * 1000.0;

    let init_started = Instant::now();
    let mut session = Session::builder()?
        .with_optimization_level(GraphOptimizationLevel::Level1)?
        .with_intra_threads(1)?
        .with_inter_threads(1)?
        .with_parallel_execution(false)?
        .commit_from_memory(&model_bytes)
        .context("creating ONNX Runtime session from hashed model bytes")?;
    let session_initialization_ms = init_started.elapsed().as_secs_f64() * 1000.0;
    let runtime_build = ort::info().to_owned();
    let host_os = env::consts::OS.to_owned();
    let host_arch = env::consts::ARCH.to_owned();

    for warmup_index in 0..args.warmup {
        if warmup_index % 2 == 0 {
            let _ = run_baseline_sample(&mut session, &inputs)?;
            let _ = run_governed_sample(
                &mut session, &inputs, &model_hash, &runtime_build, &host_os, &host_arch,
            )?;
        } else {
            let _ = run_governed_sample(
                &mut session, &inputs, &model_hash, &runtime_build, &host_os, &host_arch,
            )?;
            let _ = run_baseline_sample(&mut session, &inputs)?;
        }
    }

    let mut baseline_ns = Vec::with_capacity(args.runs);
    let mut governed_ns = Vec::with_capacity(args.runs);
    let mut baseline_hashes = Vec::with_capacity(args.runs);
    let mut governed_hashes = Vec::with_capacity(args.runs);
    let mut pipeline_hashes = Vec::with_capacity(args.runs);
    for run_index in 0..args.runs {
        if run_index % 2 == 0 {
            let (elapsed, digest) = run_baseline_sample(&mut session, &inputs)?;
            baseline_ns.push(elapsed);
            baseline_hashes.push(digest);

            let (elapsed, digest, pipeline) = run_governed_sample(
                &mut session, &inputs, &model_hash, &runtime_build, &host_os, &host_arch,
            )?;
            governed_ns.push(elapsed);
            governed_hashes.push(digest);
            pipeline_hashes.push(pipeline);
        } else {
            let (elapsed, digest, pipeline) = run_governed_sample(
                &mut session, &inputs, &model_hash, &runtime_build, &host_os, &host_arch,
            )?;
            governed_ns.push(elapsed);
            governed_hashes.push(digest);
            pipeline_hashes.push(pipeline);

            let (elapsed, digest) = run_baseline_sample(&mut session, &inputs)?;
            baseline_ns.push(elapsed);
            baseline_hashes.push(digest);
        }
    }

    let baseline_output_hashes_stable = hashes_stable(&baseline_hashes);
    let governed_output_hashes_stable = hashes_stable(&governed_hashes);
    let pipeline_digests_stable = hashes_stable(&pipeline_hashes);
    let baseline_and_governed_outputs_match =
        baseline_hashes.iter().zip(&governed_hashes).all(|(a, b)| a == b);
    let exact_output_reproducibility_verified = baseline_output_hashes_stable
        && governed_output_hashes_stable
        && baseline_and_governed_outputs_match;

    let baseline_stats = stats(&baseline_ns)?;
    let governed_stats = stats(&governed_ns)?;
    let median_added_governance_ns = governed_stats.median_ns - baseline_stats.median_ns;
    let median_added_governance_percent = if baseline_stats.median_ns > 0.0 {
        median_added_governance_ns / baseline_stats.median_ns * 100.0
    } else { 0.0 };

    let file_name = args.model.file_name().and_then(|s| s.to_str()).unwrap_or("model.onnx").to_owned();
    let report = Report {
        schema_version: 1,
        model_file_name: file_name,
        model_size_bytes: model_bytes.len(),
        model_sha3_256: model_hash,
        input_sha3_256: input_digest,
        runtime_policy: POLICY.to_owned(),
        onnx_runtime_build: runtime_build,
        host_os,
        host_arch,
        host_label: env::var("THALOS_HOST_LABEL").ok(),
        model_read_and_hash_ms,
        input_hash_ms,
        session_initialization_ms,
        warmup_runs: args.warmup,
        measured_runs: args.runs,
        baseline_inference: baseline_stats,
        governed_inference: governed_stats,
        median_added_governance_ns,
        median_added_governance_percent,
        baseline_output_hashes_stable,
        governed_output_hashes_stable,
        baseline_and_governed_outputs_match,
        pipeline_digests_stable,
        exact_output_reproducibility_verified,
        output_sha3_256: governed_hashes.first().cloned().unwrap_or_default(),
        pipeline_sha3_256: pipeline_hashes.first().cloned().unwrap_or_default(),
    };

    fs::write(&args.output, serde_json::to_vec_pretty(&report)?)
        .with_context(|| format!("writing report {}", args.output.display()))?;
    eprintln!("Wrote benchmark report to {}", args.output.display());
    eprintln!("Baseline median: {:.0} ns; governed median: {:.0} ns; overhead: {:.0} ns ({:.2}%)",
        report.baseline_inference.median_ns, report.governed_inference.median_ns,
        report.median_added_governance_ns, report.median_added_governance_percent);
    eprintln!("Output reproducibility gate: {}", if exact_output_reproducibility_verified { "PASS" } else { "FAIL" });
    Ok((report, args.allow_nondeterminism))
}

fn main() {
    match run() {
        Ok((report, allow)) if !report.exact_output_reproducibility_verified && !allow => {
            eprintln!("Determinism gate failed; report retained for diagnosis.");
            process::exit(2);
        }
        Ok(_) => {}
        Err(error) => {
            eprintln!("error: {error:#}");
            process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn input_hash_is_independent_of_input_order() {
        let a = vec![
            InputTensor { name: "y".into(), shape: vec![2], data: TensorData::I64(vec![1, 2]) },
            InputTensor { name: "x".into(), shape: vec![1], data: TensorData::F32(vec![-0.0]) },
        ];
        let mut b = a.clone();
        b.reverse();
        assert_eq!(input_hash(&a), input_hash(&b));
    }

    #[test]
    fn input_hash_preserves_float_bit_patterns() {
        let p = InputTensor { name: "x".into(), shape: vec![1], data: TensorData::F32(vec![0.0]) };
        let n = InputTensor { name: "x".into(), shape: vec![1], data: TensorData::F32(vec![-0.0]) };
        assert_ne!(input_hash(&[p]), input_hash(&[n]));
    }

    #[test]
    fn timing_statistics_use_median_and_nearest_rank_p95() {
        let s = stats(&[50, 10, 40, 20, 30]).expect("non-empty samples should be accepted");
        assert_eq!(s.min_ns, 10);
        assert_eq!(s.median_ns, 30.0);
        assert_eq!(s.p95_ns, 50);
        assert_eq!(s.max_ns, 50);
    }

    #[test]
    fn timing_statistics_reject_empty_samples() {
        assert!(stats(&[]).is_err());
    }

    #[test]
    fn pipeline_digest_includes_runtime_and_platform_identity() {
        let base = pipeline_hash("model", "input", "output", "ORT-A", "linux", "x86_64");
        let other_runtime =
            pipeline_hash("model", "input", "output", "ORT-B", "linux", "x86_64");
        let other_platform =
            pipeline_hash("model", "input", "output", "ORT-A", "windows", "x86_64");

        assert_ne!(base, other_runtime);
        assert_ne!(base, other_platform);
    }
}
