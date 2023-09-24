use std::path::PathBuf;

use clap::Parser;

use crate::{
    github::Version,
    utils::{create_env, ensure_python},
};

/// Create venv with python version
#[derive(Parser, Debug)]
#[clap(arg_required_else_help = true)]
pub struct Args {
    /// Path to venv
    #[arg(required = true)]
    path: PathBuf,

    /// Python version to create venv
    #[arg(short, long, required = true)]
    python: Version,
}

pub async fn execute(args: Args) -> miette::Result<()> {
    let (python_version, python_bin_path) = ensure_python(args.python).await?;
    create_env(python_version, python_bin_path, args.path).await?;
    Ok(())
}
