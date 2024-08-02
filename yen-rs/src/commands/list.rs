use clap::Parser;

use crate::github::list_pythons;

/// List available python versions to create virtual env.
#[derive(Parser, Debug)]
pub struct Args {
    /// Force downloading a 32 bit Python version
    #[arg(long, alias = "32bit")]
    force_32bit: bool,
}

pub async fn execute(args: Args) -> miette::Result<()> {
    let pythons = list_pythons(args.force_32bit).await?;
    if pythons.is_empty() {
        miette::bail!(
            "No Python versions available for your machine. \
            Please report this: https://github.com/tusharsadhwani/yen/issues/new"
        );
    }

    eprintln!("Available Pythons:");
    for v in pythons.keys().rev() {
        println!("{v}");
    }

    Ok(())
}
