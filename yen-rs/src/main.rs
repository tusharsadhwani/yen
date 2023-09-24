use std::path::PathBuf;

use clap::Parser;
use clap_verbosity_flag::Verbosity;
use env_logger::{Builder, WriteStyle};

use lazy_static::lazy_static;
use log::LevelFilter;

use commands::{create, list};
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
    static ref PYTHON_INSTALLS_PATH: PathBuf = home_dir().join(".yen_pythons");
    static ref YEN_CLIENT: Client = yen_client();
}

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
        Command::List(args) => list::execute(args).await,
    }
}
