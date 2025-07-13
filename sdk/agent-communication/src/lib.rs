//! # Agent Communication Library
//!
//! A peer-to-peer agent communication library built on libp2p, implementing the ANP (Agent Network Protocol).
//!
//! ## Features
//!
//! - **P2P Communication**: Built on libp2p for robust peer-to-peer networking
//! - **ANP Protocol**: Custom Agent Network Protocol for structured message exchange  
//! - **Auto-Discovery**: mDNS-based automatic peer discovery on local networks
//! - **Type-Safe Messaging**: Structured message types with serialization support
//! - **Connection Management**: Automatic connection handling and peer management
//!
//! ## Quick Start
//!
//! ```rust,no_run
//! use agent_communication::{AgentNode, AgentConfig};
//! use libp2p::Multiaddr;
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     // Create a simple agent node
//!     let mut node = AgentNode::new("MyAgent", "/ip4/0.0.0.0/tcp/4001").await?;
//!     
//!     // Run the node (this will handle discovery and messaging)
//!     node.run().await
//! }
//! ```
//!
//! ## Architecture
//!
//! The library is organized into several core modules:
//!
//! - [`anp`] - ANP message format and protocol definitions
//! - [`messaging`] - Low-level message codec and protocol handling
//! - [`behaviour`] - libp2p behavior combining RequestResponse and mDNS
//! - [`node`] - High-level agent node implementation
//! - [`peer`] - Peer representation and management
//! - [`data`] - Configuration and data structures
//! - [`handlers`] - Message handling logic

pub mod messaging;
pub mod peer;
pub mod peer_swarm;
pub mod peer_builder;
pub mod data;
pub mod core;
pub mod protocol;
pub mod network;

// Re-export commonly used types for convenience
pub use libp2p::{PeerId, Multiaddr};

// Re-export main types users will need
pub use protocol::anp::AnpMessage;
pub use network::behaviour::{AgentBehaviour, AgentEvent};
pub use data::AgentConfig;
pub use messaging::{AnpRequest, AnpResponse, AnpCodec, ANP_PROTOCOL};
pub use core::node::AgentNode;
pub use peer::Peer;
pub use peer_builder::AgentNodeBuilder;
pub use peer_swarm::PeerManager;

/// A simple addition function for basic testing
///
/// This function is kept for backward compatibility with existing tests.
pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}

/// Result type alias for convenience
pub type Result<T> = anyhow::Result<T>;