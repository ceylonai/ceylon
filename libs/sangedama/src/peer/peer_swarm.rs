/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *  
 */

use std::time::Duration;

use libp2p::core::muxing::StreamMuxerBox;
use libp2p::core::transport::dummy::DummyTransport;
use libp2p::{identity, noise, tcp, tls, yamux, PeerId, Swarm, SwarmBuilder};

use crate::peer::behaviour::PeerBehaviour;

pub async fn create_swarm<B>(key: identity::Keypair) -> Swarm<B>
where
    B: PeerBehaviour + 'static,
{
    SwarmBuilder::with_existing_identity(key.clone())
        .with_tokio()
        .with_tcp(
            tcp::Config::default(),
            noise::Config::new,
            yamux::Config::default,
        )
        .unwrap()
        .with_quic()
        .with_other_transport(|_key| DummyTransport::<(PeerId, StreamMuxerBox)>::new())
        .unwrap()
        .with_dns()
        .unwrap()
        .with_websocket(
            (tls::Config::new, noise::Config::new),
            yamux::Config::default,
        )
        .await
        .unwrap()
        .with_behaviour(|_key| Ok(B::new(_key.clone())))
        .unwrap()
        .with_swarm_config(|cfg| {
            // Edit cfg here.
            cfg.with_idle_connection_timeout(Duration::from_secs(240))
        })
        .build()
}
