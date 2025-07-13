// examples/simple_chat.rs
//
// A simple example demonstrating two agents discovering each other
// and exchanging chat messages using the agent communication library.

use agent_communication::{AgentNode, Result};
use serde_json::json;
use std::time::Duration;
use tokio::time::sleep;

#[tokio::main]
async fn main() -> Result<()> {
    println!("🚀 Starting Simple P2P Agent Chat Example");
    println!("==========================================");

    // Get command line arguments for agent configuration
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 3 {
        println!("Usage: {} <agent_name> <port>", args[0]);
        println!("Example: {} Alice 4001", args[0]);
        println!("\nTo test with two agents, run in separate terminals:");
        println!("  Terminal 1: {} Alice 4001", args[0]);
        println!("  Terminal 2: {} Bob 4002", args[0]);
        std::process::exit(1);
    }

    let agent_name = &args[1];
    let port: u16 = args[2].parse().unwrap_or_else(|_| {
        eprintln!("Error: Port must be a valid number");
        std::process::exit(1);
    });

    // Create the agent node
    let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", port);
    let mut agent = AgentNode::new(agent_name, &listen_addr).await?;

    println!("✅ Agent '{}' created successfully", agent_name);
    println!("🔍 Listening for peers and ready for communication...");
    println!("💡 This agent will automatically discover other agents on the network");
    println!("📝 Type 'quit' to exit\n");

    // Run the agent
    agent.run().await?;

    Ok(())
}

// Alternative: A more advanced example with custom message handling
// #[allow(dead_code)]
// async fn advanced_example() -> Result<()> {
//     use agent_communication::{AgentConfig, AgentNodeBuilder};
//     use libp2p::identity;
//
//     println!("🔧 Advanced P2P Agent Example with Custom Configuration");
//
//     // Generate a specific keypair for reproducible identity
//     let keypair = identity::Keypair::generate_ed25519();
//
//     // Build custom agent configuration
//     let config = AgentNodeBuilder::new()
//         .with_keypair(keypair)
//         .with_listen_addr("/ip4/0.0.0.0/tcp/4001")
//         .with_listen_addr("/ip4/127.0.0.1/tcp/4002") // Listen on multiple addresses
//         .with_protocol("/my-agents/1.0.0") // Custom protocol
//         .build();
//
//     // Create agent with custom config
//     let mut agent = AgentNode::from_config("AdvancedAgent", config).await?;
//
//     println!("🎯 Advanced agent configured with custom protocol and multiple addresses");
//
//     // Run the agent
//     agent.run().await?;
//
//     Ok(())
// }

// Example of running multiple agents programmatically for testing
#[allow(dead_code)]
async fn multi_agent_test() -> Result<()> {
    println!("🌐 Multi-Agent Test Example");

    // Configuration for multiple agents
    let agents = vec![("Alice", 4001), ("Bob", 4002), ("Charlie", 4003)];

    let mut handles = vec![];

    // Spawn each agent in its own task
    for (name, port) in agents {
        let agent_name = name.to_string();

        let handle = tokio::spawn(async move {
            let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", port);

            // Small delay to avoid startup conflicts
            sleep(Duration::from_millis(100)).await;

            match AgentNode::new(&agent_name, &listen_addr).await {
                Ok(mut agent) => {
                    println!("✅ Agent {} started on port {}", agent_name, port);
                    if let Err(e) = agent.run().await {
                        eprintln!("❌ Agent {} error: {:?}", agent_name, e);
                    }
                }
                Err(e) => {
                    eprintln!("❌ Failed to create agent {}: {:?}", agent_name, e);
                }
            }
        });

        handles.push(handle);
    }

    println!("🚀 All agents started! They should discover each other automatically.");
    println!("💬 Watch for discovery messages and automatic greetings...");

    // Wait for all agents to complete (they run indefinitely)
    for handle in handles {
        if let Err(e) = handle.await {
            eprintln!("❌ Agent task error: {:?}", e);
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::timeout;

    #[tokio::test]
    async fn test_agent_creation() {
        // Test that we can create an agent successfully
        let result = AgentNode::new("TestAgent", "/ip4/127.0.0.1/tcp/0").await;
        assert!(result.is_ok(), "Failed to create test agent");

        let agent = result.unwrap();
        assert_eq!(agent.name, "TestAgent");
        println!("✅ Agent creation test passed");
    }

    #[tokio::test]
    async fn test_agent_with_builder() {
        use agent_communication::AgentNodeBuilder;

        // Test using the builder pattern
        let config = AgentNodeBuilder::new()
            .with_listen_addr("/ip4/127.0.0.1/tcp/0")
            .with_protocol("/test/1.0.0")
            .build();

        let result = AgentNode::from_config("BuilderAgent", config).await;
        assert!(result.is_ok(), "Failed to create agent with builder");

        let agent = result.unwrap();
        assert_eq!(agent.name, "BuilderAgent");
        assert_eq!(agent.protocol, "/test/1.0.0");
        println!("✅ Agent builder test passed");
    }

    #[tokio::test]
    async fn test_two_agents_basic() {
        // Basic test to ensure two agents can be created without conflicts
        let agent1_result = AgentNode::new("Agent1", "/ip4/127.0.0.1/tcp/0").await;
        let agent2_result = AgentNode::new("Agent2", "/ip4/127.0.0.1/tcp/0").await;

        assert!(agent1_result.is_ok(), "Failed to create Agent1");
        assert!(agent2_result.is_ok(), "Failed to create Agent2");

        println!("✅ Two agent creation test passed");
    }
}

// Utility functions for the example

/// Helper function to print usage instructions
fn print_usage() {
    println!("📖 Usage Instructions:");
    println!("====================");
    println!();
    println!("1. Basic Usage:");
    println!("   cargo run --example simple_chat Alice 4001");
    println!("   cargo run --example simple_chat Bob 4002");
    println!();
    println!("2. What happens:");
    println!("   - Each agent starts listening on the specified port");
    println!("   - Agents automatically discover each other using mDNS");
    println!("   - Once discovered, they exchange welcome messages");
    println!("   - Agents continue to send periodic greetings");
    println!();
    println!("3. Network Requirements:");
    println!("   - Agents must be on the same local network for mDNS discovery");
    println!("   - Firewall should allow the specified ports");
    println!("   - IPv4 networking should be available");
    println!();
    println!("4. Testing:");
    println!("   cargo test --example simple_chat");
}

/// Helper function to validate port availability
fn validate_port(port: u16) -> bool {
    match std::net::TcpListener::bind(format!("127.0.0.1:{}", port)) {
        Ok(_) => true,
        Err(_) => {
            eprintln!("⚠️  Port {} appears to be in use", port);
            false
        }
    }
}
