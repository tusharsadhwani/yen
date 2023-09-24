use clap::Parser;

use crate::github::list_pythons;

/// List available python versions to create virtual env.
#[derive(Parser, Debug)]
pub struct Args;

pub async fn execute(_args: Args) -> miette::Result<()> {
    let pythons = list_pythons().await?;
    println!("Available Pythons:");
    for v in pythons.keys().rev() {
        println!("{v}");
    }

    Ok(())
}
