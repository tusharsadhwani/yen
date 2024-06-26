use std::{
    process::{exit, Command, Stdio},
    str::FromStr,
};

use clap::Parser;
use miette::IntoDiagnostic;

use crate::{github::Version, utils::ensure_python, DEFAULT_PYTHON_VERSION, PACKAGE_INSTALLS_PATH};

use super::install::install_package;

/// Install and run a Python package.
#[derive(Parser, Debug)]
pub struct Args {
    /// Name of package to install
    #[arg(required = true)]
    package_name: String,

    /// Python version to install package with
    #[arg(short, long, default_value_t = Version::from_str(DEFAULT_PYTHON_VERSION).unwrap())]
    python: Version,

    /// Arguments to pass to the command invocation
    #[arg(num_args = 0..)]
    run_args: Vec<String>,
}

pub async fn execute(args: Args) -> miette::Result<()> {
    let (_, python_bin_path) = ensure_python(args.python).await?;

    let package_name = args.package_name;
    let (shim_path, _) =
        install_package(&package_name, python_bin_path, &package_name, false, false).await?;

    let output = Command::new(shim_path)
        .args(args.run_args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .output()
        .into_diagnostic()?;

    exit(output.status.code().unwrap_or(1));
}
