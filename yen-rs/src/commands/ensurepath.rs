use std::process::Command;

use clap::Parser;
use miette::IntoDiagnostic;

use crate::{
    utils::{_ensure_userpath, find_or_download_python},
    PACKAGE_INSTALLS_PATH, USERPATH_PATH,
};

/// Ensures that `YEN_PACKAGES_PATH` is in PATH.
#[derive(Parser, Debug)]
pub struct Args;

/// Ensures that PACKAGE_INSTALLS_PATH is in PATH
async fn ensurepath() -> miette::Result<()> {
    _ensure_userpath().await?;

    let python_bin_path = find_or_download_python().await?;
    println!("{python_bin_path}");
    let stdout = Command::new(format!("{}", python_bin_path.to_string_lossy()))
        .args([
            &USERPATH_PATH.to_string_lossy(),
            "append",
            &PACKAGE_INSTALLS_PATH.to_string_lossy(),
        ])
        .output()
        .into_diagnostic()?;

    if !stdout.status.success() {
        miette::bail!(format!(
            "Error: unable to append `YEN_PACKAGES_PATH` to `PATH`!\nStdout: {}\nStderr: {}",
            String::from_utf8_lossy(&stdout.stdout),
            String::from_utf8_lossy(&stdout.stderr),
        ));
    }

    Ok(())
}

pub async fn execute(_args: Args) -> miette::Result<()> {
    ensurepath().await?;
    println!(
        "`{}` is now present in your PATH. Restart your shell for it to take effect.",
        PACKAGE_INSTALLS_PATH.display(),
    );
    Ok(())
}
