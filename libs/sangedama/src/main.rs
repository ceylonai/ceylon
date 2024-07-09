use std::net::Ipv4Addr;
use libp2p::Multiaddr;
use libp2p::multiaddr::Protocol;
use tracing::{info};
use crate::peer::peer::{AdminPeer, AdminPeerConfig, Peer};

mod p2p;
mod peer;
#[tokio::main]
async fn main() {
    let subscriber = tracing_subscriber::FmtSubscriber::new();
    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
    info!("Starting sangedama");

    let admin_config = AdminPeerConfig::new(7845);
    let admin_address = admin_config.get_listen_address();
    
    let mut admin_peer = AdminPeer::create(admin_config).await;
    let admin_id = admin_peer.id.clone();

    let task_admin = tokio::task::spawn(async move {
        admin_peer.run(Some(admin_address)).await;
    });

    let mut peer = Peer::create("sangedama-peer1".to_string()).await;
    peer.run().await;
}