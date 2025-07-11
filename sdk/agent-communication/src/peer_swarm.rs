/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */

use crate::peer::Peer;
use libp2p::PeerId;
use std::collections::HashMap;

#[derive(Debug, Default)]
pub struct PeerManager {
    peers: HashMap<PeerId, Peer>,
}

impl PeerManager {
    pub fn new() -> Self {
        Self {
            peers: HashMap::new(),
        }
    }

    pub fn add_peer(&mut self, peer: Peer) {
        self.peers.insert(peer.id.clone(), peer);
    }

    pub fn remove_peer(&mut self, peer_id: &PeerId) {
        self.peers.remove(peer_id);
    }

    pub fn get_peer(&self, peer_id: &PeerId) -> Option<&Peer> {
        self.peers.get(peer_id)
    }

    pub fn get_peer_mut(&mut self, peer_id: &PeerId) -> Option<&mut Peer> {
        self.peers.get_mut(peer_id)
    }

    pub fn all_peers(&self) -> impl Iterator<Item = &Peer> {
        self.peers.values()
    }

    pub fn count(&self) -> usize {
        self.peers.len()
    }
}
