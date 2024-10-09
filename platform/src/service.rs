mod manager;
use crate::manager::get_manager;
use clap::{Parser, Subcommand};

/// CLI for Ceylon Agent System
#[derive(Parser)]
#[command(version, about, long_about = None)]
#[command(propagate_version = true)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Agent registration and connection management
    Service {
        #[command(subcommand)]
        subcommand: ServiceCommands,
    },
}

/// Subcommands related to agent registration and connection
#[derive(Subcommand)]
enum ServiceCommands {
    /// Register a new agent in the network
    Start {
        /// Name of the agent to display details for
        #[arg(short, long)]
        name: String,
        port: u16,
        address: String,
    },
}
fn main() {
    let cli = Cli::parse();

    // Match the subcommands and handle each appropriately
    match &cli.command {
        Commands::Service { subcommand } => match subcommand {
            ServiceCommands::Start { name, port, address } => {
                println!("Starting agent: {} on port: {} and address: {}", name, port, address);


                tokio::runtime::Builder::new_multi_thread()
                    .enable_all()
                    .build()
                    .unwrap()
                    .block_on(async {
                        let admin = get_manager(name.clone(), *port);
                        admin.start(Vec::new(), Vec::new()).await;
                    });
            }
        },
    }
}