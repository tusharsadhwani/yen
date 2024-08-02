use std::{
    process::{exit, Command, Stdio},
    str::FromStr,
};

use clap::Parser;
use miette::IntoDiagnostic;

use crate::{github::Version, utils::ensure_python, DEFAULT_PYTHON_VERSION};

/// Install and run a Python package.
#[derive(Parser, Debug)]
pub struct Args {
    /// Python version to install package with
    #[arg(short, long, default_value_t = Version::from_str(DEFAULT_PYTHON_VERSION).unwrap())]
    python: Version,

    /// Force downloading a 32 bit Python version
    #[arg(long, alias = "32bit")]
    force_32bit: bool,

    /// Arguments to pass to the command invocation
    #[arg(num_args = 0..)]
    run_args: Vec<String>,
}

pub async fn execute(args: Args) -> miette::Result<()> {
    let (_, python_bin_path) = ensure_python(args.python, args.force_32bit).await?;

    let output = Command::new(python_bin_path)
        .args(args.run_args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .output()
        .into_diagnostic()?;

    exit(output.status.code().unwrap_or(1));
}
