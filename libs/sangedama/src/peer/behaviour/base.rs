/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *  
 */

use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::Duration;

use libp2p::gossipsub::{self, Config};
use libp2p::swarm::NetworkBehaviour;
use tokio::io;

pub trait PeerBehaviour
where
    Self: NetworkBehaviour,
{
    fn new(local_public_key: libp2p::identity::Keypair) -> Self;
}

pub fn message_id_fn(message: &gossipsub::Message) -> gossipsub::MessageId {
    let mut s = DefaultHasher::new();
    message.data.hash(&mut s);
    gossipsub::MessageId::from(s.finish().to_string())
}

pub fn create_gossip_sub_config() -> Config {
    gossipsub::ConfigBuilder::default()
        .heartbeat_interval(Duration::from_millis(500)) // Faster heartbeat
        .mesh_n_low(4)  // Lower mesh degree for faster propagation
        .mesh_n(6)
        .mesh_n_high(8)
        .history_length(10)
        .history_gossip(10)
        .max_transmit_size(1024 * 1024 * 100)
        .validation_mode(gossipsub::ValidationMode::Permissive) // This sets the kind of message validation. The default is Strict (enforce message signing)
        .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
        .build()
        .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))
        .unwrap()
}
