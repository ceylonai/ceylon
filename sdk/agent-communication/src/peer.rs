/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */

use libp2p::{Multiaddr, PeerId};

#[derive(Debug, Clone)]
pub struct Peer {
    pub id: PeerId,
    pub addresses: Vec<Multiaddr>,
    pub connected: bool,
}

impl Peer {
    pub fn new(id: PeerId) -> Self {
        Self {
            id,
            addresses: Vec::new(),
            connected: false,
        }
    }

    pub fn add_address(&mut self, addr: Multiaddr) {
        if !self.addresses.contains(&addr) {
            self.addresses.push(addr);
        }
    }

    pub fn set_connected(&mut self, connected: bool) {
        self.connected = connected;
    }
}
