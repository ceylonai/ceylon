/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use libp2p::{identity, PeerId};

pub fn create_key() -> identity::Keypair {
    identity::Keypair::generate_ed25519()
}

pub fn create_key_from_bytes(bytes: Vec<u8>) -> identity::Keypair {
    identity::Keypair::from_protobuf_encoding(&bytes).unwrap()
}

pub fn get_peer_id(key: &identity::Keypair) -> PeerId {
    key.public().to_peer_id()
}
