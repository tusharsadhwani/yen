use std::path::PathBuf;

use clap::Parser;
use clap_verbosity_flag::Verbosity;
use env_logger::{Builder, WriteStyle};

use lazy_static::lazy_static;
use log::LevelFilter;

use commands::{create, ensurepath, exec, install, list, run};
use regex::Regex;
use reqwest::Client;

use crate::utils::{home_dir, yen_client};

mod commands;
mod github;
mod utils;

lazy_static! {
    static ref GITHUB_API_URL: &'static str =
        "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest";
    static ref RE: Regex = Regex::new(r"cpython-(\d+\.\d+.\d+)").expect("Unable to create regex!");
    static ref GLIBC: Regex = Regex::new(r"GNU|GLIBC|glibc").expect("Unable to create regex!");
    static ref YEN_BIN_PATH: PathBuf = {
        std::path::absolute(match std::env::var("YEN_BIN_PATH") {
            Ok(yen_packages_path) => PathBuf::from(yen_packages_path),
            Err(_) => home_dir().join(".yen/bin"),
        })
        .expect("Failed to turn YEN_BIN_PATH into absolute")
    };
    static ref PYTHON_INSTALLS_PATH: PathBuf = {
        std::path::absolute(match std::env::var("YEN_PYTHONS_PATH") {
            Ok(yen_packages_path) => PathBuf::from(yen_packages_path),
            Err(_) => home_dir().join(".yen_pythons"),
        })
        .expect("Failed to turn YEN_BIN_PATH into absolute")
    };
    static ref PACKAGE_INSTALLS_PATH: PathBuf = {
        std::path::absolute(match std::env::var("YEN_PACKAGES_PATH") {
            Ok(yen_packages_path) => PathBuf::from(yen_packages_path),
            Err(_) => home_dir().join(".yen_packages"),
        })
        .expect("Failed to turn YEN_BIN_PATH into absolute")
    };
    static ref USERPATH_PATH: PathBuf = YEN_BIN_PATH.join("userpath.pyz");
    static ref MICROVENV_PATH: PathBuf = YEN_BIN_PATH.join("microvenv.py");
    static ref YEN_CLIENT: Client = yen_client();
}

static DEFAULT_PYTHON_VERSION: &'static str = "3.12";

/// Create python virtual environments with minimal effort.
#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
#[clap(arg_required_else_help = true)]
struct Args {
    #[command(subcommand)]
    command: Command,

    /// Verbosity level
    #[command(flatten)]
    verbose: Verbosity,
}

#[derive(Parser, Debug)]
enum Command {
    #[clap(alias = "l")]
    List(list::Args),
    #[clap(alias = "c")]
    Create(create::Args),
    Ensurepath(ensurepath::Args),
    Exec(exec::Args),
    Install(install::Args),
    Run(run::Args),
}

fn main() {
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        if let Err(err) = execute(Args::parse()).await {
            eprintln!("{err:?}");
            std::process::exit(1);
        }
    })
}

async fn execute(args: Args) -> miette::Result<()> {
    let level = match args.verbose.log_level_filter() {
        clap_verbosity_flag::LevelFilter::Off => LevelFilter::Off,
        clap_verbosity_flag::LevelFilter::Error => LevelFilter::Error,
        clap_verbosity_flag::LevelFilter::Warn => LevelFilter::Warn,
        clap_verbosity_flag::LevelFilter::Info => LevelFilter::Info,
        clap_verbosity_flag::LevelFilter::Debug => LevelFilter::Debug,
        clap_verbosity_flag::LevelFilter::Trace => LevelFilter::Trace,
    };

    Builder::new()
        .filter(None, level)
        .write_style(WriteStyle::Always)
        .init();

    match args.command {
        Command::Create(args) => create::execute(args).await,
        Command::Ensurepath(args) => ensurepath::execute(args).await,
        Command::Exec(args) => exec::execute(args).await,
        Command::List(args) => list::execute(args).await,
        Command::Install(args) => install::execute(args).await,
        Command::Run(args) => run::execute(args).await,
    }
}
