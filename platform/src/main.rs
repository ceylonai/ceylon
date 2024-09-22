mod manager;

use clap::{Parser, Subcommand};
use ceylon::AdminAgent;
use crate::manager::get_manager;

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
    Agent {
        #[command(subcommand)]
        subcommand: AgentCommands,
    },

    /// Agent management commands
    Manage {
        #[command(subcommand)]
        subcommand: ManageCommands,
    },
}

/// Subcommands related to agent registration and connection
#[derive(Subcommand)]
enum AgentCommands {
    /// Register a new agent in the network
    Register {
        /// Name of the agent to register
        #[arg(short, long)]
        name: String,

        /// Type of the agent (e.g., worker, coordinator)
        #[arg(short, long)]
        agent_type: String,
    },

    /// Connect an agent to another
    Connect {
        /// Name of the agent to connect
        #[arg(short, long)]
        name: String,

        /// Name of the target agent to connect to
        #[arg(short, long)]
        target: String,
    },
}

/// Subcommands related to agent management
#[derive(Subcommand)]
enum ManageCommands {
    /// List all active agents in the network
    List,

    /// Remove an agent from the network
    Remove {
        /// Name of the agent to remove
        #[arg(short, long)]
        name: String,
    },

    /// Show details of a specific agent
    Show {
        /// Name of the agent to display details for
        #[arg(short, long)]
        name: String,
    },

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
        Commands::Agent { subcommand } => match subcommand {
            AgentCommands::Register { name, agent_type } => {
                println!("Registering agent: {} of type: {}", name, agent_type);
                // Implement the actual logic to register the agent here
            }
            AgentCommands::Connect { name, target } => {
                println!("Connecting agent: {} to target agent: {}", name, target);
                // Implement the actual logic to connect the agent here
            }
        },
        Commands::Manage { subcommand } => match subcommand {
            ManageCommands::List => {
                println!("Listing all active agents...");
                // Implement the actual logic to list all agents here
            }
            ManageCommands::Remove { name } => {
                println!("Removing agent: {}", name);
                // Implement the actual logic to remove the agent here
            }
            ManageCommands::Show { name } => {
                println!("Showing details for agent: {}", name);
                // Implement the actual logic to show agent details here
            }
            ManageCommands::Start { name, port, address } => {
                println!("Starting agent: {} on port: {} and address: {}", name, port, address);

                tokio::runtime::Builder::new_multi_thread()
                    .enable_all()
                    .build()
                    .unwrap()
                    .block_on(async {
                        let admin = get_manager(name.clone(), *port);
                        admin.start(Vec::new(), Vec::new()).await;  
                    });
                
                // let admin = get_manager(name.clone(), *port);
                // admin.start(Vec::new(), Vec::new()).await;  
            }
        },
    }
}
