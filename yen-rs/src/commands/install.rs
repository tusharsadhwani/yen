use std::{os::unix::fs::PermissionsExt, path::PathBuf, process::Command, str::FromStr};

use clap::Parser;
use miette::IntoDiagnostic;

use crate::{
    github::Version,
    utils::{_ensure_userpath, ensure_python, find_or_download_python},
    DEFAULT_PYTHON_VERSION, PACKAGE_INSTALLS_PATH, USERPATH_PATH,
};

use super::create::create_env;

#[cfg(target_os = "windows")]
const IS_WINDOWS: bool = true;
#[cfg(not(target_os = "windows"))]
const IS_WINDOWS: bool = false;

/// Install a Python package in an isolated environment.
#[derive(Parser, Debug)]
pub struct Args {
    /// Name of package to install
    #[arg(required = true)]
    package_name: String,

    /// Python version to install package with
    #[arg(short, long, default_value_t = Version::from_str(DEFAULT_PYTHON_VERSION).unwrap())]
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
        &package_name,
        python_bin_path,
        &executable_name,
        is_module,
        args.force_reinstall,
    )
    .await?;

    if already_installed {
        println!("Package {package_name} is already installed.");
    } else {
        println!("Installed package {package_name} with Python {python_version} ✨");
    }

    check_path(PACKAGE_INSTALLS_PATH.to_path_buf()).await?;
    Ok(())
}

async fn check_path(path: PathBuf) -> miette::Result<()> {
    let path_exists = if IS_WINDOWS {
        _ensure_userpath().await?;
        let python_bin_path = find_or_download_python().await?;
        let stdout = Command::new(format!("{}", python_bin_path.to_string_lossy()))
            .args([
                &USERPATH_PATH.to_string_lossy(),
                "check",
                &path.to_string_lossy(),
            ])
            .output()
            .into_diagnostic()?;

        stdout.status.success()
    } else {
        match std::env::var_os("PATH") {
            Some(paths) => std::env::split_paths(&paths)
                .find(|element| *element == path)
                .is_some(),
            None => miette::bail!("Failed to read $PATH variable"),
        }
    };

    if !path_exists {
        eprintln!(
            "\x1b[1;33mWarning: The executable just installed is not in PATH.\n\
            Run `yen ensurepath` to add it to your PATH.\x1b[m",
        )
    }

    Ok(())
}

fn _venv_binary_path(binary_name: &str, venv_path: &std::path::PathBuf) -> std::path::PathBuf {
    let venv_bin_path = venv_path.join(if IS_WINDOWS { "Scripts" } else { "bin" });
    let binary_path = venv_bin_path.join(if IS_WINDOWS {
        format!("{binary_name}.exe")
    } else {
        binary_name.to_string()
    });
    return binary_path;
}

pub async fn install_package(
    package_name: &str,
    python_bin_path: std::path::PathBuf,
    executable_name: &str,
    is_module: bool,
    force_reinstall: bool,
) -> miette::Result<bool> {
    let venv_name = format!("venv_{package_name}");
    let venv_path = PACKAGE_INSTALLS_PATH.join(venv_name);
    if venv_path.exists() {
        if !force_reinstall {
            return Ok(true); // true as in package already exists
        } else {
            std::fs::remove_dir_all(&venv_path).into_diagnostic()?;
        };
    };

    create_env(python_bin_path, &venv_path).await?;

    let venv_python_path = _venv_binary_path("python", &venv_path);
    let venv_python_path = venv_python_path.to_string_lossy();

    let stdout = Command::new(format!("{venv_python_path}"))
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

    let mut shim_path = PACKAGE_INSTALLS_PATH.join(&package_name);
    if is_module {
        if IS_WINDOWS {
            shim_path = PathBuf::from(shim_path.to_string_lossy().into_owned() + ".bat");
        }

        if IS_WINDOWS {
            std::fs::write(
                &shim_path,
                format!("@echo off\n{venv_python_path} -m {package_name} %*"),
            )
            .into_diagnostic()?;
        } else {
            std::fs::write(
                &shim_path,
                format!("#!/bin/sh\n{venv_python_path} -m {package_name} \"$@\""),
            )
            .into_diagnostic()?;
        }

        let mut perms = std::fs::metadata(&shim_path)
            .into_diagnostic()?
            .permissions();
        perms.set_mode(0o777);
        std::fs::set_permissions(&shim_path, perms).into_diagnostic()?;
    } else {
        if IS_WINDOWS {
            shim_path = PathBuf::from(shim_path.to_string_lossy().into_owned() + ".exe");
        }
        let executable_path = _venv_binary_path(&executable_name, &venv_path);
        if !executable_path.exists() {
            // cleanup the venv created
            std::fs::remove_dir_all(&venv_path).into_diagnostic()?;
            if executable_name == package_name && !is_module {
                miette::bail!(
                    "Error: Executable {executable_name} does not exist in package {package_name}. \
                    Consider passing `--binary` or `--module` flags."
                );
            } else {
                miette::bail!(
                    "Error: Executable {executable_name} does not exist in package {package_name}."
                );
            }
        }
        // the created binary is always moveable
        std::fs::rename(executable_path, shim_path).into_diagnostic()?;
    }

    Ok(false) // false as in it didn't already exist and was installed just now.
}
