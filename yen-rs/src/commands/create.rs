use std::{path::PathBuf, process::Command};

use clap::Parser;
use miette::IntoDiagnostic;

use crate::{
    github::Version,
    utils::{_ensure_microvenv, ensure_python},
    MICROVENV_PATH,
};

/// Create venv with python version
#[derive(Parser, Debug)]
#[clap(arg_required_else_help = true)]
pub struct Args {
    /// Path to venv
    #[arg(required = true)]
    venv_path: PathBuf,

    /// Python version to create venv
    #[arg(short, long, required = true)]
    python: Version,
}

pub async fn create_env(python_bin_path: PathBuf, venv_path: &PathBuf) -> miette::Result<()> {
    if venv_path.exists() {
        miette::bail!("Error: {} already exists!", venv_path.to_string_lossy());
    }

    _ensure_microvenv().await?;
    let stdout = Command::new(format!("{}", python_bin_path.to_string_lossy()))
        .args([
            &MICROVENV_PATH.to_string_lossy().into_owned(),
            &venv_path.to_string_lossy().into_owned(),
        ])
        .output()
        .into_diagnostic()?;

    if !stdout.status.success() {
        miette::bail!(format!(
            "Error: unable to create venv!\nStdout: {}\nStderr: {}",
            String::from_utf8_lossy(&stdout.stdout),
            String::from_utf8_lossy(&stdout.stderr),
        ));
    }

    Ok(())
}

pub async fn execute(args: Args) -> miette::Result<()> {
    let (python_version, python_bin_path) = ensure_python(args.python).await?;
    create_env(python_bin_path, &args.venv_path).await?;
    println!(
        "Created {} with Python {} ✨",
        args.venv_path.to_string_lossy(),
        python_version
    );
    Ok(())
}
