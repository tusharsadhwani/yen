use std::{process::Command, str::FromStr};

use clap::Parser;
use miette::IntoDiagnostic;

use crate::{github::Version, utils::ensure_python, PACKAGE_INSTALLS_PATH};

use super::create::create_env;

/// List available python versions to create virtual env.
#[derive(Parser, Debug)]
pub struct Args {
    /// Name of package to install
    #[arg(required = true)]
    package_name: String,

    /// Python version to install package with
    #[arg(short, long, default_value_t = Version::from_str("3.12").unwrap())]
    python: Version,

    /// Name of command installed by package. Defaults to package name itself.
    #[arg(long)]
    binary: Option<String>,
    /// Use if package should be run as a module, i.e. `python -m <module_name>`
    #[arg(long)]
    module: Option<String>,

    #[arg(long)]
    force_reinstall: bool,
}

pub async fn execute(args: Args) -> miette::Result<()> {
    if args.module.is_some() && args.binary.is_some() {
        miette::bail!("Error: cannot pass `--binary-name` and `--module-name` together.");
    }

    let (python_version, python_bin_path) = ensure_python(args.python).await?;

    let package_name = args.package_name;
    let is_module = args.module.is_some();
    let executable_name = args.module.or(args.binary).unwrap_or(package_name.clone());

    let already_installed = install_package(
        package_name,
        python_bin_path,
        executable_name,
        is_module,
        args.force_reinstall,
    )
    .await?;

    Ok(())
}

fn _venv_binary_path(binary_name: &str, venv_path: &std::path::PathBuf) -> std::path::PathBuf {
    #[cfg(target_os = "windows")]
    let is_windows = true;
    #[cfg(not(target_os = "windows"))]
    let is_windows = false;

    let venv_bin_path = venv_path.join(if is_windows { "Scripts" } else { "bin" });
    let binary_path = venv_bin_path.join(if is_windows {
        format!("{binary_name}.exe")
    } else {
        binary_name.to_string()
    });
    return binary_path;
}

async fn install_package(
    package_name: String,
    python_bin_path: std::path::PathBuf,
    executable_name: String,
    is_module: bool,
    force_reinstall: bool,
) -> miette::Result<bool> {
    let venv_name = format!("venv_{package_name}");
    let venv_path = PACKAGE_INSTALLS_PATH.join(venv_name);
    if venv_path.exists() {
        if !force_reinstall {
            miette::bail!(format!(
                "Error: {} already exists.",
                venv_path.to_string_lossy()
            ));
        } else {
            std::fs::remove_dir_all(&venv_path).into_diagnostic()?;
        };
    };

    create_env(python_bin_path, &venv_path).await?;

    let venv_python_path = _venv_binary_path("python", &venv_path);

    let stdout = Command::new(format!("{}", venv_python_path.to_string_lossy()))
        .args(["-m", "pip", "install", &package_name])
        .output()
        .into_diagnostic()?;

    if !stdout.status.success() {
        miette::bail!(format!(
            "Error: pip install failed!\nStdout: {}\nStderr: {}",
            String::from_utf8_lossy(&stdout.stdout),
            String::from_utf8_lossy(&stdout.stderr),
        ));
    }

    Ok(true)
}
