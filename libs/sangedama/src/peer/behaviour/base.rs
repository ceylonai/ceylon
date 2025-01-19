/*
 * Copyright (c) 2023-2025 SYIGEN LTD.
 * Author: Dewmal - dewmal@syigen.com
 * Created: 2025-01-19
 * Ceylon Project - https://github.com/ceylonai/ceylon
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * This file is part of Ceylon Project.
 * Original authors: Dewmal - dewmal@syigen.com
 * For questions and support: https://github.com/ceylonai/ceylon/issues
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
