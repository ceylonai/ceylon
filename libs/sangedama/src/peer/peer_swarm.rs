/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */
use std::num::NonZeroUsize;
use std::time::Duration;

use crate::peer::behaviour::peer::PeerBehaviour;
use libp2p::{identity, noise, tls, yamux, Swarm, SwarmBuilder};

pub async fn create_swarm<B>(key: identity::Keypair) -> Swarm<B>
where
    B: PeerBehaviour + Send + 'static, // Added Send trait
{
    SwarmBuilder::with_existing_identity(key)
        .with_tokio()
        .with_tcp(
            Default::default(),
            (tls::Config::new, noise::Config::new),
            yamux::Config::default,
        )
        .unwrap()
        .with_quic()
        .with_dns()
        .unwrap()
        .with_websocket(
            (tls::Config::new, noise::Config::new),
            yamux::Config::default,
        )
        .await
        .unwrap()
        .with_behaviour(|key| Ok(B::new(key.clone())))
        .unwrap()
        .with_swarm_config(|cfg| {
            cfg.with_idle_connection_timeout(Duration::from_secs(60)) // Reduced timeout
                .with_notify_handler_buffer_size(
                    NonZeroUsize::new(1024*1024).unwrap(),
                ) // Increased buffer
        })
        .build()
}
