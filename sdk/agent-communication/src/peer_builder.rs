/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */

use crate::data::AgentConfig;
use libp2p::{PeerId, identity};

#[derive(Debug, Default)]
pub struct AgentNodeBuilder {
    keypair: Option<identity::Keypair>,
    listen_addrs: Vec<String>,
    protocol: String,
}

impl AgentNodeBuilder {
    pub fn new() -> Self {
        Self {
            protocol: "/anp/1.0.0".to_string(),
            ..Default::default()
        }
    }

    pub fn with_keypair(mut self, keypair: identity::Keypair) -> Self {
        self.keypair = Some(keypair);
        self
    }

    pub fn with_listen_addr(mut self, addr: &str) -> Self {
        self.listen_addrs.push(addr.to_string());
        self
    }

    pub fn with_protocol(mut self, protocol: &str) -> Self {
        self.protocol = protocol.to_string();
        self
    }

    pub fn build(self) -> AgentConfig {
        let keypair = self
            .keypair
            .unwrap_or_else(identity::Keypair::generate_ed25519);
        let peer_id = PeerId::from(keypair.public());

        AgentConfig {
            keypair: Some(keypair),
            peer_id,
            listen_addrs: self
                .listen_addrs
                .iter()
                .map(|addr| addr.parse().unwrap())
                .collect(),
            protocol: self.protocol,
            request_timeout_secs: 10,
            keep_alive_secs: 60,
        }
    }
}
