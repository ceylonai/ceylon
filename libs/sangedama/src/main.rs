/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

mod peer;

use std::net::Ipv4Addr;
use libp2p::multiaddr::Protocol;
use libp2p::Multiaddr;
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::info;

use peer::NodeMessage;
use peer::{create_key, get_peer_id};
use peer::{UnifiedPeerImpl, UnifiedPeerConfig};

#[tokio::main]
async fn main() {
    let subscriber = tracing_subscriber::FmtSubscriber::new();
    tracing::subscriber::set_global_default(subscriber).unwrap();

    let workspace_id = "workspace-test".to_string();
    info!("Starting {}", workspace_id);

    let admin_port = 7845;
    let admin_config = UnifiedPeerConfig::new_admin(
        workspace_id.clone(),
        admin_port,
        None,
    );

    let admin_key = create_key();
    let admin_id_from_key = get_peer_id(&admin_key);
    let (mut admin_peer, mut admin_listener) = UnifiedPeerImpl::create(admin_config.clone(), admin_key).await;
    let admin_id = admin_peer.id.clone();
    let admin_id_2 = admin_peer.id.clone();

    let cancel_token = CancellationToken::new();

    if admin_id.to_string() == admin_id_from_key.to_string() {
        info!("Admin peer created with id: {}", admin_id);
    }

    let admin_emitter = admin_peer.emitter();
    let cancel_token_clone = cancel_token.clone();
    let task_admin = tokio::task::spawn(async move {
        admin_peer.run(cancel_token_clone).await;
    });

    let task_admin_listener = tokio::spawn(async move {
        loop {
            select! {
                event = admin_listener.recv() => {
                    if let Some(event) = event {
                        match event {
                            NodeMessage::Message{ data, created_by, ..} => {
                                info!("Admin listener Message {:?} from {:?}",
                                    String::from_utf8(data),
                                    created_by
                                );
                            }
                            _ => {
                                info!("Admin listener {:?}", event);
                            }
                        }
                    }
                }
            }
        }
    });

    let task_run_admin = tokio::task::spawn(async move {
        loop {
            admin_emitter
                .send((
                    admin_id.clone(),
                    "Admin Send regards".to_string().as_bytes().to_vec(),
                    None,
                ))
                .await
                .unwrap();
            tokio::time::sleep(std::time::Duration::from_millis(1000)).await;
        }
    });

    // Create localhost address for peer-admin connection
    let peer_dial_address = Multiaddr::empty()
        .with(Protocol::Ip4(Ipv4Addr::LOCALHOST))
        .with(Protocol::Udp(admin_port))
        .with(Protocol::QuicV1);

    let peer_1 = create_client(
        workspace_id.clone(),
        admin_id_2.clone(),
        admin_port,
        "peer1".to_string(),
        cancel_token.clone(),
    ).await;

    let peer_2 = create_client(
        workspace_id.clone(),
        admin_id_2.clone(),
        admin_port,
        "peer2".to_string(),
        cancel_token.clone(),
    ).await;

    let peer_3 = create_client(
        workspace_id.clone(),
        admin_id_2.clone(),
        admin_port,
        "peer3".to_string(),
        cancel_token.clone(),
    ).await;

    let peer_4 = create_client(
        workspace_id.clone(),
        admin_id_2.clone(),
        admin_port,
        "peer4".to_string(),
        cancel_token.clone(),
    ).await;

    task_admin.await.unwrap();
    task_admin_listener.await.unwrap();
    task_run_admin.await.unwrap();

    peer_1.await.unwrap();
    peer_2.await.unwrap();
    peer_3.await.unwrap();
    peer_4.await.unwrap();
}

async fn create_client(
    workspace_id: String,
    admin_id: String,
    peer_dial_port: u16,
    name: String,
    cancel_token: CancellationToken,
) -> tokio::task::JoinHandle<()> {
    let member_key = create_key();
    let member_id_from_key = get_peer_id(&member_key);

    let member_config = UnifiedPeerConfig::new_member(
        name.clone(),
        workspace_id.clone(),
        admin_id,
        peer_dial_port,
        "127.0.0.1".to_string(),
        None,
    );

    let (mut peer, mut peer_listener) = UnifiedPeerImpl::create(
        member_config,
        member_key,
    ).await;

    let peer_emitter = peer.emitter();
    let peer_id = peer.id.clone();
    let peer_id_2 = peer_id.clone();

    if member_id_from_key.to_string() == peer_id.to_string() {
        info!("{} {} created", name.clone(), peer_id);
    }

    let cancel_token_clone = cancel_token.clone();
    let task_peer = tokio::task::spawn(async move {
        peer.run(cancel_token_clone).await;
    });

    let name_clone = name.clone();
    let task_peer_listener = tokio::spawn(async move {
        loop {
            select! {
                event = peer_listener.recv() => {
                    if let Some(event) = event {
                        match event {
                            NodeMessage::Message{ data, created_by, ..} => {
                                info!("{} {} listener Message {:?} from {:?}",
                                    name_clone,
                                    peer_id,
                                    String::from_utf8(data),
                                    created_by
                                );
                            }
                            _ => {
                                info!("{} listener {:?}", name_clone, event);
                            }
                        }
                    }
                }
            }
        }
    });

    let task_run_peer = tokio::task::spawn(async move {
        loop {
            peer_emitter
                .send((
                    peer_id_2.clone(),
                    format!("{} Send regards", name).as_bytes().to_vec(),
                    None,
                ))
                .await
                .expect("Failed to send message");
            tokio::time::sleep(std::time::Duration::from_millis(3000)).await;
        }
    });

    tokio::spawn(async {
        task_peer.await.unwrap();
        task_peer_listener.await.unwrap();
        task_run_peer.await.unwrap();
    })
}