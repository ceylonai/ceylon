/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use std::hash::{DefaultHasher, Hash, Hasher};
use std::io;
use std::time::Duration;

use crate::peer::behaviour::PeerBehaviour;
use libp2p::swarm::NetworkBehaviour;
use libp2p::{gossipsub, identify, identity, ping, rendezvous};
use serde::{Deserialize, Serialize};

// Custom enum to handle both client and server rendezvous behaviors
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "RendezvousEvent")]
pub struct RendezvousBehaviour {
    pub(crate) client: rendezvous::client::Behaviour,
    server: rendezvous::server::Behaviour,
}

#[derive(Debug)]
pub enum RendezvousEvent {
    Client(rendezvous::client::Event),
    Server(rendezvous::server::Event),
}

impl From<rendezvous::client::Event> for RendezvousEvent {
    fn from(event: rendezvous::client::Event) -> Self {
        RendezvousEvent::Client(event)
    }
}

impl From<rendezvous::server::Event> for RendezvousEvent {
    fn from(event: rendezvous::server::Event) -> Self {
        RendezvousEvent::Server(event)
    }
}

// Unified network behavior
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "UnifiedPeerEvent")]
pub struct UnifiedPeerBehaviour {
    pub identify: identify::Behaviour,
    pub ping: ping::Behaviour,
    pub gossip_sub: gossipsub::Behaviour,
    pub rendezvous: RendezvousBehaviour,
}

#[derive(Debug)]
pub enum UnifiedPeerEvent {
    GossipSub(gossipsub::Event),
    Ping(ping::Event),
    Identify(identify::Event),
    Rendezvous(RendezvousEvent),
}

impl From<gossipsub::Event> for UnifiedPeerEvent {
    fn from(event: gossipsub::Event) -> Self {
        UnifiedPeerEvent::GossipSub(event)
    }
}

impl From<ping::Event> for UnifiedPeerEvent {
    fn from(event: ping::Event) -> Self {
        UnifiedPeerEvent::Ping(event)
    }
}

impl From<identify::Event> for UnifiedPeerEvent {
    fn from(event: identify::Event) -> Self {
        UnifiedPeerEvent::Identify(event)
    }
}

impl From<RendezvousEvent> for UnifiedPeerEvent {
    fn from(event: RendezvousEvent) -> Self {
        UnifiedPeerEvent::Rendezvous(event)
    }
}

impl RendezvousBehaviour {
    pub fn new(local_public_key: identity::Keypair) -> Self {
        Self {
            client: rendezvous::client::Behaviour::new(local_public_key.clone()),
            server: rendezvous::server::Behaviour::new(rendezvous::server::Config::default()),
        }
    }
}

impl PeerBehaviour for UnifiedPeerBehaviour {
    fn new(local_public_key: identity::Keypair) -> Self {
        let gossip_sub_config = create_gossip_sub_config();
        let gossip_sub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(local_public_key.clone()),
            gossip_sub_config,
        )
        .unwrap();

        let identify = identify::Behaviour::new(identify::Config::new(
            "/CEYLON-AI-IDENTITY/0.0.1".to_string(),
            local_public_key.public(),
        ));

        let ping = ping::Behaviour::new(ping::Config::new().with_interval(Duration::from_secs(10)));

        let rendezvous = RendezvousBehaviour::new(local_public_key.clone());

        Self {
            identify,
            ping,
            gossip_sub,
            rendezvous,
        }
    }
}

pub struct UnifiedPeer {
    behaviour: UnifiedPeerBehaviour,
    mode: PeerMode,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, Default)]
pub enum PeerMode {
    #[default]
    Client,
    Admin,
}

impl UnifiedPeer {
    pub fn new(local_public_key: identity::Keypair, mode: PeerMode) -> Self {
        Self {
            behaviour: UnifiedPeerBehaviour::new(local_public_key),
            mode,
        }
    }

    pub fn change_mode(&mut self, new_mode: PeerMode) {
        self.mode = new_mode;
    }

    pub fn get_mode(&self) -> &PeerMode {
        &self.mode
    }

    pub fn get_behaviour(&mut self) -> &mut UnifiedPeerBehaviour {
        &mut self.behaviour
    }
}

pub fn message_id_fn(message: &gossipsub::Message) -> gossipsub::MessageId {
    let mut s = DefaultHasher::new();
    message.data.hash(&mut s);
    gossipsub::MessageId::from(s.finish().to_string())
}

pub fn create_gossip_sub_config() -> gossipsub::Config {
    gossipsub::ConfigBuilder::default()
        .heartbeat_interval(Duration::from_millis(500))
        .mesh_n_low(4)
        .mesh_n(6)
        .mesh_n_high(8)
        .history_length(10)
        .history_gossip(10)
        .max_transmit_size(1024 * 1024 * 100)
        .validation_mode(gossipsub::ValidationMode::Permissive)
        .message_id_fn(message_id_fn)
        .build()
        .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))
        .unwrap()
}
