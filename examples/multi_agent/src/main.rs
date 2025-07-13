// examples/multi_agent.rs
//
// Example showing multiple agents in a network, demonstrating
// automatic discovery and message broadcasting.

use agent_communication::{AgentNode, AgentNodeBuilder, Result};
use std::time::Duration;
use tokio::time::sleep;

#[tokio::main]
async fn main() -> Result<()> {
    println!("🌐 Multi-Agent Network Example");
    println!("==============================");

    // Enable logging for better visibility
    #[cfg(feature = "verbose")]
    setup_logging();

    // Configuration for our agent network
    let agents = vec![
        AgentConfig {
            name: "Alice".to_string(),
            port: 4001,
            role: "coordinator",
        },
        AgentConfig {
            name: "Bob".to_string(),
            port: 4002,
            role: "worker",
        },
        AgentConfig {
            name: "Charlie".to_string(),
            port: 4003,
            role: "worker",
        },
        AgentConfig {
            name: "Diana".to_string(),
            port: 4004,
            role: "observer",
        },
    ];

    println!("🚀 Starting {} agents...", agents.len());

    let mut handles = vec![];

    // Start each agent
    for config in agents {
        let handle = tokio::spawn(async move {
            if let Err(e) = run_agent(config).await {
                eprintln!("❌ Agent error: {:?}", e);
            }
        });
        handles.push(handle);

        // Small delay between agent starts
        sleep(Duration::from_millis(200)).await;
    }

    println!("✅ All agents started!");
    println!("🔍 Agents will automatically discover each other");
    println!("💬 Watch for discovery and messaging activity");
    println!("⏹️  Press Ctrl+C to stop all agents\n");

    // Wait for all agents (they run indefinitely)
    for handle in handles {
        if let Err(e) = handle.await {
            eprintln!("❌ Agent task failed: {:?}", e);
        }
    }

    Ok(())
}

#[derive(Debug, Clone)]
struct AgentConfig {
    name: String,
    port: u16,
    role: &'static str,
}

async fn run_agent(config: AgentConfig) -> Result<()> {
    println!(
        "🤖 Starting {} ({}) on port {}",
        config.name, config.role, config.port
    );

    // Create agent with role-specific configuration
    let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", config.port);

    let agent_config = AgentNodeBuilder::new()
        .with_listen_addr(&listen_addr)
        .with_protocol("/multi-agent-demo/1.0.0")
        .build();

    let mut agent = AgentNode::from_config(&config.name, agent_config).await?;

    println!("✅ {} is ready for networking", config.name);

    // Run the agent
    agent.run().await?;

    Ok(())
}

// Example with custom behavior based on agent roles
#[allow(dead_code)]
async fn run_agent_with_custom_behavior(config: AgentConfig) -> Result<()> {
    use serde_json::json;

    let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", config.port);
    let mut agent = AgentNode::new(&config.name, &listen_addr).await?;

    // Simulate role-specific behavior
    tokio::spawn({
        let role = config.role;
        let name = config.name.clone();
        async move {
            role_specific_tasks(name, role).await;
        }
    });

    agent.run().await
}

async fn role_specific_tasks(name: String, role: &'static str) {
    let mut interval = tokio::time::interval(Duration::from_secs(15));

    loop {
        interval.tick().await;

        match role {
            "coordinator" => {
                println!("📋 [{}] Coordinator checking network status...", name);
            }
            "worker" => {
                println!("⚙️  [{}] Worker ready for tasks...", name);
            }
            "observer" => {
                println!("👁️  [{}] Observer monitoring network...", name);
            }
            _ => {
                println!("🤖 [{}] Agent active...", name);
            }
        }
    }
}

// Demonstration of network scaling
#[allow(dead_code)]
async fn scalability_demo() -> Result<()> {
    println!("📈 Network Scalability Demo");
    println!("==========================");

    let agent_count = 10;
    let mut handles = vec![];

    for i in 0..agent_count {
        let agent_name = format!("Agent{:02}", i + 1);
        let port = 4000 + i + 1;

        let handle = tokio::spawn(async move {
            let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", port);

            match AgentNode::new(&agent_name, &listen_addr).await {
                Ok(mut agent) => {
                    println!("✅ {} joined the network", agent_name);
                    if let Err(e) = agent.run().await {
                        eprintln!("❌ {} error: {:?}", agent_name, e);
                    }
                }
                Err(e) => {
                    eprintln!("❌ Failed to create {}: {:?}", agent_name, e);
                }
            }
        });

        handles.push(handle);

        // Stagger agent creation
        sleep(Duration::from_millis(500)).await;
    }

    println!("🌐 {} agents are now forming a network", agent_count);

    // Let agents run for a while to see discovery in action
    for handle in handles {
        if let Err(e) = handle.await {
            eprintln!("❌ Agent error: {:?}", e);
        }
    }

    Ok(())
}

// Network topology visualization helper
#[allow(dead_code)]
fn print_network_topology() {
    println!("🗺️  Network Topology:");
    println!("     ┌─────────┐");
    println!("     │  Alice  │ ← Coordinator");
    println!("     │ (4001)  │");
    println!("     └────┬────┘");
    println!("          │");
    println!("     ┌────┴────┐");
    println!("     │         │");
    println!("┌────▼───┐ ┌───▼────┐ ┌─────────┐");
    println!("│  Bob   │ │Charlie │ │  Diana  │");
    println!("│ (4002) │ │ (4003) │ │ (4004)  │");
    println!("│Worker  │ │Worker  │ │Observer │");
    println!("└────────┘ └────────┘ └─────────┘");
    println!();
}

#[cfg(feature = "verbose")]
fn setup_logging() {
    use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .init();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_config_creation() {
        let config = AgentConfig {
            name: "TestAgent".to_string(),
            port: 4001,
            role: "test",
        };

        assert_eq!(config.name, "TestAgent");
        assert_eq!(config.port, 4001);
        assert_eq!(config.role, "test");
    }

    #[tokio::test]
    async fn test_multiple_agent_creation() {
        // Test creating multiple agents with different configs
        let configs = vec![
            AgentConfig {
                name: "Agent1".to_string(),
                port: 5001,
                role: "worker",
            },
            AgentConfig {
                name: "Agent2".to_string(),
                port: 5002,
                role: "observer",
            },
        ];

        for config in configs {
            let listen_addr = format!("/ip4/127.0.0.1/tcp/{}", config.port);
            let result = AgentNode::new(&config.name, &listen_addr).await;
            assert!(result.is_ok(), "Failed to create agent {}", config.name);
        }
    }
}
