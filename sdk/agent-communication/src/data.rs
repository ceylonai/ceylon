/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */

use libp2p::{Multiaddr, PeerId, identity};
use serde::ser::SerializeStruct;
use serde::{Deserialize, Serialize};

/// Holds configuration needed to start an Agent Node.
#[derive(Debug, Clone)]
pub struct AgentConfig {
    /// The agent's cryptographic keypair (optional).
    pub keypair: Option<identity::Keypair>,
    /// The agent's PeerId (derived from keypair if missing).
    pub peer_id: PeerId,

    /// Addresses this agent should listen on.
    pub listen_addrs: Vec<Multiaddr>,

    /// Protocol ID this agent uses.
    pub protocol: String,

    /// Request timeout in seconds.
    pub request_timeout_secs: u64,

    /// Keep-alive duration in seconds.
    pub keep_alive_secs: u64,
}

impl Serialize for AgentConfig {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let mut state = serializer.serialize_struct("AgentConfig", 6)?;
        state.serialize_field("keypair", "--")?;
        state.serialize_field("peer_id", &self.peer_id.to_string())?;
        state.serialize_field("listen_addrs", &self.listen_addrs)?;
        state.serialize_field("protocol", &self.protocol)?;
        state.serialize_field("request_timeout_secs", &self.request_timeout_secs)?;
        state.serialize_field("keep_alive_secs", &self.keep_alive_secs)?;
        state.end()
    }
}

impl<'de> Deserialize<'de> for AgentConfig {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let s = <String>::deserialize(deserializer).map_err(serde::de::Error::custom)?; // String
        serde_json::from_str(&s).map_err(serde::de::Error::custom) // AgentConfig
    }
}

impl AgentConfig {
    /// Create a new AgentConfig with sensible defaults.
    pub fn new(
        keypair: Option<identity::Keypair>,
        listen_addrs: Vec<Multiaddr>,
        protocol: &str,
    ) -> Self {
        let actual_keypair = keypair.unwrap_or_else(identity::Keypair::generate_ed25519);
        let peer_id = PeerId::from(actual_keypair.public());

        Self {
            keypair: Some(actual_keypair),
            peer_id,
            listen_addrs,
            protocol: protocol.to_string(),
            request_timeout_secs: 10,
            keep_alive_secs: 60,
        }
    }

    /// Customize the request timeout.
    pub fn with_request_timeout_secs(mut self, secs: u64) -> Self {
        self.request_timeout_secs = secs;
        self
    }

    /// Customize the keep-alive duration.
    pub fn with_keep_alive_secs(mut self, secs: u64) -> Self {
        self.keep_alive_secs = secs;
        self
    }
}
